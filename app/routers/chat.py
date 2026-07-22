import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.dependencies import (
    ADMIN,
    CLIENT,
    COACH,
    SUPERADMIN,
    _coach_client_ids,
    _get_coach_detail,
    _user_role_ids,
    get_current_user,
    get_db,
)
from app.core.responses import send_error, send_response
from app.core.security import decode_token
from app.core.ws_manager import manager
from app.database import SessionLocal
from app.models.chat import ChatConversation, ChatMessage, ChatParticipant
from app.models.user import RoleUser, User, UserDetail

router = APIRouter(prefix="/chat", tags=["Chat"])


# ── Pydantic schemas ──────────────────────────────────────────────────────────

class ConversationCreate(BaseModel):
    type: str  # 'individual' | 'group'
    participant_user_ids: Optional[list[int]] = None
    name: Optional[str] = None
    target: Optional[str] = None  # 'coaches' | 'clients' (admin group)


class MessageCreate(BaseModel):
    content: str


# ── Helpers ───────────────────────────────────────────────────────────────────

def _user_detail(db: Session, user_id: int) -> Optional[UserDetail]:
    return db.query(UserDetail).filter(UserDetail.user_id == user_id).first()


def _serialize_message(msg: ChatMessage, db: Session) -> dict:
    sender_detail = _user_detail(db, msg.sender_user_id)
    sender_name = ""
    sender_photo = None
    if sender_detail:
        sender_name = f"{sender_detail.name} {sender_detail.last_name or ''}".strip()
        sender_photo = sender_detail.photo
    elif msg.sender:
        sender_name = msg.sender.name
    return {
        "id": msg.id,
        "conversation_id": msg.conversation_id,
        "content": msg.content,
        "sender_user_id": msg.sender_user_id,
        "sender_name": sender_name,
        "sender_photo": sender_photo,
        "created_at": msg.created_at.isoformat() if msg.created_at else None,
    }


def _serialize_conversation(conv: ChatConversation, current_user_id: int, db: Session) -> dict:
    participant_user_ids = [p.user_id for p in conv.participants]
    participants_info = []
    for uid in participant_user_ids:
        detail = _user_detail(db, uid)
        if detail:
            participants_info.append({
                "user_id": uid,
                "name": f"{detail.name} {detail.last_name or ''}".strip(),
                "photo": detail.photo,
            })
        else:
            u = db.query(User).filter(User.id == uid).first()
            if u:
                participants_info.append({"user_id": uid, "name": u.name, "photo": None})

    last_msg = (
        db.query(ChatMessage)
        .filter(ChatMessage.conversation_id == conv.id)
        .order_by(ChatMessage.created_at.desc())
        .first()
    )
    last_message = _serialize_message(last_msg, db) if last_msg else None

    return {
        "id": conv.id,
        "type": conv.type,
        "name": conv.name,
        "created_by_user_id": conv.created_by_user_id,
        "created_at": conv.created_at.isoformat() if conv.created_at else None,
        "updated_at": conv.updated_at.isoformat() if conv.updated_at else None,
        "participants": participants_info,
        "last_message": last_message,
    }


def _get_client_user_ids_for_coach(coach_user_id: int, db: Session) -> list[int]:
    coach_detail = _get_coach_detail(coach_user_id, db)
    if not coach_detail:
        return []
    client_detail_ids = _coach_client_ids(coach_detail.id, db)
    result = []
    for detail_id in client_detail_ids:
        detail = db.query(UserDetail).filter(UserDetail.id == detail_id).first()
        if detail:
            result.append(detail.user_id)
    return result


def _get_all_coach_user_ids(db: Session) -> list[int]:
    rows = db.query(RoleUser).filter(RoleUser.role_id == COACH).all()
    return [r.user_id for r in rows]


def _get_all_client_user_ids(db: Session) -> list[int]:
    rows = db.query(RoleUser).filter(RoleUser.role_id == CLIENT).all()
    return [r.user_id for r in rows]


# ── REST endpoints ────────────────────────────────────────────────────────────

@router.get("/conversations")
def list_conversations(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    participations = (
        db.query(ChatParticipant)
        .filter(ChatParticipant.user_id == current_user.id)
        .all()
    )
    conv_ids = [p.conversation_id for p in participations]
    convs = (
        db.query(ChatConversation)
        .filter(ChatConversation.id.in_(conv_ids))
        .order_by(ChatConversation.updated_at.desc())
        .all()
    )
    data = [_serialize_conversation(c, current_user.id, db) for c in convs]
    return send_response(data, "Conversaciones obtenidas")


@router.post("/conversations")
def create_conversation(
    body: ConversationCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    user_roles = _user_role_ids(current_user.id, db)

    if body.type not in ("individual", "group"):
        return send_error("Tipo debe ser 'individual' o 'group'", code=400)

    if body.type == "group" and CLIENT in user_roles and COACH not in user_roles and ADMIN not in user_roles and SUPERADMIN not in user_roles:
        return send_error("Los clientes no pueden crear grupos", code=403)

    participant_ids: list[int] = list(body.participant_user_ids or [])

    if body.type == "group" and not participant_ids:
        is_coach = COACH in user_roles
        is_admin = ADMIN in user_roles or SUPERADMIN in user_roles
        if is_admin:
            target = body.target or "clients"
            if target == "coaches":
                participant_ids = _get_all_coach_user_ids(db)
            else:
                participant_ids = _get_all_client_user_ids(db)
        elif is_coach:
            participant_ids = _get_client_user_ids_for_coach(current_user.id, db)
        else:
            return send_error("No se puede determinar los participantes", code=400)

    if current_user.id not in participant_ids:
        participant_ids.append(current_user.id)

    now = datetime.utcnow()
    conv = ChatConversation(
        id=str(uuid.uuid4()),
        type=body.type,
        name=body.name,
        created_by_user_id=current_user.id,
        created_at=now,
        updated_at=now,
    )
    db.add(conv)
    db.flush()

    for uid in set(participant_ids):
        db.add(ChatParticipant(
            conversation_id=conv.id,
            user_id=uid,
            joined_at=now,
        ))

    db.commit()
    db.refresh(conv)
    return send_response(_serialize_conversation(conv, current_user.id, db), "Conversación creada")


@router.get("/conversations/{conv_id}/messages")
def list_messages(
    conv_id: str,
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    part = (
        db.query(ChatParticipant)
        .filter(
            ChatParticipant.conversation_id == conv_id,
            ChatParticipant.user_id == current_user.id,
        )
        .first()
    )
    if not part:
        return send_error("Conversación no encontrada", code=404)

    total = db.query(ChatMessage).filter(ChatMessage.conversation_id == conv_id).count()
    messages = (
        db.query(ChatMessage)
        .filter(ChatMessage.conversation_id == conv_id)
        .order_by(ChatMessage.created_at.asc())
        .offset((page - 1) * per_page)
        .limit(per_page)
        .all()
    )
    data = [_serialize_message(m, db) for m in messages]
    return send_response({"messages": data, "total": total, "page": page, "per_page": per_page}, "Mensajes obtenidos")


@router.get("/unread-count")
def unread_count(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Total de mensajes no leídos del usuario y desglose por conversación.

    'No leído' = mensaje de otra persona con created_at posterior a la
    última vez que el usuario abrió esa conversación (last_read_at); si
    nunca la abrió, se usa joined_at como referencia.
    """
    parts = (
        db.query(ChatParticipant)
        .filter(ChatParticipant.user_id == current_user.id)
        .all()
    )
    total = 0
    per_conversation = []
    for part in parts:
        threshold = part.last_read_at or part.joined_at
        q = db.query(ChatMessage).filter(
            ChatMessage.conversation_id == part.conversation_id,
            ChatMessage.sender_user_id != current_user.id,
        )
        if threshold is not None:
            q = q.filter(ChatMessage.created_at > threshold)
        n = q.count()
        if n:
            total += n
            per_conversation.append({"conversation_id": part.conversation_id, "count": n})
    return send_response({"total": total, "conversations": per_conversation}, "OK")


@router.post("/conversations/{conv_id}/read")
def mark_conversation_read(
    conv_id: str,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Marca la conversación como leída para el usuario (limpia su badge)."""
    part = (
        db.query(ChatParticipant)
        .filter(
            ChatParticipant.conversation_id == conv_id,
            ChatParticipant.user_id == current_user.id,
        )
        .first()
    )
    if not part:
        return send_error("Conversación no encontrada", code=404)
    part.last_read_at = datetime.utcnow()
    db.commit()
    return send_response(None, "Conversación marcada como leída")


@router.post("/conversations/{conv_id}/messages")
async def send_message_rest(
    conv_id: str,
    body: MessageCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    part = (
        db.query(ChatParticipant)
        .filter(
            ChatParticipant.conversation_id == conv_id,
            ChatParticipant.user_id == current_user.id,
        )
        .first()
    )
    if not part:
        return send_error("Conversación no encontrada", code=404)

    now = datetime.utcnow()
    msg = ChatMessage(
        id=str(uuid.uuid4()),
        conversation_id=conv_id,
        sender_user_id=current_user.id,
        content=body.content,
        created_at=now,
    )
    db.add(msg)

    conv = db.query(ChatConversation).filter(ChatConversation.id == conv_id).first()
    if conv:
        conv.updated_at = now

    db.commit()
    db.refresh(msg)

    data = _serialize_message(msg, db)

    # Notificar en tiempo real a los demás participantes (p. ej. el coach)
    # por WebSocket, igual que el endpoint WS. Sin esto, quien envía por
    # REST (la zona del cliente) no notificaba al destinatario conectado.
    recipient_ids = [
        p.user_id for p in
        db.query(ChatParticipant).filter(ChatParticipant.conversation_id == conv_id).all()
    ]
    await manager.broadcast_to_users(
        recipient_ids,
        {"type": "message", "conversation_id": conv_id, "message": data},
    )

    return send_response(data, "Mensaje enviado")


@router.delete("/conversations/{conv_id}")
def delete_conversation(
    conv_id: str,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    conv = db.query(ChatConversation).filter(ChatConversation.id == conv_id).first()
    if not conv:
        return send_error("Conversación no encontrada", code=404)

    user_roles = _user_role_ids(current_user.id, db)
    is_admin = ADMIN in user_roles or SUPERADMIN in user_roles
    if conv.created_by_user_id != current_user.id and not is_admin:
        return send_error("No tienes permisos para eliminar esta conversación", code=403)

    db.delete(conv)
    db.commit()
    return send_response(None, "Conversación eliminada")


# ── WebSocket endpoint ────────────────────────────────────────────────────────

router_ws = APIRouter(tags=["Chat"])


@router_ws.websocket("/ws/chat")
async def websocket_chat(websocket: WebSocket, token: str = Query(...)):
    payload = decode_token(token)
    if payload is None or payload.get("type") != "access":
        await websocket.close(code=4001)
        return

    user_id_raw = payload.get("sub")
    if user_id_raw is None:
        await websocket.close(code=4001)
        return

    user_id = int(user_id_raw)

    await manager.connect(websocket, user_id)
    try:
        while True:
            data = await websocket.receive_json()
            msg_type = data.get("type", "message")

            if msg_type == "typing":
                conv_id = data.get("conversation_id")
                if not conv_id:
                    continue
                db = SessionLocal()
                try:
                    participants = db.query(ChatParticipant).filter(
                        ChatParticipant.conversation_id == conv_id
                    ).all()
                    recipient_ids = [p.user_id for p in participants if p.user_id != user_id]
                finally:
                    db.close()
                await manager.broadcast_to_users(
                    recipient_ids,
                    {"type": "typing", "conversation_id": conv_id, "user_id": user_id},
                )
                continue

            conv_id = data.get("conversation_id")
            content = data.get("content", "").strip()
            if not conv_id or not content:
                continue

            db = SessionLocal()
            try:
                part = db.query(ChatParticipant).filter(
                    ChatParticipant.conversation_id == conv_id,
                    ChatParticipant.user_id == user_id,
                ).first()
                if not part:
                    continue

                now = datetime.utcnow()
                msg = ChatMessage(
                    id=str(uuid.uuid4()),
                    conversation_id=conv_id,
                    sender_user_id=user_id,
                    content=content,
                    created_at=now,
                )
                db.add(msg)

                conv = db.query(ChatConversation).filter(ChatConversation.id == conv_id).first()
                if conv:
                    conv.updated_at = now

                db.commit()
                db.refresh(msg)

                msg_data = {
                    "id": msg.id,
                    "conversation_id": msg.conversation_id,
                    "content": msg.content,
                    "sender_user_id": msg.sender_user_id,
                    "sender_name": "",
                    "sender_photo": None,
                    "created_at": msg.created_at.isoformat() if msg.created_at else None,
                }
                sender_detail = _user_detail(db, user_id)
                if sender_detail:
                    msg_data["sender_name"] = f"{sender_detail.name} {sender_detail.last_name or ''}".strip()
                    msg_data["sender_photo"] = sender_detail.photo

                participants = db.query(ChatParticipant).filter(
                    ChatParticipant.conversation_id == conv_id
                ).all()
                recipient_ids = [p.user_id for p in participants]
            finally:
                db.close()

            broadcast_payload = {
                "type": "message",
                "conversation_id": conv_id,
                "message": msg_data,
            }
            await manager.broadcast_to_users(recipient_ids, broadcast_payload)

    except WebSocketDisconnect:
        manager.disconnect(websocket, user_id)
    except Exception:
        manager.disconnect(websocket, user_id)
