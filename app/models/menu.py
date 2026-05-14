from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship

from app.database import Base


class Menu(Base):
    __tablename__ = "menus"

    menuId = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(150), nullable=False)
    menuParentId = Column(Integer, ForeignKey("menus.menuId"), nullable=True)
    icon = Column(String(100), nullable=True)
    path = Column(String(200), nullable=True)

    children = relationship("Menu", backref="parent", remote_side=[menuId])
    menu_roles = relationship("MenuRole", back_populates="menu")


class MenuRole(Base):
    __tablename__ = "menu_roles"

    id = Column(Integer, primary_key=True, autoincrement=True)
    role_id = Column(Integer, ForeignKey("roles.id"), nullable=False)
    menu_id = Column(Integer, ForeignKey("menus.menuId"), nullable=False)

    role = relationship("Role", back_populates="menu_roles")
    menu = relationship("Menu", back_populates="menu_roles")
