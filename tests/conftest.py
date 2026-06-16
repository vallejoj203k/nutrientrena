"""
Test configuration — uses an in-memory SQLite database so no real MySQL
connection is required.  All env vars must be set BEFORE any app module
is imported, which is why the os.environ lines come first.
"""
import os
os.environ["DATABASE_URL"] = "sqlite:///./test_nutrientrena.db"
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-ci-only-not-production")
os.environ.setdefault("AWS_ACCESS_KEY_ID", "test")
os.environ.setdefault("AWS_SECRET_ACCESS_KEY", "test")
os.environ.setdefault("AWS_BUCKET", "test-bucket")
os.environ.setdefault("RESEND_API_KEY", "test")

import uuid
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

TEST_DB_URL = "sqlite:///./test_nutrientrena.db"


@pytest.fixture(scope="session")
def engine():
    import app.models  # registers all SQLAlchemy models with Base.metadata  # noqa: F401
    from app.database import Base

    eng = create_engine(TEST_DB_URL, connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=eng)
    yield eng
    Base.metadata.drop_all(bind=eng)
    if os.path.exists("./test_nutrientrena.db"):
        os.remove("./test_nutrientrena.db")


@pytest.fixture(scope="session")
def db(engine):
    Session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = Session()
    yield session
    session.close()


@pytest.fixture(scope="session")
def client(db):
    from app.database import get_db
    from app.main import app

    app.dependency_overrides[get_db] = lambda: db
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture(scope="session")
def seed(db):
    """Insert minimal rows needed for auth and event tests."""
    from app.models.role import Role
    from app.models.user import User, RoleUser, UserDetail
    from app.core.security import hash_password

    # Roles
    for r in [
        Role(id=1, name="Superadmin", slug="superadmin"),
        Role(id=2, name="Admin", slug="admin"),
        Role(id=5, name="Coach", slug="coach"),
        Role(id=6, name="Client", slug="client"),
    ]:
        db.merge(r)

    # Admin user
    admin = User(
        id=1,
        name="Test Admin",
        email="admin@test.com",
        password=hash_password("Admin123!"),
    )
    db.merge(admin)
    db.flush()

    existing_ru = db.query(RoleUser).filter_by(user_id=1, role_id=1).first()
    if not existing_ru:
        db.add(RoleUser(user_id=1, role_id=1))

    existing_ud = db.query(UserDetail).filter_by(user_id=1).first()
    if not existing_ud:
        db.add(UserDetail(id=str(uuid.uuid4()), user_id=1, name="Test Admin"))

    # Coach user
    coach = User(
        id=2,
        name="Test Coach",
        email="coach@test.com",
        password=hash_password("Coach123!"),
    )
    db.merge(coach)
    db.flush()

    existing_ru2 = db.query(RoleUser).filter_by(user_id=2, role_id=5).first()
    if not existing_ru2:
        db.add(RoleUser(user_id=2, role_id=5))

    existing_ud2 = db.query(UserDetail).filter_by(user_id=2).first()
    if not existing_ud2:
        db.add(UserDetail(id=str(uuid.uuid4()), user_id=2, name="Test Coach"))

    db.commit()
    return {"admin_email": "admin@test.com", "admin_password": "Admin123!",
            "coach_email": "coach@test.com", "coach_password": "Coach123!"}


@pytest.fixture(scope="session")
def admin_token(client, seed):
    r = client.post("/api/auth/login", json={
        "email": seed["admin_email"],
        "password": seed["admin_password"],
    })
    assert r.status_code == 200
    return r.json()["data"]["token"]


@pytest.fixture(scope="session")
def admin_headers(admin_token):
    return {"Authorization": f"Bearer {admin_token}"}


@pytest.fixture(scope="session")
def coach_token(client, seed):
    r = client.post("/api/auth/login", json={
        "email": seed["coach_email"],
        "password": seed["coach_password"],
    })
    assert r.status_code == 200
    return r.json()["data"]["token"]


@pytest.fixture(scope="session")
def coach_headers(coach_token):
    return {"Authorization": f"Bearer {coach_token}"}
