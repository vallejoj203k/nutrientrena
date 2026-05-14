from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional

from app.database import get_db
from app.core.dependencies import get_current_user
from app.models.template_notes import TemplateNote
from app.models.note_user import NoteUser
from app.schemas.notes import (
    TemplateNoteCreate, TemplateNoteUpdate, TemplateNoteOut,
    NoteUserCreate, NoteUserUpdate, NoteUserOut,
)

router_templates = APIRouter(prefix="/template-notes", tags=["Template Notes"])
router_notes = APIRouter(prefix="/note-users", tags=["Note Users"])


def _get_template_or_404(db: Session, obj_id: int) -> TemplateNote:
    obj = db.query(TemplateNote).filter(TemplateNote.id == obj_id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Plantilla no encontrada")
    return obj


def _get_note_or_404(db: Session, obj_id: int) -> NoteUser:
    obj = db.query(NoteUser).filter(NoteUser.id == obj_id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Nota no encontrada")
    return obj


@router_templates.post("")
def create_template(data: TemplateNoteCreate, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    obj = TemplateNote(instructor_id=current_user.id, **data.model_dump())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return TemplateNoteOut.model_validate(obj)


@router_templates.post("/update/{id}")
def update_template(id: int, data: TemplateNoteUpdate, db: Session = Depends(get_db), _=Depends(get_current_user)):
    obj = _get_template_or_404(db, id)
    for f, v in data.model_dump(exclude_unset=True).items():
        setattr(obj, f, v)
    db.commit()
    db.refresh(obj)
    return TemplateNoteOut.model_validate(obj)


@router_templates.get("/find-all")
def find_all_templates(db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    items = db.query(TemplateNote).filter(TemplateNote.instructor_id == current_user.id, TemplateNote.state == 1).all()
    return [TemplateNoteOut.model_validate(i) for i in items]


@router_templates.get("/search")
def search_templates(search: Optional[str] = Query(None), db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    q = db.query(TemplateNote).filter(TemplateNote.instructor_id == current_user.id)
    if search:
        q = q.filter(TemplateNote.title.ilike(f"%{search}%"))
    return [TemplateNoteOut.model_validate(i) for i in q.all()]


@router_templates.delete("/delete/{id}")
def delete_template(id: int, db: Session = Depends(get_db), _=Depends(get_current_user)):
    obj = _get_template_or_404(db, id)
    db.delete(obj)
    db.commit()
    return {"message": "Plantilla eliminada"}


@router_notes.post("")
def create_note(data: NoteUserCreate, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    obj = NoteUser(instructor_id=current_user.id, **data.model_dump())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return NoteUserOut.model_validate(obj)


@router_notes.post("/update/{id}")
def update_note(id: int, data: NoteUserUpdate, db: Session = Depends(get_db), _=Depends(get_current_user)):
    obj = _get_note_or_404(db, id)
    for f, v in data.model_dump(exclude_unset=True).items():
        setattr(obj, f, v)
    db.commit()
    db.refresh(obj)
    return NoteUserOut.model_validate(obj)


@router_notes.get("/find-all")
def find_all_notes(db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    items = db.query(NoteUser).filter(NoteUser.instructor_id == current_user.id, NoteUser.state == 1).all()
    return [NoteUserOut.model_validate(i) for i in items]


@router_notes.get("/search")
def search_notes(
    user_id: Optional[int] = Query(None),
    search: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    q = db.query(NoteUser).filter(NoteUser.instructor_id == current_user.id)
    if user_id:
        q = q.filter(NoteUser.user_id == user_id)
    if search:
        q = q.filter(NoteUser.title.ilike(f"%{search}%"))
    return [NoteUserOut.model_validate(i) for i in q.all()]


@router_notes.delete("/delete/{id}")
def delete_note(id: int, db: Session = Depends(get_db), _=Depends(get_current_user)):
    obj = _get_note_or_404(db, id)
    db.delete(obj)
    db.commit()
    return {"message": "Nota eliminada"}
