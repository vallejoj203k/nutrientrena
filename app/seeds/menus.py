from sqlalchemy.orm import Session
from app.models.menu import Menu, MenuRole
from app.models.role import Role, ADMIN, INSTRUCTOR


MENU_TREE = [
    {
        "name": "Seguridad", "icon": "setting", "path": None,
        "children": [
            {"name": "Perfiles", "icon": "solution", "path": "/profile-tray"},
            {"name": "Perfil Menú", "icon": "user-switch", "path": "/profile-menu-tray"},
        ],
        "roles": [],
    },
    {
        "name": "Mantenimiento", "icon": "table", "path": None,
        "children": [
            {"name": "Clientes", "icon": "team", "path": "/customer-tray"},
            {"name": "Entrenadores", "icon": "team", "path": "/coach-tray"},
        ],
        "roles": [ADMIN, INSTRUCTOR],
        "children_roles": {
            "Clientes": [ADMIN, INSTRUCTOR],
            "Entrenadores": [ADMIN],
        },
    },
    {
        "name": "Rutinas", "icon": "container", "path": None,
        "children": [
            {"name": "Bandeja Rutinas", "icon": "calendar", "path": "/routine-tray"},
            {"name": "Bandeja Ejercicios", "icon": "share-alt", "path": "/excercise-tray"},
            {"name": "Bandeja Grupo Muscular", "icon": "tags", "path": "/muscle-group-tray"},
        ],
        "roles": [ADMIN, INSTRUCTOR],
    },
    {
        "name": "Nutrición", "icon": "container", "path": None,
        "children": [
            {"name": "Bandeja Dietas", "icon": "file", "path": "/diet-tray"},
            {"name": "Bandeja Tipo Alimento", "icon": "code", "path": "/food-type-tray"},
            {"name": "Bandeja Grupo Alimento", "icon": "bars", "path": "/food-group-tray"},
            {"name": "Bandeja Alimento", "icon": "coffee", "path": "/food-tray"},
            {"name": "Bandeja Receta", "icon": "control", "path": "/recipe-tray"},
        ],
        "roles": [ADMIN, INSTRUCTOR],
    },
]


def seed_menus(db: Session):
    if db.query(Menu).count() > 0:
        return

    role_map = {r.name: r.id for r in db.query(Role).all()}

    for menu_def in MENU_TREE:
        parent = Menu(name=menu_def["name"], icon=menu_def["icon"], path=menu_def["path"])
        db.add(parent)
        db.flush()

        for role_name in menu_def.get("roles", []):
            if role_name in role_map:
                db.add(MenuRole(role_id=role_map[role_name], menu_id=parent.menuId))

        for child_def in menu_def.get("children", []):
            child = Menu(name=child_def["name"], icon=child_def["icon"], path=child_def["path"], menuParentId=parent.menuId)
            db.add(child)
            db.flush()

            child_roles = menu_def.get("children_roles", {}).get(child_def["name"], menu_def.get("roles", []))
            for role_name in child_roles:
                if role_name in role_map:
                    db.add(MenuRole(role_id=role_map[role_name], menu_id=child.menuId))

    db.commit()
