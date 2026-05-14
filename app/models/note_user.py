from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base


class NoteUser(Base):
    __tablename__ = "note_users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    instructor_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    template_note_id = Column(Integer, ForeignKey("template_notes.id"), nullable=True)
    title = Column(String(255), nullable=False)
    content = Column(Text, nullable=True)
    state = Column(Integer, default=1)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="notes_user", foreign_keys=[user_id])
    instructor = relationship("User", foreign_keys=[instructor_id])
    template = relationship("TemplateNote")
