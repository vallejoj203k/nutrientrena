"""
Run all database seeds.
Usage: python -m app.seeds.run_seeds
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from app.database import SessionLocal, engine, Base
import app.models  # ensure all models are registered

from app.seeds.roles import seed_roles
from app.seeds.parameters import seed_parameters
from app.seeds.countries import seed_countries
from app.seeds.menus import seed_menus
from app.seeds.admin_user import seed_admin_user
from app.seeds.default_form import seed_default_form


def run_all():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        print("Seeding roles...")
        seed_roles(db)
        print("Seeding parameters...")
        seed_parameters(db)
        print("Seeding countries...")
        seed_countries(db)
        print("Seeding menus...")
        seed_menus(db)
        print("Seeding admin user...")
        seed_admin_user(db)
        print("Seeding default form...")
        seed_default_form(db)
        print("Done.")
    finally:
        db.close()


if __name__ == "__main__":
    run_all()
