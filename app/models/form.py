import uuid
from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base


PROFILE_FIELD_MAP = {
    # Form field key  →  UserDetail column
    "weight":       "weight",
    "height":       "height",
    "gender_id":    "gender_id",
    "objective_id": "objective_id",
    "activity_id":  "activity_id",
    "phone":        "phone",
    "occupation":   "occupation",
    "country_code": "country_code",
    # New fields (free-text — stored in form_responses only, not in user_details):
    # "training_days", "equipment", "pathologies", "injuries", "food_allergies",
    # "eating_habits", "sleep_hours", "stress_level", "experience", "motivation"
    # are intentionally NOT mapped so coach notes are preserved.
}


class FormTemplate(Base):
    __tablename__ = "form_templates"

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    # Categoría de la plantilla para la Librería › Formularios:
    # "checkin" (seguimiento periódico), "onboarding" (bienvenida) o "survey" (encuesta).
    category = Column(String(30), nullable=False, default="checkin", server_default="checkin")
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    is_default = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    creator = relationship("User")
    fields = relationship("FormTemplateField", back_populates="template",
                          order_by="FormTemplateField.order", cascade="all, delete-orphan")
    assignments = relationship("FormAssignment", back_populates="template")


class FormTemplateField(Base):
    __tablename__ = "form_template_fields"

    id = Column(Integer, primary_key=True, autoincrement=True)
    form_template_id = Column(Integer, ForeignKey("form_templates.id"), nullable=False)
    label = Column(String(255), nullable=False)
    field_type = Column(String(50), nullable=False, default="text")
    field_key = Column(String(100), nullable=False)
    placeholder = Column(String(255), nullable=True)
    options = Column(Text, nullable=True)
    order = Column(Integer, default=0)
    required = Column(Boolean, default=True)

    template = relationship("FormTemplate", back_populates="fields")


class FormAssignment(Base):
    __tablename__ = "form_assignments"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    form_template_id = Column(Integer, ForeignKey("form_templates.id"), nullable=False)
    client_user_detail_id = Column(String(36), ForeignKey("user_details.id"), nullable=False)
    assigned_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    status = Column(String(20), default="pending")
    submitted_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    template = relationship("FormTemplate", back_populates="assignments")
    client = relationship("UserDetail", foreign_keys=[client_user_detail_id])
    assigner = relationship("User", foreign_keys=[assigned_by])
    responses = relationship("FormResponse", back_populates="assignment",
                             cascade="all, delete-orphan")


class FormResponse(Base):
    __tablename__ = "form_responses"

    id = Column(Integer, primary_key=True, autoincrement=True)
    form_assignment_id = Column(String(36), ForeignKey("form_assignments.id"), nullable=False)
    field_key = Column(String(100), nullable=False)
    value = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    assignment = relationship("FormAssignment", back_populates="responses")
