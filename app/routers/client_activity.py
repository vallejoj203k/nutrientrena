"""Actividad reciente de un cliente — para que el coach esté al día.

Reúne en un solo feed, ordenado por fecha, lo que hace el cliente:
pesos registrados, check-ins enviados, entrenamientos completados (con
sus series), fotos de progreso y tareas marcadas como hechas.

Todo sale de datos que ya existen; no crea tablas nuevas.
"""
from datetime import date, datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.core.dependencies import (
    require_role_ids, verify_client_access,
    SUPERADMIN, ADMIN, COACH,
)
from app.core.responses import send_response
from app.models.checkin import WeeklyCheckin
from app.models.session_log import WorkoutSession
from app.models.calendar_task import CalendarTask

router = APIRouter(prefix="/client-activity", tags=["Client Activity"])


def _iso(d) -> Optional[str]:
    if not d:
        return None
    return d.date().isoformat() if isinstance(d, datetime) else d.isoformat()


@router.get("/{client_id}", summary="Actividad reciente del cliente", description="Feed cronológico de lo que ha hecho el cliente: pesos, check-ins, entrenamientos con sus series, fotos y tareas completadas.")
def client_activity(
    client_id: str,
    days: int = Query(30, ge=1, le=365),
    limit: int = Query(30, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user=Depends(require_role_ids(SUPERADMIN, ADMIN, COACH)),
):
    verify_client_access(client_id, current_user, db)
    since = date.today() - timedelta(days=days)
    items = []

    # ── Check-ins: peso, medidas y fotos ──
    checks = (
        db.query(WeeklyCheckin)
        .filter(
            WeeklyCheckin.client_user_detail_id == client_id,
            WeeklyCheckin.checkin_date >= since,
        )
        .order_by(WeeklyCheckin.checkin_date.desc())
        .all()
    )
    for c in checks:
        if c.weight is not None:
            items.append({
                "type": "peso",
                "date": _iso(c.checkin_date),
                "title": f"Registró su peso: {c.weight} kg",
                "detail": None,
                "ref_id": c.id,
            })
        photos = [p for p in (c.photo_url, c.photo2, c.photo3) if p]
        if photos:
            items.append({
                "type": "fotos",
                "date": _iso(c.checkin_date),
                "title": f"Subió {len(photos)} foto{'s' if len(photos) != 1 else ''} de progreso",
                "detail": None,
                "ref_id": c.id,
                "photos": photos,
            })
        meas = [(lbl, getattr(c, f, None)) for f, lbl in [
            ("body_fat", "% grasa"), ("muscle_mass", "masa muscular"), ("waist", "cintura"),
            ("chest", "pecho"), ("hips", "cadera"), ("arms", "brazos"), ("legs", "piernas"),
        ] if getattr(c, f, None) is not None]
        if meas:
            items.append({
                "type": "medidas",
                "date": _iso(c.checkin_date),
                "title": "Actualizó sus medidas",
                "detail": ", ".join(f"{lbl} {val}" for lbl, val in meas),
                "ref_id": c.id,
            })
        if c.notes:
            items.append({
                "type": "checkin",
                "date": _iso(c.checkin_date),
                "title": "Envió un comentario en su check-in",
                "detail": c.notes,
                "ref_id": c.id,
            })

    # ── Entrenamientos completados (con detalle de series) ──
    sessions = (
        db.query(WorkoutSession)
        .filter(
            WorkoutSession.client_user_detail_id == client_id,
            WorkoutSession.session_date >= since,
        )
        .order_by(WorkoutSession.session_date.desc())
        .all()
    )
    for s in sessions:
        exs = s.exercises or []
        n_sets = sum(len(e.sets or []) for e in exs)
        bits = []
        if exs:
            bits.append(f"{len(exs)} ejercicio{'s' if len(exs) != 1 else ''}")
        if n_sets:
            bits.append(f"{n_sets} serie{'s' if n_sets != 1 else ''}")
        if s.duration_min:
            bits.append(f"{s.duration_min} min")
        if s.rpe:
            bits.append(f"RPE {s.rpe}")
        # Mejor carga de la sesión: útil para ver progresión de un vistazo
        best = None
        for e in exs:
            for st in (e.sets or []):
                if st.weight is not None and (best is None or st.weight > best[1]):
                    best = (e.name or "Ejercicio", st.weight, st.reps)
        items.append({
            "type": "entreno",
            "date": _iso(s.session_date),
            "title": f"Completó «{s.routine.name}»" if s.routine else "Completó un entrenamiento",
            "detail": " · ".join(bits) or None,
            "best": ({"name": best[0], "weight": best[1], "reps": best[2]} if best else None),
            "ref_id": s.id,
        })

    # ── Tareas del coach marcadas como hechas por el cliente ──
    tasks = (
        db.query(CalendarTask)
        .filter(
            CalendarTask.client_user_detail_id == client_id,
            CalendarTask.done == True,  # noqa: E712
            CalendarTask.task_date >= since,
        )
        .order_by(CalendarTask.task_date.desc())
        .all()
    )
    for t in tasks:
        items.append({
            "type": "tarea",
            "date": _iso(t.done_at) or _iso(t.task_date),
            "title": f"Completó la tarea: {t.title or (t.task_type or 'tarea')}",
            "detail": t.notes,
            "task_type": t.task_type,
            "ref_id": t.id,
        })

    items.sort(key=lambda x: (x["date"] or ""), reverse=True)

    # Resumen de los últimos 7 días, para el titular
    last7 = (date.today() - timedelta(days=7)).isoformat()
    recent = [i for i in items if (i["date"] or "") >= last7]
    summary = {
        "entrenos_7d": sum(1 for i in recent if i["type"] == "entreno"),
        "pesos_7d": sum(1 for i in recent if i["type"] == "peso"),
        "tareas_7d": sum(1 for i in recent if i["type"] == "tarea"),
        "last_activity": items[0]["date"] if items else None,
        "days_since_activity": (
            (date.today() - date.fromisoformat(items[0]["date"])).days
            if items and items[0]["date"] else None
        ),
    }

    return send_response({"summary": summary, "items": items[:limit]}, "OK")
