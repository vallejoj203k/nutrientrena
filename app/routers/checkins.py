from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Optional

from app.database import get_db
from app.core.dependencies import (
    require_role_ids, verify_client_access,
    SUPERADMIN, ADMIN, COACH,
)
from app.core.responses import send_response, send_error
from app.core.email import notify_coach_checkin, notify_client_coach_notes
from app.models.checkin import WeeklyCheckin
from app.models.user import UserDetail, UserParent, User
from app.schemas.checkin import CheckinCreate, CheckinCoachUpdate, CheckinUpdate, CheckinOut


def _get_coach_for_client(client_detail_id: str, db: Session):
    """Return (coach_detail, coach_user) for a client, or (None, None)."""
    parent = db.query(UserParent).filter(
        UserParent.user_detail_id == client_detail_id
    ).first()
    if not parent:
        return None, None
    coach_detail = db.query(UserDetail).filter(
        UserDetail.id == parent.parent_user_detail_id
    ).first()
    if not coach_detail:
        return None, None
    coach_user = db.query(User).filter(User.id == coach_detail.user_id).first()
    return coach_detail, coach_user

router = APIRouter(prefix="/checkins", tags=["Check-ins"])


def _get_coach_detail(db: Session, user_id: int) -> Optional[UserDetail]:
    return db.query(UserDetail).filter(UserDetail.user_id == user_id).first()


# ── Create: admin, coach ───────────────────────────────────────────────────────
@router.post("", summary="Registrar check-in", description="Registra un check-in semanal del cliente con peso, medidas y foto.")
def create_checkin(
    data: CheckinCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_role_ids(SUPERADMIN, ADMIN, COACH)),
):
    client = db.query(UserDetail).filter(UserDetail.id == data.client_user_detail_id).first()
    if not client:
        return send_error("Cliente no encontrado")

    verify_client_access(data.client_user_detail_id, current_user, db)

    coach_detail = _get_coach_detail(db, current_user.id)
    checkin = WeeklyCheckin(
        client_user_detail_id=data.client_user_detail_id,
        coach_user_detail_id=coach_detail.id if coach_detail else None,
        checkin_date=data.checkin_date,
        weight=data.weight,
        notes=data.notes,
        photo_url=data.photo_url,
        photo2=data.photo2,
        photo3=data.photo3,
        body_fat=data.body_fat,
        muscle_mass=data.muscle_mass,
        waist=data.waist,
        chest=data.chest,
        hips=data.hips,
        arms=data.arms,
        legs=data.legs,
    )
    db.add(checkin)
    db.commit()
    db.refresh(checkin)

    # ── Notify coach ──────────────────────────────────────────────────────────
    coach_detail, coach_user = _get_coach_for_client(data.client_user_detail_id, db)
    if coach_user and coach_user.email:
        client = db.query(UserDetail).filter(UserDetail.id == data.client_user_detail_id).first()
        client_name = f"{client.name or ''} {client.last_name or ''}".strip() if client else "Cliente"
        coach_name  = f"{coach_detail.name or ''} {coach_detail.last_name or ''}".strip() or "Coach"
        notify_coach_checkin(
            coach_email=coach_user.email,
            coach_name=coach_name,
            client_name=client_name,
            checkin_date=str(data.checkin_date or ""),
            weight=data.weight,
        )

    return send_response(CheckinOut.model_validate(checkin).model_dump(), "Check-in registrado")


# ── Get by client: admin, coach (own clients only) ────────────────────────────
@router.get("/client/{client_id}", summary="Historial de check-ins", description="Retorna el historial de check-ins de un cliente con progreso de peso.")
def client_checkins(
    client_id: str,
    limit: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user=Depends(require_role_ids(SUPERADMIN, ADMIN, COACH)),
):
    verify_client_access(client_id, current_user, db)

    checkins = (
        db.query(WeeklyCheckin)
        .filter(WeeklyCheckin.client_user_detail_id == client_id)
        .order_by(WeeklyCheckin.checkin_date.desc())
        .limit(limit)
        .all()
    )
    data = [CheckinOut.model_validate(c).model_dump() for c in checkins]

    progress = None
    if len(checkins) >= 2 and checkins[0].weight and checkins[1].weight:
        progress = round(checkins[0].weight - checkins[1].weight, 2)

    return send_response({"checkins": data, "weight_progress": progress}, "OK")


# ── Summary: admin, coach (own clients only) ──────────────────────────────────
@router.get("/summary/{client_id}", summary="Resumen de check-ins", description="Totales y variación de peso desde el primer al último check-in del cliente.")
def client_summary(
    client_id: str,
    db: Session = Depends(get_db),
    current_user=Depends(require_role_ids(SUPERADMIN, ADMIN, COACH)),
):
    verify_client_access(client_id, current_user, db)

    checkins = (
        db.query(WeeklyCheckin)
        .filter(WeeklyCheckin.client_user_detail_id == client_id)
        .order_by(WeeklyCheckin.checkin_date.asc())
        .all()
    )
    if not checkins:
        return send_response({"total": 0}, "Sin check-ins")

    weights = [c.weight for c in checkins if c.weight is not None]
    first_weight = weights[0] if weights else None
    last_weight  = weights[-1] if weights else None
    total_change = round(last_weight - first_weight, 2) if first_weight and last_weight else None

    return send_response({
        "total": len(checkins),
        "first_checkin": str(checkins[0].checkin_date),
        "last_checkin":  str(checkins[-1].checkin_date),
        "first_weight":  first_weight,
        "last_weight":   last_weight,
        "total_weight_change": total_change,
    }, "OK")


# ── Coach notes: admin, coach ─────────────────────────────────────────────────
@router.put("/{id}/coach-notes", summary="Agregar notas del coach", description="El coach añade retroalimentación y actualiza medidas en un check-in.")
def add_coach_notes(
    id: str,
    data: CheckinCoachUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(require_role_ids(SUPERADMIN, ADMIN, COACH)),
):
    checkin = db.query(WeeklyCheckin).filter(WeeklyCheckin.id == id).first()
    if not checkin:
        return send_error("Check-in no encontrado")

    verify_client_access(checkin.client_user_detail_id, current_user, db)

    for field in ("coach_notes", "weight", "body_fat", "waist", "chest", "hips", "arms", "legs"):
        v = getattr(data, field, None)
        if v is not None:
            setattr(checkin, field, v)

    coach_detail = _get_coach_detail(db, current_user.id)
    if coach_detail and not checkin.coach_user_detail_id:
        checkin.coach_user_detail_id = coach_detail.id

    db.commit()
    db.refresh(checkin)

    # ── Notify client when coach leaves notes ─────────────────────────────────
    if data.coach_notes:
        client = db.query(UserDetail).filter(
            UserDetail.id == checkin.client_user_detail_id
        ).first()
        client_user = db.query(User).filter(User.id == client.user_id).first() if client else None
        if client_user and client_user.email:
            client_name = f"{client.name or ''} {client.last_name or ''}".strip() or "Cliente"
            coach_detail_obj = None
            if checkin.coach_user_detail_id:
                coach_detail_obj = db.query(UserDetail).filter(
                    UserDetail.id == checkin.coach_user_detail_id
                ).first()
            coach_name = (
                f"{coach_detail_obj.name or ''} {coach_detail_obj.last_name or ''}".strip()
                if coach_detail_obj else "Tu coach"
            )
            notify_client_coach_notes(
                client_email=client_user.email,
                client_name=client_name,
                coach_name=coach_name,
                notes=data.coach_notes,
            )

    return send_response(CheckinOut.model_validate(checkin).model_dump(), "Notas actualizadas")


# ── Update all own fields: admin, coach ───────────────────────────────────────
@router.put("/{id}/update", summary="Actualizar check-in", description="Edita los datos de un check-in (fecha, peso, medidas, notas, fotos).")
def update_checkin(
    id: str,
    data: CheckinUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(require_role_ids(SUPERADMIN, ADMIN, COACH)),
):
    checkin = db.query(WeeklyCheckin).filter(WeeklyCheckin.id == id).first()
    if not checkin:
        return send_error("Check-in no encontrado")
    verify_client_access(checkin.client_user_detail_id, current_user, db)
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(checkin, field, value)
    db.commit()
    db.refresh(checkin)
    return send_response(CheckinOut.model_validate(checkin).model_dump(), "Check-in actualizado")


# ── Delete: admin, coach ──────────────────────────────────────────────────────
@router.delete("/{id}", summary="Eliminar check-in", description="Elimina un check-in.")
def delete_checkin(
    id: str,
    db: Session = Depends(get_db),
    current_user=Depends(require_role_ids(SUPERADMIN, ADMIN, COACH)),
):
    checkin = db.query(WeeklyCheckin).filter(WeeklyCheckin.id == id).first()
    if not checkin:
        return send_error("Check-in no encontrado")
    verify_client_access(checkin.client_user_detail_id, current_user, db)
    db.delete(checkin)
    db.commit()
    return send_response(None, "Check-in eliminado")
