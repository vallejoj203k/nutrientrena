from sqlalchemy.orm import Session
from app.models.role import Role, SUPERADMIN, ADMIN, INSTRUCTOR, CLIENT


def seed_roles(db: Session):
    for name in [SUPERADMIN, ADMIN, INSTRUCTOR, CLIENT]:
        if not db.query(Role).filter(Role.name == name).first():
            db.add(Role(name=name))
    db.commit()
