import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, ForeignKey, DateTime, Boolean, JSON
from sqlalchemy.orm import relationship
from app.database import Base


class Organization(Base):
    __tablename__ = "organizations"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(255), nullable=False)
    slug = Column(String(255), nullable=True, unique=True)
    owner_id = Column(String(36), ForeignKey("user_details.id"), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False, server_default="1")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    owner = relationship("UserDetail", foreign_keys=[owner_id])
    members = relationship(
        "OrganizationMember",
        back_populates="organization",
        cascade="all, delete-orphan",
    )


class OrganizationMember(Base):
    __tablename__ = "organization_members"

    id = Column(Integer, primary_key=True, autoincrement=True)
    organization_id = Column(
        String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    user_detail_id = Column(
        String(36), ForeignKey("user_details.id", ondelete="CASCADE"), nullable=False
    )
    # JSON dict with module-level permissions granted by the org owner
    # e.g. {"manage_org": false, "create_aliments": true, "view_all_clients": false}
    permissions = Column(JSON, nullable=True, default=dict)
    joined_at = Column(DateTime, default=datetime.utcnow)

    organization = relationship("Organization", back_populates="members")
    user_detail = relationship("UserDetail", foreign_keys=[user_detail_id])
