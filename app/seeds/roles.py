from sqlalchemy.orm import Session
from app.models.role import Role


ROLES = [
    {"id": 1, "name": "Superadmin",        "slug": "superadmin"},
    {"id": 2, "name": "Administrador",     "slug": "admin"},
    {"id": 3, "name": "Setter",            "slug": "setter"},
    {"id": 4, "name": "Closer",            "slug": "closer"},
    {"id": 5, "name": "Coach",             "slug": "coach"},
    {"id": 6, "name": "Cliente",           "slug": "client"},
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
