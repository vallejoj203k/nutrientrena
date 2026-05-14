from sqlalchemy.orm import Session
from app.models.menu import Menu, MenuRole
from app.models.role import Role


ADMIN_SLUG = "admin"
INSTRUCTOR_SLUG = "instructor"

MENU_TREE = [
    {
        "name": "Seguridad", "icon": "setting", "path": None,
        "roles": [],
        "children": [
            {"name": "Perfiles", "icon": "solution", "path": "/profile-tray", "roles": []},
            {"name": "Perfil Menú", "icon": "user-switch", "path": "/profile-menu-tray", "roles": []},
        ],
    },
    {
        "name": "Mantenimiento", "icon": "table", "path": None,
        "roles": [ADMIN_SLUG, INSTRUCTOR_SLUG],
        "children": [
            {"name": "Clientes", "icon": "team", "path": "/customer-tray", "roles": [ADMIN_SLUG, INSTRUCTOR_SLUG]},
            {"name": "Entrenadores", "icon": "team", "path": "/coach-tray", "roles": [ADMIN_SLUG]},
        ],
    },
    {
        "name": "Rutinas", "icon": "container", "path": None,
        "roles": [ADMIN_SLUG, INSTRUCTOR_SLUG],
        "children": [
            {"name": "Bandeja Rutinas", "icon": "calendar", "path": "/routine-tray", "roles": [ADMIN_SLUG, INSTRUCTOR_SLUG]},
            {"name": "Bandeja Ejercicios", "icon": "share-alt", "path": "/excercise-tray", "roles": [ADMIN_SLUG, INSTRUCTOR_SLUG]},
            {"name": "Bandeja Grupo Muscular", "icon": "tags", "path": "/muscle-group-tray", "roles": [ADMIN_SLUG, INSTRUCTOR_SLUG]},
        ],
    },
    {
        "name": "Nutrición", "icon": "container", "path": None,
        "roles": [ADMIN_SLUG, INSTRUCTOR_SLUG],
        "children": [
            {"name": "Bandeja Dietas", "icon": "file", "path": "/diet-tray", "roles": [ADMIN_SLUG, INSTRUCTOR_SLUG]},
            {"name": "Bandeja Tipo Alimento", "icon": "code", "path": "/food-type-tray", "roles": [ADMIN_SLUG, INSTRUCTOR_SLUG]},
            {"name": "Bandeja Grupo Alimento", "icon": "bars", "path": "/food-group-tray", "roles": [ADMIN_SLUG, INSTRUCTOR_SLUG]},
            {"name": "Bandeja Alimento", "icon": "coffee", "path": "/food-tray", "roles": [ADMIN_SLUG, INSTRUCTOR_SLUG]},
            {"name": "Bandeja Receta", "icon": "control", "path": "/recipe-tray", "roles": [ADMIN_SLUG, INSTRUCTOR_SLUG]},
        ],
    },
]


def seed_menus(db: Session):
    if db.query(Menu).count() > 0:
        return

    role_map = {r.slug: r.id for r in db.query(Role).all() if r.slug}

    for menu_def in MENU_TREE:
        parent = Menu(name=menu_def["name"], icon=menu_def["icon"], path=menu_def["path"])
        db.add(parent)
        db.flush()

        for slug in menu_def.get("roles", []):
            if slug in role_map:
                db.add(MenuRole(role_id=role_map[slug], menu_id=parent.menuId))

        for child_def in menu_def.get("children", []):
            child = Menu(
                name=child_def["name"],
                icon=child_def["icon"],
                path=child_def["path"],
                menuParentId=parent.menuId,
            )
            db.add(child)
            db.flush()

            for slug in child_def.get("roles", []):
                if slug in role_map:
                    db.add(MenuRole(role_id=role_map[slug], menu_id=child.menuId))

    db.commit()
