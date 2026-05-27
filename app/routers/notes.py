from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Optional

from app.database import get_db
from app.core.dependencies import require_role_ids, SUPERADMIN, ADMIN, SETTER, CLOSER, COACH
from app.core.responses import send_response, send_error
from app.models.template_notes import TemplateNote
from app.models.note_user import NoteUser
from app.schemas.notes import (
    TemplateNoteCreate, TemplateNoteUpdate, TemplateNoteOut,
    NoteUserCreate, NoteUserUpdate, NoteUserOut,
)

router_templates = APIRouter(prefix="/template-notes", tags=["Template Notes"])
router_notes = APIRouter(prefix="/note-users", tags=["Note Users"])


def _get_template_or_404(db: Session, obj_id: int):
    return db.query(TemplateNote).filter(TemplateNote.id == obj_id).first()


def _get_note_or_404(db: Session, obj_id: int):
    return db.query(NoteUser).filter(NoteUser.id == obj_id).first()


@router_templates.post("")
def create_template(data: TemplateNoteCreate, db: Session = Depends(get_db), current_user=Depends(require_role_ids(SUPERADMIN, ADMIN, SETTER, CLOSER, COACH))):
    obj = TemplateNote(instructor_id=current_user.id, **data.model_dump())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return send_response(TemplateNoteOut.model_validate(obj).model_dump(), "Plantilla creada")


@router_templates.post("/update/{id}")
def update_template(id: int, data: TemplateNoteUpdate, db: Session = Depends(get_db), _=Depends(require_role_ids(SUPERADMIN, ADMIN, SETTER, CLOSER, COACH))):
    obj = _get_template_or_404(db, id)
    if not obj:
        return send_error("Plantilla no encontrada")
    for f, v in data.model_dump(exclude_unset=True).items():
        setattr(obj, f, v)
    db.commit()
    db.refresh(obj)
    return send_response(TemplateNoteOut.model_validate(obj).model_dump(), "Actualizada")


@router_templates.get("/find-all")
def find_all_templates(db: Session = Depends(get_db), current_user=Depends(require_role_ids(SUPERADMIN, ADMIN, SETTER, CLOSER, COACH))):
    items = db.query(TemplateNote).filter(TemplateNote.instructor_id == current_user.id, TemplateNote.state == 1).all()
    return send_response([TemplateNoteOut.model_validate(i).model_dump() for i in items], "OK")


@router_templates.get("/search")
def search_templates(
    search: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user=Depends(require_role_ids(SUPERADMIN, ADMIN, SETTER, CLOSER, COACH)),
):
    q = db.query(TemplateNote).filter(TemplateNote.instructor_id == current_user.id)
    if search:
        q = q.filter(TemplateNote.title.ilike(f"%{search}%"))
    return send_response([TemplateNoteOut.model_validate(i).model_dump() for i in q.all()], "OK")


@router_templates.delete("/delete/{id}")
def delete_template(id: int, db: Session = Depends(get_db), _=Depends(require_role_ids(SUPERADMIN, ADMIN, SETTER, CLOSER, COACH))):
    obj = _get_template_or_404(db, id)
    if not obj:
        return send_error("Plantilla no encontrada")
    db.delete(obj)
    db.commit()
    return send_response(None, "Plantilla eliminada")


@router_notes.post("")
def create_note(data: NoteUserCreate, db: Session = Depends(get_db), current_user=Depends(require_role_ids(SUPERADMIN, ADMIN, SETTER, CLOSER, COACH))):
    obj = NoteUser(instructor_id=current_user.id, **data.model_dump())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return send_response(NoteUserOut.model_validate(obj).model_dump(), "Nota creada")


@router_notes.post("/update/{id}")
def update_note(id: int, data: NoteUserUpdate, db: Session = Depends(get_db), _=Depends(require_role_ids(SUPERADMIN, ADMIN, SETTER, CLOSER, COACH))):
    obj = _get_note_or_404(db, id)
    if not obj:
        return send_error("Nota no encontrada")
    for f, v in data.model_dump(exclude_unset=True).items():
        setattr(obj, f, v)
    db.commit()
    db.refresh(obj)
    return send_response(NoteUserOut.model_validate(obj).model_dump(), "Nota actualizada")


@router_notes.get("/find-all")
def find_all_notes(db: Session = Depends(get_db), current_user=Depends(require_role_ids(SUPERADMIN, ADMIN, SETTER, CLOSER, COACH))):
    items = db.query(NoteUser).filter(NoteUser.instructor_id == current_user.id, NoteUser.state == 1).all()
    return send_response([NoteUserOut.model_validate(i).model_dump() for i in items], "OK")


@router_notes.get("/search")
def search_notes(
    user_id: Optional[int] = Query(None),
    search: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user=Depends(require_role_ids(SUPERADMIN, ADMIN, SETTER, CLOSER, COACH)),
):
    q = db.query(NoteUser).filter(NoteUser.instructor_id == current_user.id)
    if user_id:
        q = q.filter(NoteUser.user_id == user_id)
    if search:
        q = q.filter(NoteUser.title.ilike(f"%{search}%"))
    return send_response([NoteUserOut.model_validate(i).model_dump() for i in q.all()], "OK")


@router_notes.delete("/delete/{id}")
def delete_note(id: int, db: Session = Depends(get_db), _=Depends(require_role_ids(SUPERADMIN, ADMIN, SETTER, CLOSER, COACH))):
    obj = _get_note_or_404(db, id)
    if not obj:
        return send_error("Nota no encontrada")
    db.delete(obj)
    db.commit()
    return send_response(None, "Nota eliminada")
