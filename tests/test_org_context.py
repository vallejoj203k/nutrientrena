"""Fase 2: un ADMIN dueño de una organización real actúa DENTRO de ella, en
vez de tener siempre bypass total.

Antes, `get_org_context` cortaba con "si es SUPERADMIN o ADMIN, org_id=None,
is_owner=True" sin mirar si ese ADMIN era en realidad dueño de una
organización (la migración que dio de alta `organizations` le creó una a cada
ADMIN/COACH existente). Eso hacía indistinguibles "Oswal como Alzum" y "Oswal
como NutriEntrena": un ADMIN nunca podía actuar dentro de su propia
organización, siempre por encima de todas — lo contrario de lo que pide el
documento de jerarquía.

SUPERADMIN no cambia: sigue con bypass incondicional, sea cual sea su
situación de organización.
"""
from app.core.dependencies import get_org_context
from app.database import SessionLocal
from app.models.organization import Organization, OrganizationMember
from app.models.routine import Routine
from app.models.user import User

from tests.test_org_scope import _crear_organizacion, _agregar_miembro, _crear_usuario


def _contexto_de(user_id):
    """Resuelve el OrgContext de un usuario ya creado, fuera de una petición HTTP."""
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.id == user_id).first()
        # get_org_context es una dependencia FastAPI: se llama tal cual, con
        # el mismo current_user/db que recibiría vía Depends.
        return get_org_context(current_user=user, db=db)
    finally:
        db.close()


def test_superadmin_conserva_el_bypass_incondicional(client, seed, admin_headers):
    """seed() crea el usuario "admin" con role_id=1 (SUPERADMIN): debe seguir
    viendo org_id=None, is_owner=True, tenga o no una organización."""
    db = SessionLocal()
    try:
        superadmin = db.query(User).filter(User.email == seed["admin_email"]).first()
        uid = superadmin.id
    finally:
        db.close()

    ctx = _contexto_de(uid)
    assert ctx.org_id is None
    assert ctx.is_owner is True


def test_admin_dueno_de_una_organizacion_actua_dentro_de_ella(client, seed, admin_headers):
    """El caso central de la Fase 2: un ADMIN que de verdad es dueño de una
    organización deja de tener bypass y pasa a actuar en su propio contexto."""
    uid, det, _h = _crear_usuario(client, admin_headers, "admin.duenio@nutrientrena-qa.com", role_id=2)
    org_id = _crear_organizacion(det, "NutriEntrena (admin dueño)")

    ctx = _contexto_de(uid)
    assert ctx.org_id == org_id
    assert ctx.is_owner is True


def test_admin_miembro_de_otra_organizacion_actua_como_delegado(client, seed, admin_headers):
    """Un ADMIN que es miembro (no dueño) de la organización de otra persona
    queda con is_owner=False y sus permisos delegados, igual que un coach
    miembro — el rol ADMIN no le da bypass si tiene organización asignada."""
    uid_dueno, det_dueno, _h1 = _crear_usuario(client, admin_headers, "dueno.para_admin_miembro@nutrientrena-qa.com", role_id=2)
    uid_admin, det_admin, _h2 = _crear_usuario(client, admin_headers, "admin.miembro@nutrientrena-qa.com", role_id=2)
    org_id = _crear_organizacion(det_dueno, "Organización con ADMIN delegado")
    _agregar_miembro(org_id, det_admin)

    ctx = _contexto_de(uid_admin)
    assert ctx.org_id == org_id
    assert ctx.is_owner is False


def test_admin_sin_organizacion_conserva_el_bypass_de_antes(client, seed, admin_headers):
    """Sin organización propia ni membresía, un ADMIN no tiene dónde
    "meterse": conserva el bypass total que ya tenía, para no romper cuentas
    de administración de plataforma que nunca pasaron por organizaciones."""
    uid, _det, _h = _crear_usuario(client, admin_headers, "admin.sin_org@nutrientrena-qa.com", role_id=2)

    ctx = _contexto_de(uid)
    assert ctx.org_id is None
    assert ctx.is_owner is True


def test_admin_dueno_crea_contenido_dentro_de_su_organizacion(client, seed, admin_headers):
    """Extremo a extremo: el ADMIN dueño de una organización ya no crea
    contenido "de plataforma" (organization_id NULL) sino de SU organización,
    y ese contenido queda protegido frente a otras organizaciones —
    exactamente el comportamiento que describe el documento de jerarquía."""
    uid, det, h_admin = _crear_usuario(client, admin_headers, "admin.crea_contenido@nutrientrena-qa.com", role_id=2)
    org_id = _crear_organizacion(det, "NutriEntrena (contenido de admin)")

    r = client.post("/api/routines", headers=h_admin, json={"name": "Rutina del admin dueño"})
    assert r.status_code == 200, r.text
    routine_id = r.json()["data"]["id"]

    db = SessionLocal()
    try:
        routine = db.query(Routine).filter_by(id=routine_id).first()
        assert routine.organization_id == org_id, (
            "antes de la Fase 2 esto habría quedado en NULL (contenido de plataforma)"
        )
    finally:
        db.close()

    # Un coach de OTRA organización no debe verla — antes de este cambio,
    # org_id=NULL la habría hecho global para cualquiera.
    _uid_b, _det_b, h_otra_org = _crear_usuario(client, admin_headers, "coach.otra_org.para_admin@nutrientrena-qa.com", role_id=5)
    _crear_organizacion(_det_b, "Otra organización, ajena al admin")
    nombres = [x["name"] for x in client.get("/api/routines/findAll", headers=h_otra_org).json()["data"]]
    assert "Rutina del admin dueño" not in nombres
