"""Abrir el contenido de plataforma desde la Librería del coach.

En la Librería salen listadas las rutinas y dietas del catálogo común, pero al
pulsar una respondía 403: "Error al cargar la rutina", y la dieta se abría con
guiones en todo. La pantalla de detalle usaba la comprobación de EDITAR, y esa
solo deja pasar lo de tu propia organización — el catálogo no es de ninguna.

Ver y editar son cosas distintas, y esto sujeta las dos:

  · Que el coach pueda ABRIR el catálogo común, tenga organización o no.
  · Que siga sin poder CAMBIARLO ni borrarlo, que era el motivo de la
    comprobación.
  · Que no se cuele lo que no es catálogo: el contenido privado de otro coach,
    ni la dieta del cliente de otra cuenta.
"""
import uuid

from app.database import SessionLocal
from app.models.nutrition.diet import Diet
from app.models.routine import Routine
from app.models.user import UserParent

from tests.test_org_scope import (
    _crear_coach, _crear_organizacion, _crear_usuario, _agregar_miembro,
)

PLATAFORMA = {"X-Organization-Id": "plataforma"}

# El super-admin del banco de pruebas (`conftest.py`): es de quien es el
# catálogo de plataforma.
SUPERADMIN_ID = 1


def _de_plataforma(suf, dueno=None):
    """Catálogo común: sin organización y de una cuenta de plataforma."""
    db = SessionLocal()
    try:
        rut = Routine(name=f"Full Body {suf}", organization_id=None, user_id=dueno)
        dieta = Diet(title=f"Low Carb {suf}", organization_id=None, user_id=dueno)
        db.add(rut)
        db.add(dieta)
        db.commit()
        return rut.id, dieta.id
    finally:
        db.close()


def _de_la_cuenta(suf, org_id, dueno):
    db = SessionLocal()
    try:
        rut = Routine(name=f"Privada {suf}", organization_id=org_id, user_id=dueno)
        dieta = Diet(title=f"Privada {suf}", organization_id=org_id, user_id=dueno)
        db.add(rut)
        db.add(dieta)
        db.commit()
        return rut.id, dieta.id
    finally:
        db.close()


def _coach_con_org(client, admin_headers, suf, quien="a"):
    uid, det, h = _crear_coach(client, admin_headers, f"coach.vc.{quien}.{suf}@nutrientrena-qa.com")
    org = _crear_organizacion(det, f"Org {quien} {suf}")
    _agregar_miembro(org, det)
    return uid, det, h, org


# ── El caso reportado ──────────────────────────────────────────────────────

def test_UN_COACH_ABRE_LA_RUTINA_DE_PLATAFORMA(client, seed, admin_headers):
    suf = uuid.uuid4().hex[:8]
    _uid, _det, h, _org = _coach_con_org(client, admin_headers, suf)
    rut_id, _d = _de_plataforma(suf, dueno=SUPERADMIN_ID)

    r = client.get(f"/api/routines/{rut_id}/edit", headers=h)
    assert r.status_code == 200, r.text
    assert r.json()["data"]["name"].startswith("Full Body"), r.json()


def test_UN_COACH_ABRE_LA_DIETA_DE_PLATAFORMA(client, seed, admin_headers):
    suf = uuid.uuid4().hex[:8]
    _uid, _det, h, _org = _coach_con_org(client, admin_headers, suf)
    _r, dieta_id = _de_plataforma(suf, dueno=SUPERADMIN_ID)

    r = client.get(f"/api/diets/{dieta_id}/edit", headers=h)
    assert r.status_code == 200, r.text
    assert r.json()["data"]["title"].startswith("Low Carb"), r.json()


def test_un_coach_SIN_organizacion_tambien(client, seed, admin_headers):
    suf = uuid.uuid4().hex[:8]
    _uid, _det, h = _crear_coach(client, admin_headers, f"coach.solo.{suf}@nutrientrena-qa.com")
    rut_id, dieta_id = _de_plataforma(suf, dueno=SUPERADMIN_ID)

    assert client.get(f"/api/routines/{rut_id}/edit", headers=h).status_code == 200
    assert client.get(f"/api/diets/{dieta_id}/edit", headers=h).status_code == 200


def test_el_catalogo_sin_dueno_tambien_se_abre(client, seed, admin_headers):
    """Las filas viejas del catálogo no tienen a nadie detrás."""
    suf = uuid.uuid4().hex[:8]
    _uid, _det, h, _org = _coach_con_org(client, admin_headers, suf)
    rut_id, dieta_id = _de_plataforma(suf, dueno=None)

    assert client.get(f"/api/routines/{rut_id}/edit", headers=h).status_code == 200
    assert client.get(f"/api/diets/{dieta_id}/edit", headers=h).status_code == 200


def test_y_su_pdf_se_descarga(client, seed, admin_headers):
    suf = uuid.uuid4().hex[:8]
    _uid, _det, h, _org = _coach_con_org(client, admin_headers, suf)
    rut_id, dieta_id = _de_plataforma(suf, dueno=SUPERADMIN_ID)

    assert client.get(f"/api/routines/{rut_id}/pdf", headers=h).status_code == 200
    assert client.get(f"/api/diets/{dieta_id}/pdf", headers=h).status_code == 200


# ── Verlo no es poder cambiarlo ────────────────────────────────────────────

def test_VERLO_NO_ES_PODER_EDITARLO(client, seed, admin_headers):
    """Es el motivo por el que estaba la comprobación: el catálogo lo mantiene
    la plataforma, y un coach no puede reescribírselo a todas las cuentas."""
    suf = uuid.uuid4().hex[:8]
    _uid, _det, h, _org = _coach_con_org(client, admin_headers, suf)
    rut_id, dieta_id = _de_plataforma(suf, dueno=SUPERADMIN_ID)

    r = client.put(f"/api/routines/{rut_id}/update", headers=h,
                   json={"name": "Mía ahora", "days_list": []})
    assert r.status_code == 403, r.status_code
    r = client.put(f"/api/diets/{dieta_id}/update", headers=h,
                   json={"id": dieta_id, "title": "Mía ahora"})
    assert r.status_code == 403, r.status_code


def test_ni_borrarlo(client, seed, admin_headers):
    suf = uuid.uuid4().hex[:8]
    _uid, _det, h, _org = _coach_con_org(client, admin_headers, suf)
    rut_id, dieta_id = _de_plataforma(suf, dueno=SUPERADMIN_ID)

    assert client.delete(f"/api/routines/{rut_id}", headers=h).status_code == 403
    assert client.delete(f"/api/diets/{dieta_id}", headers=h).status_code == 403


# ── Lo que NO es catálogo sigue cerrado ────────────────────────────────────

def test_NO_SE_ABRE_LO_PRIVADO_DE_OTRA_CUENTA(client, seed, admin_headers):
    suf = uuid.uuid4().hex[:8]
    _u1, _d1, h_mio, _o1 = _coach_con_org(client, admin_headers, suf, "mio")
    u2, _d2, _h2, org_otro = _coach_con_org(client, admin_headers, suf, "otro")
    rut_id, dieta_id = _de_la_cuenta(suf, org_otro, u2)

    assert client.get(f"/api/routines/{rut_id}/edit", headers=h_mio).status_code == 403
    assert client.get(f"/api/diets/{dieta_id}/edit", headers=h_mio).status_code == 403


def test_LO_DE_UN_COACH_SIN_ORGANIZACION_NO_ES_CATALOGO(client, seed, admin_headers):
    """Un coach sin organización crea con `organization_id` a NULL, igual que
    el catálogo. Dar eso por catálogo dejaría su biblioteca a la vista de
    cualquier otro coach."""
    suf = uuid.uuid4().hex[:8]
    uid_suyo, _d, _h = _crear_coach(client, admin_headers, f"coach.solo2.{suf}@nutrientrena-qa.com")
    _u2, _d2, h_otro, _o = _coach_con_org(client, admin_headers, suf, "curioso")
    db = SessionLocal()
    try:
        rut = Routine(name=f"Privada suya {suf}", organization_id=None, user_id=uid_suyo)
        dieta = Diet(title=f"Privada suya {suf}", organization_id=None, user_id=uid_suyo)
        db.add(rut); db.add(dieta); db.commit()
        rut_id, dieta_id = rut.id, dieta.id
    finally:
        db.close()

    assert client.get(f"/api/routines/{rut_id}/edit", headers=h_otro).status_code == 403
    assert client.get(f"/api/diets/{dieta_id}/edit", headers=h_otro).status_code == 403


def test_NI_LA_DIETA_DEL_CLIENTE_DE_OTRO(client, seed, admin_headers):
    """Una dieta asignada se queda con `organization_id` a NULL: si el catálogo
    se reconociera solo por eso, cualquier coach vería a los clientes de todos.
    """
    suf = uuid.uuid4().hex[:8]
    _u1, det_coach, h_dueno, _o = _coach_con_org(client, admin_headers, suf, "dueno")
    _u2, _d2, h_curioso, _o2 = _coach_con_org(client, admin_headers, suf, "curioso")
    uid_cli, det_cli, _h = _crear_usuario(
        client, admin_headers, f"cli.vc.{suf}@nutrientrena-qa.com", role_id=6)
    db = SessionLocal()
    try:
        db.add(UserParent(user_detail_id=det_cli, parent_user_detail_id=det_coach))
        dieta = Diet(title=f"Del cliente {suf}", organization_id=None, user_id=uid_cli)
        rut = Routine(name=f"Del cliente {suf}", organization_id=None, user_id=uid_cli)
        db.add(dieta); db.add(rut); db.commit()
        dieta_id, rut_id = dieta.id, rut.id
    finally:
        db.close()

    assert client.get(f"/api/diets/{dieta_id}/edit", headers=h_curioso).status_code == 403
    assert client.get(f"/api/routines/{rut_id}/edit", headers=h_curioso).status_code == 403
    # Y su coach sí.
    assert client.get(f"/api/diets/{dieta_id}/edit", headers=h_dueno).status_code == 200
    assert client.get(f"/api/routines/{rut_id}/edit", headers=h_dueno).status_code == 200


def test_EL_PDF_DEL_CLIENTE_DE_OTRO_TAMPOCO(client, seed, admin_headers):
    """El PDF no comprobaba nada: con acertar el id se descargaba."""
    suf = uuid.uuid4().hex[:8]
    _u1, det_coach, h_dueno, _o = _coach_con_org(client, admin_headers, suf, "d2")
    _u2, _d2, h_curioso, _o2 = _coach_con_org(client, admin_headers, suf, "c2")
    uid_cli, det_cli, _h = _crear_usuario(
        client, admin_headers, f"cli.vc2.{suf}@nutrientrena-qa.com", role_id=6)
    db = SessionLocal()
    try:
        db.add(UserParent(user_detail_id=det_cli, parent_user_detail_id=det_coach))
        dieta = Diet(title=f"Del cliente {suf}", organization_id=None, user_id=uid_cli)
        db.add(dieta); db.commit()
        dieta_id = dieta.id
    finally:
        db.close()

    assert client.get(f"/api/diets/{dieta_id}/pdf", headers=h_curioso).status_code == 403
    assert client.get(f"/api/diets/{dieta_id}/pdf", headers=h_dueno).status_code == 200


def test_mirando_solo_el_catalogo_no_se_abre_lo_de_las_cuentas(client, seed, admin_headers):
    """Por "Contenido global" se mantiene el catálogo común, y lo privado de
    cada cuenta ni se lista ni se abre."""
    suf = uuid.uuid4().hex[:8]
    u2, _d2, _h2, org = _coach_con_org(client, admin_headers, suf, "priv")
    rut_id, dieta_id = _de_la_cuenta(suf, org, u2)

    h = dict(admin_headers)
    h.update(PLATAFORMA)
    assert client.get(f"/api/routines/{rut_id}/edit", headers=h).status_code == 403
    assert client.get(f"/api/diets/{dieta_id}/edit", headers=h).status_code == 403
