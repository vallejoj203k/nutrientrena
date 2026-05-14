from sqlalchemy.orm import Session
from app.models.user import User
from app.models.role import Role, ADMIN
from app.core.security import hash_password


def seed_admin_user(db: Session):
    if db.query(User).filter(User.email == "admin@nutrientrena.com").first():
        return

    admin_role = db.query(Role).filter(Role.name == ADMIN).first()
    user = User(
        name="Admin",
        last_name="NutrientrenaI",
        email="admin@nutrientrena.com",
        password=hash_password("Admin123!"),
        slug="admin-nutrientrena",
        role_id=admin_role.id if admin_role else None,
        state=1,
    )
    db.add(user)
    db.commit()
