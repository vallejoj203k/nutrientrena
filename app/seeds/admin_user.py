import os
import uuid
from sqlalchemy.orm import Session
from app.models.user import User, UserDetail, RoleUser
from app.models.role import ADMIN
from app.core.security import hash_password

ADMIN_EMAIL = os.environ.get("ADMIN_EMAIL", "admin@nutrientrena.com")


def seed_admin_user(db: Session):
    if db.query(User).filter(User.email == ADMIN_EMAIL).first():
        return

    user = User(
        name="Admin Nutrientrena",
        email=ADMIN_EMAIL,
        password=hash_password("Admin123!"),
    )
    db.add(user)
    db.flush()

    db.add(RoleUser(user_id=user.id, role_id=ADMIN))

    db.add(UserDetail(
        id=str(uuid.uuid4()),
        user_id=user.id,
        name="Admin",
        last_name="Nutrientrena",
    ))

    db.commit()
