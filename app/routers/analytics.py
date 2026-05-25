from datetime import datetime, date
from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import UserDetail, RoleUser, UserParent
from app.models.role import COACH, CLIENT
from app.models.checkin import WeeklyCheckin
from app.models.parameter import ParameterDetail
from app.core.responses import send_response

router = APIRouter(prefix="/analytics", tags=["Analytics"])


def _client_ids(db: Session) -> list[int]:
    return [r.user_id for r in db.query(RoleUser).filter(RoleUser.role_id == CLIENT).all()]


def _coach_ids(db: Session) -> list[int]:
    return [r.user_id for r in db.query(RoleUser).filter(RoleUser.role_id == COACH).all()]


def _get_client_details(db: Session, coach_id: Optional[str] = None):
    client_user_ids = _client_ids(db)
    q = db.query(UserDetail).filter(UserDetail.user_id.in_(client_user_ids))
    if coach_id:
        assigned = [
            up.user_detail_id
            for up in db.query(UserParent)
            .filter(UserParent.parent_user_detail_id == coach_id)
            .all()
        ]
        q = q.filter(UserDetail.id.in_(assigned))
    return q.all()


@router.get("/overview")
def overview(
    coach_id: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
):
    """
    Totales generales: clientes, activos, nuevos este mes, coaches.
    """
    clients = _get_client_details(db, coach_id)
    total = len(clients)

    now = datetime.utcnow()
    new_this_month = sum(
        1 for c in clients
        if c.created_at and c.created_at.year == now.year and c.created_at.month == now.month
    )

    # "Activo" = tiene al menos un check-in en los últimos 30 días
    thirty_days_ago = date.today().replace(day=max(1, date.today().day - 30))
    client_ids = [c.id for c in clients]
    recent_checkin_ids = {
        row.client_user_detail_id
        for row in db.query(WeeklyCheckin.client_user_detail_id)
        .filter(
            WeeklyCheckin.client_user_detail_id.in_(client_ids),
            WeeklyCheckin.checkin_date >= thirty_days_ago,
        )
        .distinct()
        .all()
    }
    active = len(recent_checkin_ids)

    # Coaches
    total_coaches = len(_coach_ids(db)) if not coach_id else 1

    # Total check-ins globales
    total_checkins = (
        db.query(func.count(WeeklyCheckin.id))
        .filter(WeeklyCheckin.client_user_detail_id.in_(client_ids))
        .scalar()
        or 0
    )

    return send_response({
        "total_clients":   total,
        "active_clients":  active,
        "inactive_clients": total - active,
        "new_this_month":  new_this_month,
        "total_coaches":   total_coaches,
        "total_checkins":  total_checkins,
    }, "ok")


@router.get("/states")
def states_distribution(
    coach_id: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
):
    """
    Distribución de clientes por estado — para gráfico de barras/dona.
    """
    clients = _get_client_details(db, coach_id)

    # Group by status_id
    counts: dict[int, int] = {}
    for c in clients:
        sid = c.status_id or 0
        counts[sid] = counts.get(sid, 0) + 1

    # Resolve status names
    status_ids = [sid for sid in counts if sid != 0]
    names: dict[int, str] = {}
    if status_ids:
        rows = db.query(ParameterDetail).filter(ParameterDetail.id.in_(status_ids)).all()
        names = {r.id: r.description for r in rows}

    result = [
        {
            "status_id":   sid,
            "status_name": names.get(sid, "Sin estado") if sid else "Sin estado",
            "count":       cnt,
            "percentage":  round(cnt / len(clients) * 100, 1) if clients else 0,
        }
        for sid, cnt in sorted(counts.items(), key=lambda x: -x[1])
    ]

    return send_response({"total": len(clients), "distribution": result}, "ok")


@router.get("/checkins")
def checkin_stats(
    coach_id: Optional[str] = Query(None),
    from_date: Optional[date] = Query(None, alias="from"),
    to_date: Optional[date] = Query(None, alias="to"),
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
):
    """
    Métricas de check-ins: peso promedio perdido, adherencia, totales.
    """
    clients = _get_client_details(db, coach_id)
    client_ids = [c.id for c in clients]

    q = db.query(WeeklyCheckin).filter(WeeklyCheckin.client_user_detail_id.in_(client_ids))
    if from_date:
        q = q.filter(WeeklyCheckin.checkin_date >= from_date)
    if to_date:
        q = q.filter(WeeklyCheckin.checkin_date <= to_date)
    checkins = q.order_by(WeeklyCheckin.client_user_detail_id, WeeklyCheckin.checkin_date).all()

    total_checkins = len(checkins)

    # Adherence: % of clients with at least one check-in
    clients_with_checkin = len({c.client_user_detail_id for c in checkins})
    adherence = round(clients_with_checkin / len(clients) * 100, 1) if clients else 0

    # Average weight change per client (last - first)
    by_client: dict[str, list] = {}
    for ck in checkins:
        if ck.weight is not None:
            by_client.setdefault(ck.client_user_detail_id, []).append(ck.weight)

    weight_changes = [
        weights[-1] - weights[0]
        for weights in by_client.values()
        if len(weights) >= 2
    ]
    avg_weight_change = (
        round(sum(weight_changes) / len(weight_changes), 2) if weight_changes else None
    )
    clients_losing = sum(1 for d in weight_changes if d < 0)
    clients_gaining = sum(1 for d in weight_changes if d > 0)

    # Weekly trend — checkins per week (last 8 weeks)
    from collections import defaultdict
    weekly: dict[str, int] = defaultdict(int)
    for ck in checkins:
        if ck.checkin_date:
            iso = ck.checkin_date.isocalendar()
            key = f"{iso[0]}-W{iso[1]:02d}"
            weekly[key] += 1
    weekly_trend = [{"week": k, "count": v} for k, v in sorted(weekly.items())[-8:]]

    return send_response({
        "total_checkins":      total_checkins,
        "clients_with_checkin": clients_with_checkin,
        "adherence_pct":       adherence,
        "avg_weight_change_kg": avg_weight_change,
        "clients_losing_weight": clients_losing,
        "clients_gaining_weight": clients_gaining,
        "weekly_trend":        weekly_trend,
    }, "ok")


@router.get("/coaches")
def coaches_stats(
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
):
    """
    Métricas por coach: clientes asignados, check-ins recibidos.
    """
    coach_user_ids = _coach_ids(db)
    coach_details = (
        db.query(UserDetail)
        .filter(UserDetail.user_id.in_(coach_user_ids))
        .all()
    )

    result = []
    for coach in coach_details:
        assigned = (
            db.query(UserParent)
            .filter(UserParent.parent_user_detail_id == coach.id)
            .count()
        )
        checkins_received = (
            db.query(WeeklyCheckin)
            .filter(WeeklyCheckin.coach_user_detail_id == coach.id)
            .count()
        )
        result.append({
            "coach_id":          coach.id,
            "coach_name":        f"{coach.name} {coach.last_name or ''}".strip(),
            "clients_assigned":  assigned,
            "checkins_received": checkins_received,
        })

    result.sort(key=lambda x: -x["clients_assigned"])

    return send_response({"coaches": result, "total_coaches": len(result)}, "ok")
