from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Optional

from app.database import get_db
from app.core.dependencies import require_role_ids, get_current_user, SUPERADMIN, ADMIN, SETTER, CLOSER, COACH
from app.core.responses import send_response, send_error
from app.models.program import Program, ProgramPhase, ProgramClient
from app.models.user import User
from app.schemas.program import ProgramCreate, ProgramUpdate, ProgramAssignRequest, ProgramOut, PhaseOut, ClientMini

router = APIRouter(prefix="/programs", tags=["Programs"])

ALLOWED = (SUPERADMIN, ADMIN, SETTER, CLOSER, COACH)


def _serialize(p: Program) -> dict:
    phases = sorted(p.phases, key=lambda x: x.order)
    clients = []
    for pc in p.clients:
        u = pc.client
        if u:
            name = u.name or u.email
            initials = "".join(w[0].upper() for w in name.split()[:2]) if name else "?"
            clients.append({"id": u.id, "name": name, "email": u.email, "initials": initials})
    return {
        "id": p.id,
        "name": p.name,
        "category": p.category,
        "description": p.description,
        "status": p.status,
        "checkins_count": p.checkins_count,
        "coach_id": p.coach_id,
        "created_at": p.created_at.isoformat() if p.created_at else None,
        "updated_at": p.updated_at.isoformat() if p.updated_at else None,
        "phases": [{"id": ph.id, "name": ph.name, "weeks": ph.weeks, "order": ph.order} for ph in phases],
        "total_weeks": sum(ph.weeks for ph in phases),
        "clients": clients,
    }


def _get_or_404(db: Session, program_id: int, current_user: User):
    p = db.query(Program).filter(Program.id == program_id).first()
    if not p:
        return None
    return p


# ── List ──────────────────────────────────────────────────────────────────────
@router.get("", summary="Listar programas")
def list_programs(
    category: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _=Depends(require_role_ids(*ALLOWED)),
):
    q = db.query(Program).filter(Program.coach_id == current_user.id)
    if category:
        q = q.filter(Program.category == category)
    if status:
        q = q.filter(Program.status == status)
    if search:
        q = q.filter(Program.name.ilike(f"%{search}%"))
    programs = q.order_by(Program.created_at.desc()).all()
    return send_response([_serialize(p) for p in programs], "OK")


# ── Create ────────────────────────────────────────────────────────────────────
@router.post("", summary="Crear programa")
def create_program(
    data: ProgramCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _=Depends(require_role_ids(*ALLOWED)),
):
    program = Program(
        name=data.name,
        category=data.category,
        description=data.description,
        checkins_count=data.checkins_count,
        coach_id=current_user.id,
    )
    db.add(program)
    db.flush()

    for idx, phase in enumerate(data.phases):
        db.add(ProgramPhase(
            program_id=program.id,
            name=phase.name,
            weeks=phase.weeks,
            order=phase.order if phase.order else idx,
        ))

    db.commit()
    db.refresh(program)
    return send_response(_serialize(program), "Programa creado")


# ── Get one ───────────────────────────────────────────────────────────────────
@router.get("/{id}", summary="Ver programa")
def get_program(
    id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _=Depends(require_role_ids(*ALLOWED)),
):
    p = _get_or_404(db, id, current_user)
    if not p:
        return send_error("Programa no encontrado", 404)
    return send_response(_serialize(p), "OK")


# ── Update ────────────────────────────────────────────────────────────────────
@router.put("/{id}", summary="Actualizar programa")
def update_program(
    id: int,
    data: ProgramUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _=Depends(require_role_ids(*ALLOWED)),
):
    p = _get_or_404(db, id, current_user)
    if not p:
        return send_error("Programa no encontrado", 404)

    for field in ("name", "category", "description", "status", "checkins_count"):
        val = getattr(data, field, None)
        if val is not None:
            setattr(p, field, val)

    if data.phases is not None:
        # Replace phases entirely
        for old in p.phases:
            db.delete(old)
        db.flush()
        for idx, phase in enumerate(data.phases):
            db.add(ProgramPhase(
                program_id=p.id,
                name=phase.name,
                weeks=phase.weeks,
                order=phase.order if phase.order else idx,
            ))

    db.commit()
    db.refresh(p)
    return send_response(_serialize(p), "Programa actualizado")


# ── Delete ────────────────────────────────────────────────────────────────────
@router.delete("/{id}", summary="Eliminar programa")
def delete_program(
    id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _=Depends(require_role_ids(*ALLOWED)),
):
    p = _get_or_404(db, id, current_user)
    if not p:
        return send_error("Programa no encontrado", 404)
    db.delete(p)
    db.commit()
    return send_response(None, "Programa eliminado")


# ── Assign clients ────────────────────────────────────────────────────────────
@router.post("/{id}/assign", summary="Asignar clientes a programa")
def assign_clients(
    id: int,
    data: ProgramAssignRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _=Depends(require_role_ids(*ALLOWED)),
):
    p = _get_or_404(db, id, current_user)
    if not p:
        return send_error("Programa no encontrado", 404)

    existing_ids = {pc.client_id for pc in p.clients}
    for client_id in data.client_ids:
        if client_id not in existing_ids:
            db.add(ProgramClient(program_id=p.id, client_id=client_id))

    db.commit()
    db.refresh(p)
    return send_response(_serialize(p), "Clientes asignados")


# ── Unassign client ───────────────────────────────────────────────────────────
@router.delete("/{id}/clients/{client_id}", summary="Quitar cliente del programa")
def unassign_client(
    id: int,
    client_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _=Depends(require_role_ids(*ALLOWED)),
):
    p = _get_or_404(db, id, current_user)
    if not p:
        return send_error("Programa no encontrado", 404)

    pc = db.query(ProgramClient).filter_by(program_id=id, client_id=client_id).first()
    if pc:
        db.delete(pc)
        db.commit()
    db.refresh(p)
    return send_response(_serialize(p), "Cliente eliminado del programa")


# ── Duplicate ─────────────────────────────────────────────────────────────────
@router.post("/{id}/duplicate", summary="Duplicar programa")
def duplicate_program(
    id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _=Depends(require_role_ids(*ALLOWED)),
):
    p = _get_or_404(db, id, current_user)
    if not p:
        return send_error("Programa no encontrado", 404)

    clone = Program(
        name=p.name + " (copia)",
        category=p.category,
        description=p.description,
        checkins_count=p.checkins_count,
        coach_id=current_user.id,
    )
    db.add(clone)
    db.flush()

    for ph in sorted(p.phases, key=lambda x: x.order):
        db.add(ProgramPhase(program_id=clone.id, name=ph.name, weeks=ph.weeks, order=ph.order))

    db.commit()
    db.refresh(clone)
    return send_response(_serialize(clone), "Programa duplicado")
