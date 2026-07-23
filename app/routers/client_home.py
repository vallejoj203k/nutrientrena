"""Zona del cliente — endpoint agregado para la pantalla de Inicio.

Devuelve, en una sola llamada, lo que necesita el Inicio del cliente:
perfil, coach, adherencia de la semana, sesión/rutina, estado del
check-in y contador de notificaciones.

Se calcula siempre para el usuario autenticado (ownership implícito: el
cliente solo obtiene lo suyo).
"""
from datetime import date, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.core.dependencies import require_role_ids, SUPERADMIN, ADMIN, COACH, CLIENT
from app.core.responses import send_response, send_error
from app.models.user import User, UserDetail, UserParent
from app.models.routine import Routine
from app.models.session_log import WorkoutSession
from app.models.checkin import WeeklyCheckin

router = APIRouter(prefix="/client", tags=["Client"])

_WEEKDAY_ES = ["L", "M", "X", "J", "V", "S", "D"]


def _client_detail(db: Session, user: User):
    return db.query(UserDetail).filter(UserDetail.user_id == user.id).first()


def _coach_of(db: Session, client_detail_id: str):
    """Coach (UserDetail) del cliente, vía user_parents. None si no tiene."""
    parent = db.query(UserParent).filter(
        UserParent.user_detail_id == client_detail_id
    ).first()
    if not parent:
        return None
    return db.query(UserDetail).filter(
        UserDetail.id == parent.parent_user_detail_id
    ).first()


_MONTHS_ES = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"]
_WEEKDAY_NAMES = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]


def _routine_day_muscles(day):
    """Grupos musculares únicos de un día de rutina (por orden de aparición)."""
    seen, out = set(), []
    for blk in (day.blocks or []):
        for ex in (blk.exercises or []):
            mg = ex.training.muscle_group.name if (ex.training and ex.training.muscle_group) else None
            if mg and mg not in seen:
                seen.add(mg)
                out.append(mg)
    return out


@router.get("/home", summary="Inicio del cliente", description="Datos agregados de la pantalla de inicio del cliente.")
def client_home(
    week_offset: int = Query(0),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role_ids(SUPERADMIN, ADMIN, COACH, CLIENT)),
):
    today = date.today()
    today_idx = today.weekday()  # 0 = lunes
    monday = today - timedelta(days=today_idx)
    week_start = monday + timedelta(days=week_offset * 7)
    week_end = week_start + timedelta(days=6)

    detail = _client_detail(db, current_user)

    # ── Perfil ──
    full_name = current_user.name if hasattr(current_user, "name") else None
    if detail:
        full_name = (f"{detail.name or ''} {detail.last_name or ''}").strip() or full_name
    full_name = full_name or getattr(current_user, "email", None) or "Cliente"
    parts = full_name.strip().split()
    initials = ((parts[0][:1] if parts else "C") + (parts[1][:1] if len(parts) > 1 else "")).upper()
    profile = {
        "name": full_name,
        "photo": getattr(current_user, "photo", None),
        "initials": initials or "C",
    }

    # ── Coach ──
    coach = None
    coach_detail = _coach_of(db, detail.id) if detail else None
    if coach_detail:
        cname = (f"{coach_detail.name or ''} {coach_detail.last_name or ''}").strip() or "Coach"
        coach = {"name": cname, "first_name": (coach_detail.name or cname).split()[0] if cname else "Coach",
                 "initials": (cname.strip()[:1] or "C").upper()}

    # ── Semana visible (sesiones registradas por día) + racha ──
    all_sessions = []
    if detail:
        all_sessions = db.query(WorkoutSession).filter(
            WorkoutSession.client_user_detail_id == detail.id
        ).all()
    session_dates = {s.session_date for s in all_sessions}
    week = []
    for i in range(7):
        d = week_start + timedelta(days=i)
        week.append({
            "date": d.isoformat(),
            "label": _WEEKDAY_ES[i],
            "day": d.day,
            "done": d in session_dates,
            "is_today": d == today,
            "is_future": d > today,
        })
    week_range = f"{week_start.day}–{week_end.day} {_MONTHS_ES[week_end.month - 1].capitalize()}"

    # Racha: días consecutivos con entreno terminando en hoy (o ayer si hoy aún no)
    streak = 0
    cursor = today if today in session_dates else today - timedelta(days=1)
    while cursor in session_dates:
        streak += 1
        cursor -= timedelta(days=1)

    # ── Rutina de HOY (día de la rutina según el día de la semana) ──
    routine = None
    r = db.query(Routine).filter(Routine.user_id == current_user.id).order_by(Routine.id.desc()).first()
    if r:
        days = r.days_list or []
        rd = days[today_idx] if today_idx < len(days) else None
        if rd:
            muscles = _routine_day_muscles(rd)
            routine = {
                "id": r.id,
                "name": rd.day_name or f"Día {today_idx + 1}",
                "muscles": muscles,
                "focus": " · ".join(muscles) if muscles else (r.objective or r.training or None),
                "duration_min": r.time,
                "is_rest": False,
            }
        else:
            routine = {"id": r.id, "name": None, "muscles": [], "focus": None, "duration_min": None, "is_rest": True}

    # ── Menú/dieta de HOY (kcal + nº de comidas) ──
    menu = None
    if detail:
        menu = _today_menu_summary(db, detail, current_user, today_idx)

    # ── Check-in solicitado por el coach (pendiente si no hay uno esta semana) ──
    this_monday = monday
    this_sunday = monday + timedelta(days=6)
    checkin_done = False
    if detail:
        checkin_done = db.query(WeeklyCheckin).filter(
            WeeklyCheckin.client_user_detail_id == detail.id,
            WeeklyCheckin.checkin_date >= this_monday,
            WeeklyCheckin.checkin_date <= this_sunday,
        ).first() is not None
    checkin = {
        "status": "done" if checkin_done else "pending",
        "coach_name": coach["name"] if coach else None,
        "coach_initials": coach["initials"] if coach else None,
        "requested_fields": ["peso", "fotos", "medidas"],
    }

    return send_response({
        "profile": profile,
        "coach": coach,
        "today": {"weekday": _WEEKDAY_NAMES[today_idx], "day": today.day, "month": _MONTHS_ES[today.month - 1]},
        "week": {"range": week_range, "days": week, "offset": week_offset},
        "streak": streak,
        "routine": routine,
        "menu": menu,
        "checkin": checkin,
        "notifications_unread": 0,  # [pendiente] modelo de notificaciones
    }, "OK")


def _today_menu_summary(db: Session, detail, current_user: User, today_idx: int):
    """Resumen del menú/dieta de hoy: kcal y nº de comidas."""
    from app.models.client_menu import ClientMenu
    from app.models.weekly_menu import WeeklyMenu
    from app.models.nutrition.diet import Diet

    diet = None
    cm = db.query(ClientMenu).filter(
        ClientMenu.client_user_detail_id == detail.id
    ).order_by(ClientMenu.assigned_at.desc(), ClientMenu.id.desc()).first()
    menu_name = None
    if cm:
        wm = db.query(WeeklyMenu).filter(WeeklyMenu.id == cm.menu_id).first()
        if wm:
            menu_name = wm.name
            by_idx = {d.day_index: d for d in wm.days}
            md = by_idx.get(today_idx)
            if md and md.diet_id:
                diet = db.query(Diet).filter(Diet.id == md.diet_id).first()
    if not diet:
        diet = db.query(Diet).filter(
            Diet.user_id == current_user.id
        ).order_by(Diet.created_at.desc()).first()
    if not diet:
        return None

    meals, kcal, prot, carb, fat = _diet_meals_macros(diet)
    return {
        "diet_id": diet.id,
        "name": menu_name or diet.title,
        "kcal": round(kcal) if kcal else None,
        "meals_count": len(meals),
        "weekday": _WEEKDAY_NAMES[today_idx],
    }


_DAY_LABELS = ["L", "M", "X", "J", "V", "S", "D"]
_DAY_NAMES = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]


def _diet_meals_macros(diet):
    """Comidas (con kcal por comida) y macros de una dieta."""
    kcal = diet.calories
    prot = carb = fat = None
    if diet.detail:
        prot, carb, fat = diet.detail.proteins, diet.detail.carbs, diet.detail.fats
    meals = []
    for food in diet.foods:
        mk = 0.0
        for dfa in food.detail:
            al = dfa.aliment
            if al and al.calories and dfa.quantity:
                mk += (al.calories / 100.0) * dfa.quantity
        meals.append({"name": food.name, "time": food.time, "kcal": round(mk) if mk else None})
    meals.sort(key=lambda m: m["time"] or "~")
    return meals, kcal, prot, carb, fat


@router.get("/nutrition", summary="Nutrición del cliente", description="Plan nutricional (dietas) asignado al cliente autenticado, con totales y comidas por día de la semana.")
def client_nutrition(db: Session = Depends(get_db), current_user: User = Depends(require_role_ids(SUPERADMIN, ADMIN, COACH, CLIENT))):
    from app.models.client_menu import ClientMenu
    from app.models.weekly_menu import WeeklyMenu
    from app.models.nutrition.diet import Diet

    empty = {"menu": None, "week_start": None, "days": []}
    detail = _client_detail(db, current_user)
    if not detail:
        return send_response(empty, "Sin cliente")

    today = date.today()
    today_idx = today.weekday()  # 0 = lunes
    week_start = today - timedelta(days=today_idx)

    # 1) Menú semanal asignado (ClientMenu → WeeklyMenu), si existe: cada día
    #    puede tener su propia dieta.
    cm = db.query(ClientMenu).filter(
        ClientMenu.client_user_detail_id == detail.id
    ).order_by(ClientMenu.assigned_at.desc(), ClientMenu.id.desc()).first()
    menu = db.query(WeeklyMenu).filter(WeeklyMenu.id == cm.menu_id).first() if cm else None

    if menu:
        by_idx = {d.day_index: d for d in menu.days}
        days = []
        for i in range(7):
            md = by_idx.get(i)
            diet = db.query(Diet).filter(Diet.id == md.diet_id).first() if (md and md.diet_id) else None
            if diet:
                meals, kcal, prot, carb, fat = _diet_meals_macros(diet)
            else:
                meals, kcal, prot, carb, fat = [], None, None, None, None
            days.append({
                "day_index": i, "label": _DAY_LABELS[i],
                "name": (md.name if (md and md.name) else _DAY_NAMES[i]),
                "date": (week_start + timedelta(days=i)).isoformat(),
                "is_today": i == today_idx, "has_diet": diet is not None,
                "kcal": kcal, "protein": prot, "carbs": carb, "fats": fat, "meals": meals,
            })
        return send_response({"menu": {"name": menu.name}, "week_start": week_start.isoformat(), "days": days}, "OK")

    # 2) Sin menú semanal: usar las dietas que el coach asignó directamente al
    #    cliente (Diet.user_id == cliente). Es el flujo real de client-profile.
    #    La dieta más reciente es el plan activo, mostrado todos los días.
    diet = db.query(Diet).filter(
        Diet.user_id == current_user.id
    ).order_by(Diet.created_at.desc()).first()
    if not diet:
        return send_response(empty, "Sin plan asignado")

    meals, kcal, prot, carb, fat = _diet_meals_macros(diet)
    days = []
    for i in range(7):
        days.append({
            "day_index": i, "label": _DAY_LABELS[i], "name": _DAY_NAMES[i],
            "date": (week_start + timedelta(days=i)).isoformat(),
            "is_today": i == today_idx, "has_diet": True,
            "kcal": kcal, "protein": prot, "carbs": carb, "fats": fat, "meals": meals,
        })
    return send_response({"menu": {"name": diet.title}, "week_start": week_start.isoformat(), "days": days}, "OK")


@router.get("/progress", summary="Progreso del cliente", description="Evolución del cliente: estadísticas, serie de peso y fotos de progreso.")
def client_progress(db: Session = Depends(get_db), current_user: User = Depends(require_role_ids(SUPERADMIN, ADMIN, COACH, CLIENT))):
    from app.models.checkin import WeeklyCheckin

    empty = {"stats": {"weeks": 0, "kg_lost": None, "workouts": 0},
             "weight": {"series": [], "delta": None, "latest": None},
             "photos": {"frontal": [], "lateral": [], "espalda": [], "total": 0}}
    detail = _client_detail(db, current_user)
    if not detail:
        return send_response(empty, "Sin cliente")

    checks = db.query(WeeklyCheckin).filter(
        WeeklyCheckin.client_user_detail_id == detail.id
    ).order_by(WeeklyCheckin.checkin_date.asc()).all()

    workouts = db.query(WorkoutSession).filter(
        WorkoutSession.client_user_detail_id == detail.id
    ).count()

    # Serie de peso
    with_w = [c for c in checks if c.weight is not None]
    series = [{"date": c.checkin_date.isoformat(), "weight": c.weight} for c in with_w]
    delta = latest = None
    if with_w:
        latest = with_w[-1].weight
        if len(with_w) >= 2 and with_w[0].weight is not None:
            delta = round(with_w[-1].weight - with_w[0].weight, 1)

    # Semanas de seguimiento
    weeks = 0
    if checks:
        span = (checks[-1].checkin_date - checks[0].checkin_date).days
        weeks = span // 7 + 1

    kg_lost = round(with_w[0].weight - with_w[-1].weight, 1) if len(with_w) >= 2 else None

    def _photos(attr):
        out = []
        for c in checks:
            url = getattr(c, attr, None)
            if url:
                out.append({"date": c.checkin_date.isoformat(), "url": url, "weight": c.weight})
        return out
    frontal, lateral, espalda = _photos("photo_url"), _photos("photo2"), _photos("photo3")

    return send_response({
        "stats": {"weeks": weeks, "kg_lost": kg_lost, "workouts": workouts},
        "weight": {"series": series, "delta": delta, "latest": latest},
        "photos": {
            "frontal": frontal, "lateral": lateral, "espalda": espalda,
            "total": len(frontal) + len(lateral) + len(espalda),
        },
    }, "OK")


class _ClientCheckinBody(BaseModel):
    weight: Optional[float] = None
    photo_frontal: Optional[str] = None
    photo_lateral: Optional[str] = None
    photo_espalda: Optional[str] = None
    body_fat: Optional[float] = None
    muscle_mass: Optional[float] = None
    waist: Optional[float] = None
    chest: Optional[float] = None
    hips: Optional[float] = None
    arms: Optional[float] = None
    legs: Optional[float] = None
    notes: Optional[str] = None


@router.post("/checkin", summary="Registrar check-in (cliente)", description="El cliente registra/actualiza su check-in de hoy (peso, medidas o fotos).")
def client_checkin(body: _ClientCheckinBody, db: Session = Depends(get_db), current_user: User = Depends(require_role_ids(CLIENT))):
    from app.models.checkin import WeeklyCheckin
    detail = _client_detail(db, current_user)
    if not detail:
        return send_error("Perfil de cliente no encontrado")

    today = date.today()
    ck = db.query(WeeklyCheckin).filter(
        WeeklyCheckin.client_user_detail_id == detail.id,
        WeeklyCheckin.checkin_date == today,
    ).first()
    if not ck:
        coach = _coach_of(db, detail.id)
        ck = WeeklyCheckin(
            client_user_detail_id=detail.id,
            coach_user_detail_id=coach.id if coach else None,
            checkin_date=today,
        )
        db.add(ck)

    # Solo se actualizan los campos que llegan (peso, fotos o medidas)
    mapping = {
        "weight": body.weight, "photo_url": body.photo_frontal, "photo2": body.photo_lateral,
        "photo3": body.photo_espalda, "body_fat": body.body_fat, "muscle_mass": body.muscle_mass,
        "waist": body.waist, "chest": body.chest, "hips": body.hips, "arms": body.arms,
        "legs": body.legs, "notes": body.notes,
    }
    for field, value in mapping.items():
        if value is not None:
            setattr(ck, field, value)

    db.commit()
    db.refresh(ck)
    return send_response({"id": ck.id, "checkin_date": ck.checkin_date.isoformat()}, "Check-in guardado")


class _WorkoutSessionBody(BaseModel):
    routine_id: Optional[int] = None
    duration_min: Optional[int] = None
    rpe: Optional[float] = None
    notes: Optional[str] = None


@router.post("/workout-session", summary="Registrar entrenamiento (cliente)", description="El cliente registra una sesión de entrenamiento completada hoy (duración, RPE, notas).")
def client_workout_session(body: _WorkoutSessionBody, db: Session = Depends(get_db), current_user: User = Depends(require_role_ids(CLIENT))):
    detail = _client_detail(db, current_user)
    if not detail:
        return send_error("Perfil de cliente no encontrado")
    session = WorkoutSession(
        client_user_detail_id=detail.id,
        routine_id=body.routine_id,
        session_date=date.today(),
        duration_min=body.duration_min,
        rpe=body.rpe,
        notes=body.notes,
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return send_response({"id": session.id, "session_date": session.session_date.isoformat()}, "Entrenamiento registrado")


@router.get("/routines", summary="Rutinas del cliente", description="Rutinas (planes) asignadas al cliente autenticado, con sus días y ejercicios.")
def client_routines(db: Session = Depends(get_db), current_user: User = Depends(require_role_ids(SUPERADMIN, ADMIN, COACH, CLIENT))):
    # Reutiliza el serializador del panel del coach (mismo formato de días/bloques/ejercicios).
    from app.routers.routines import _serialize as _serialize_routine
    rows = db.query(Routine).filter(
        Routine.user_id == current_user.id
    ).order_by(Routine.id.desc()).all()
    return send_response([_serialize_routine(r) for r in rows], "OK")


@router.get("/chat", summary="Conversación con el coach", description="Devuelve (creándola si no existe) la conversación individual entre el cliente y su coach.")
def client_chat(db: Session = Depends(get_db), current_user: User = Depends(require_role_ids(CLIENT))):
    """Localiza o crea el chat 1:1 del cliente con su coach.

    El cliente no elige con quién habla: siempre es su coach asignado
    (vía user_parents). Reutiliza el modelo de chat existente para que el
    coach vea la misma conversación desde su panel.
    """
    import uuid
    from datetime import datetime
    from app.models.chat import ChatConversation, ChatParticipant

    detail = _client_detail(db, current_user)
    coach_detail = _coach_of(db, detail.id) if detail else None
    if not coach_detail:
        return send_response({"conversation_id": None, "coach": None}, "Sin coach asignado")

    coach_user_id = coach_detail.user_id
    coach_name = (f"{coach_detail.name or ''} {coach_detail.last_name or ''}").strip() or "Tu coach"
    coach_info = {
        "user_id": coach_user_id,
        "name": coach_name,
        "photo": coach_detail.photo,
        "initials": (coach_name.strip()[:1] or "C").upper(),
    }

    # Conversación individual que contenga a ambos.
    my_conv_ids = [
        p.conversation_id for p in
        db.query(ChatParticipant).filter(ChatParticipant.user_id == current_user.id).all()
    ]
    conv = None
    if my_conv_ids:
        candidates = db.query(ChatConversation).filter(
            ChatConversation.id.in_(my_conv_ids),
            ChatConversation.type == "individual",
        ).all()
        for c in candidates:
            uids = {p.user_id for p in c.participants}
            if coach_user_id in uids:
                conv = c
                break

    if conv is None:
        now = datetime.utcnow()
        conv = ChatConversation(
            id=str(uuid.uuid4()), type="individual", name=None,
            created_by_user_id=current_user.id, created_at=now, updated_at=now,
        )
        db.add(conv)
        db.flush()
        db.add(ChatParticipant(conversation_id=conv.id, user_id=current_user.id, joined_at=now))
        db.add(ChatParticipant(conversation_id=conv.id, user_id=coach_user_id, joined_at=now))
        db.commit()
        db.refresh(conv)

    return send_response({"conversation_id": conv.id, "coach": coach_info}, "OK")
