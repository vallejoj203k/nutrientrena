from sqlalchemy.orm import Session
from app.models.role import Role


ROLES = [
    {"id": 1, "name": "Administrador", "slug": "admin"},
    {"id": 2, "name": "Cliente", "slug": "client"},
    {"id": 3, "name": "Instructor", "slug": "instructor"},
]


def seed_roles(db: Session):
    for role_data in ROLES:
        existing = db.query(Role).filter(Role.id == role_data["id"]).first()
        if existing:
            existing.name = role_data["name"]
            existing.slug = role_data["slug"]
        else:
            db.add(Role(id=role_data["id"], name=role_data["name"], slug=role_data["slug"]))
    db.commit()
