from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship
from app.database import Base

SUPERADMIN = 1
ADMIN      = 2
SETTER     = 3
CLOSER     = 4
COACH      = 5
CLIENT     = 6


class Role(Base):
    __tablename__ = "roles"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False, unique=True)
    slug = Column(String(100), nullable=True, unique=True)

    role_users = relationship("RoleUser", back_populates="role")
    menu_roles = relationship("MenuRole", back_populates="role")
