import json
import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.core.dependencies import (
    require_role_ids, SUPERADMIN, ADMIN, COACH, CLIENT,
    _user_role_ids,
)
from app.core.responses import send_response, send_error
from app.core.security import decode_token
from app.core.ws_manager import manager
from app.models.chat import ChatConversation, ChatParticipant, ChatMessage
from app.models.user import User, UserDetail, RoleUser

router = APIRouter(prefix="/chat", tags=["Chat"])


# ── Helpers ───────────────────────────────────────────────────────────────────

def _get_detail(user_id: int, db: Session) -> Optional[UserDetail]:
    return db.query(UserDetail).filter(UserDetail.user_id == user_id).first()


def _serialize_message(msg: ChatMessage, db: Session) -> dict:
    detail = _get_detail(msg.sender_user_id, db)
    return {
        "id":             msg.id,
        "conversation_id": msg.conversation_id,
        "sender_user_id": msg.sender_user_id,
        "sender_name":    detail.name if detail else "Usuario",
        "sender_photo":   detail.photo if detail else None,
        "content":        msg.content,
        "created_at":     msg.created_at.isoformat() if msg.created_at else None,
    }


def _serialize_conversation(conv: ChatConversation, current_user_id: int, db: Session) -> dict:
    participant_ids = [p.user_id for p in conv.participants]
    participants = []
    for uid in participant_ids:
        d = _get_detail(uid, db)
        if d:
            participants.append({
                "user_id": uid,
                "name": d.name,
                "photo": d.photo,
            })

    last_msg = (
        db.query(ChatMessage)
        .filter(ChatMessage.conversation_id == conv.id)
        .order_by(ChatMessage.created_at.desc())
        .first()
    )

    name = conv.name
    if not name and conv.type == "individual":
        other = next((p for p in participants if p["user_id"] != current_user_id), None)
        name = other["name"] if other else "Conversación"

    return {
        "id":           conv.id,
        "type":         conv.type,
        "name":         name,
        "participants": participants,
        "last_message": _serialize_message(last_msg, db) if last_msg else None,
        "updated_at":   conv.updated_at.isoformat() if conv.updated_at else None,
    }


def _is_participant(conv_id: str, user_id: int, db: Session) -> bool:
    return db.query(ChatParticipant).filter(
        ChatParticipant.conversation_id == conv_id,
        ChatParticipant.user_id == user_id,
    ).first() is not None


def _coach_client_ids(coach_user_id: int, db: Session) -> list[int]:
    from app.core.dependencies import filter_clients_by_role
    client_role_users = db.query(RoleUser).filter(RoleUser.role_id == CLIENT).all()
    client_user_ids = [ru.user_id for ru in client_role_users]

    from app.models.user import UserDetail as UD
    all_details = db.query(UD).filter(UD.user_id.in_(client_user_ids)).all()
    filtered = filter_clients_by_role(all_details, db.query(User).filter(User.id == coach_user_id).first(), db)
    return [d.user_id for d in filtered]


# ── Schemas ───────────────────────────────────────────────────────────────────

class CreateConversationRequest(BaseModel):
    type: str = "individual"
    participant_user_ids: list[int] = []
    name: Optional[str] = None
    target: Optional[str] = None  # "my_clients" | "all_coaches" | "all_clients"


class SendMessageRequest(BaseModel):
    content: str


# ── REST endpoints ────────────────────────────────────────────────────────────

@router.get("/conversations")
def list_conversations(
    db: Session = Depends(get_db),
    current_user=Depends(require_role_ids(SUPERADMIN, ADMIN, COACH, CLIENT)),
):
    part_rows = db.query(ChatParticipant).filter(
        ChatParticipant.user_id == current_user.id
    ).all()
    conv_ids = [p.conversation_id for p in part_rows]
    convs = db.query(ChatConversation).filter(
        ChatConversation.id.in_(conv_ids)
    ).order_by(ChatConversation.updated_at.desc()).all()
    return send_response(
        [_serialize_conversation(c, current_user.id, db) for c in convs], "OK"
    )


@router.post("/conversations")
def create_conversation(
    data: CreateConversationRequest,
    db: Session = Depends(get_db),
    current_user=Depends(require_role_ids(SUPERADMIN, ADMIN, COACH, CLIENT)),
):
    user_ids: list[int] = list(set(data.participant_user_ids))
    if current_user.id not in user_ids:
        user_ids.append(current_user.id)

    if data.type == "group" and data.target:
        roles = _user_role_ids(current_user.id, db)
        if data.target == "my_clients" and COACH in roles:
            client_ids = _coach_client_ids(current_user.id, db)
            user_ids = list(set(user_ids + client_ids))
        elif data.target == "all_coaches" and (ADMIN in roles or SUPERADMIN in roles):
            coach_users = db.query(RoleUser).filter(RoleUser.role_id == COACH).all()
            user_ids = list(set(user_ids + [ru.user_id for ru in coach_users]))
        elif data.target == "all_clients" and (ADMIN in roles or SUPERADMIN in roles):
            client_users = db.query(RoleUser).filter(RoleUser.role_id == CLIENT).all()
            user_ids = list(set(user_ids + [ru.user_id for ru in client_users]))

    if data.type == "individual" and len(user_ids) == 2:
        existing = (
            db.query(ChatConversation)
            .join(ChatParticipant, ChatParticipant.conversation_id == ChatConversation.id)
            .filter(
                ChatConversation.type == "individual",
                ChatParticipant.user_id == user_ids[0],
            ).all()
        )
        for conv in existing:
            ids = {p.user_id for p in conv.participants}
            if ids == set(user_ids):
                return send_response(_serialize_conversation(conv, current_user.id, db), "OK")

    conv = ChatConversation(
        id=str(uuid.uuid4()),
        type=data.type,
        name=data.name,
        created_by_user_id=current_user.id,
    )
    db.add(conv)
    db.flush()

    for uid in user_ids:
        db.add(ChatParticipant(conversation_id=conv.id, user_id=uid))

    db.commit()
    db.refresh(conv)
    return send_response(_serialize_conversation(conv, current_user.id, db), "Conversación creada")


@router.get("/conversations/{conv_id}/messages")
def get_messages(
    conv_id: str,
    page: int = Query(1),
    per_page: int = Query(50),
    db: Session = Depends(get_db),
    current_user=Depends(require_role_ids(SUPERADMIN, ADMIN, COACH, CLIENT)),
):
    if not _is_participant(conv_id, current_user.id, db):
        return send_error("No tienes acceso a esta conversación", code=403)
    total = db.query(ChatMessage).filter(ChatMessage.conversation_id == conv_id).count()
    msgs = (
        db.query(ChatMessage)
        .filter(ChatMessage.conversation_id == conv_id)
        .order_by(ChatMessage.created_at.asc())
        .offset((page - 1) * per_page)
        .limit(per_page)
        .all()
    )
    return send_response({
        "messages":  [_serialize_message(m, db) for m in msgs],
        "total":     total,
        "page":      page,
        "per_page":  per_page,
        "last_page": max(1, (total + per_page - 1) // per_page),
    }, "OK")


@router.post("/conversations/{conv_id}/messages")
def send_message_rest(
    conv_id: str,
    data: SendMessageRequest,
    db: Session = Depends(get_db),
    current_user=Depends(require_role_ids(SUPERADMIN, ADMIN, COACH, CLIENT)),
):
    if not _is_participant(conv_id, current_user.id, db):
        return send_error("No tienes acceso a esta conversación", code=403)
    msg = ChatMessage(
        id=str(uuid.uuid4()),
        conversation_id=conv_id,
        sender_user_id=current_user.id,
        content=data.content,
    )
    db.add(msg)
    conv = db.query(ChatConversation).filter(ChatConversation.id == conv_id).first()
    if conv:
        conv.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(msg)
    return send_response(_serialize_message(msg, db), "Mensaje enviado")


@router.delete("/conversations/{conv_id}")
def delete_conversation(
    conv_id: str,
    db: Session = Depends(get_db),
    current_user=Depends(require_role_ids(SUPERADMIN, ADMIN, COACH, CLIENT)),
):
    conv = db.query(ChatConversation).filter(ChatConversation.id == conv_id).first()
    if not conv:
        return send_error("Conversación no encontrada", code=404)
    roles = _user_role_ids(current_user.id, db)
    if conv.created_by_user_id != current_user.id and not (ADMIN in roles or SUPERADMIN in roles):
        return send_error("Sin permiso para eliminar", code=403)
    db.delete(conv)
    db.commit()
    return send_response({}, "Conversación eliminada")


# ── WebSocket ─────────────────────────────────────────────────────────────────

@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    token: str = Query(...),
    db: Session = Depends(get_db),
):
    payload = decode_token(token)
    if not payload or payload.get("type") != "access":
        await websocket.close(code=4001)
        return

    user_id: int = int(payload.get("sub", 0))
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        await websocket.close(code=4001)
        return

    await manager.connect(websocket, user_id)
    try:
        while True:
            raw = await websocket.receive_text()
            try:
                data = json.loads(raw)
            except Exception:
                continue

            event_type = data.get("type", "message")

            if event_type == "typing":
                conv_id = data.get("conversation_id")
                if conv_id and _is_participant(conv_id, user_id, db):
                    participant_ids = [
                        p.user_id for p in
                        db.query(ChatParticipant).filter(
                            ChatParticipant.conversation_id == conv_id
                        ).all()
                    ]
                    await manager.broadcast_to_users(
                        [uid for uid in participant_ids if uid != user_id],
                        {"type": "typing", "conversation_id": conv_id, "user_id": user_id},
                    )
                continue

            conv_id = data.get("conversation_id")
            content = (data.get("content") or "").strip()
            if not conv_id or not content:
                continue
            if not _is_participant(conv_id, user_id, db):
                continue

            msg = ChatMessage(
                id=str(uuid.uuid4()),
                conversation_id=conv_id,
                sender_user_id=user_id,
                content=content,
            )
            db.add(msg)
            conv = db.query(ChatConversation).filter(ChatConversation.id == conv_id).first()
            if conv:
                conv.updated_at = datetime.utcnow()
            db.commit()
            db.refresh(msg)

            payload_out = {
                "type":    "message",
                "message": _serialize_message(msg, db),
            }
            participant_ids = [
                p.user_id for p in
                db.query(ChatParticipant).filter(
                    ChatParticipant.conversation_id == conv_id
                ).all()
            ]
            await manager.broadcast_to_users(participant_ids, payload_out)

    except WebSocketDisconnect:
        manager.disconnect(websocket, user_id)
