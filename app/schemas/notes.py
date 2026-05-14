from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class TemplateNoteCreate(BaseModel):
    title: str
    content: Optional[str] = None


class TemplateNoteUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    state: Optional[int] = None


class TemplateNoteOut(BaseModel):
    id: int
    instructor_id: int
    title: str
    content: Optional[str] = None
    state: int
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class NoteUserCreate(BaseModel):
    user_id: int
    template_note_id: Optional[int] = None
    title: str
    content: Optional[str] = None


class NoteUserUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    state: Optional[int] = None


class NoteUserOut(BaseModel):
    id: int
    user_id: int
    instructor_id: int
    template_note_id: Optional[int] = None
    title: str
    content: Optional[str] = None
    state: int
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}
