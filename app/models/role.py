from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship

from app.database import Base

SUPERADMIN = "SUPERADMIN"
ADMIN = "ADMIN"
INSTRUCTOR = "INSTRUCTOR"
CLIENT = "CLIENT"


class Role(Base):
    __tablename__ = "roles"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False, unique=True)

    users = relationship("User", back_populates="role")
    menu_roles = relationship("MenuRole", back_populates="role")
