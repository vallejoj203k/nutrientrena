"""Sección "Configuración": ajustes que afectan a toda la plataforma.

La regla que se ha seguido: un ajuste que no gobierna nada no se pone. Por eso
las pruebas no comprueban que el valor se guarde —eso es lo fácil— sino que
HACE algo:

- el modo mantenimiento bloquea de verdad las escrituras de los coaches;
- el correo de soporte y el nombre le llegan al coach a su panel;
- los días de prueba se convierten en la fecha de fin de una cuenta.

El único que hoy no gobierna nada es "registro abierto", porque no existe la
página pública de alta. La API lo dice explícitamente para que la pantalla
pueda advertirlo en vez de fingir.
"""
from app.core.dependencies import EDITOR_CONTENIDO_GLOBAL, SOPORTE
from app.database import SessionLocal
from app.models.platform_setting import PlatformSetting

from tests.test_admin_panel import _con_rol, _crear_cuenta
from tests.test_org_scope import _crear_organizacion, _crear_usuario


def _ajustes(client, headers):
    r = client.get("/api/admin/settings", headers=headers)
    assert r.status_code == 200, r.text
    return r.json()["data"]


def _guardar(client, headers, **campos):
    return client.put("/api/admin/settings", headers=headers, json=campos)


def _apagar_mantenimiento():
    """Deja la plataforma como estaba, pase lo que pase en el test.

    Sin esto, un fallo a mitad de una prueba dejaría el modo mantenimiento
    puesto y TODAS las demás pruebas de la suite empezarían a recibir 503.
    """
    from app.routers.platform_settings import _invalidar_cache
    db = SessionLocal()
    try:
        s = db.query(PlatformSetting).filter(PlatformSetting.id == 1).first()
        if s:
            s.maintenance_mode = False
            db.commit()
    finally:
        db.close()
    _invalidar_cache()


# ── Quién entra ─────────────────────────────────────────────────────────────

def test_solo_el_superadmin_toca_la_configuracion(client, seed, admin_headers):
    assert client.get("/api/admin/settings", headers=admin_headers).status_code == 200

    for email, rol in [("soporte.cfg@nutrientrena-qa.com", SOPORTE),
                       ("editor.cfg@nutrientrena-qa.com", EDITOR_CONTENIDO_GLOBAL)]:
        _uid, _det, h = _con_rol(client, admin_headers, email, rol)
        assert client.get("/api/admin/settings", headers=h).status_code == 403
        assert _guardar(client, h, platform_name="Mío").status_code == 403

    _uid, _det, hc = _crear_usuario(client, admin_headers, "coach.cfg@nutrientrena-qa.com", role_id=5)
    assert client.get("/api/admin/settings", headers=hc).status_code == 403


def test_hay_valores_por_defecto_desde_el_primer_dia(client, seed, admin_headers):
    """La fila se crea sola. Si no, la primera visita a la sección reventaría
    contra una tabla vacía."""
    d = _ajustes(client, admin_headers)
    assert d["platform_name"]
    assert d["default_currency"] in d["monedas"]
    assert isinstance(d["trial_days"], int)
    assert d["maintenance_mode"] is False


# ── Validaciones ────────────────────────────────────────────────────────────

def test_no_se_deja_la_plataforma_sin_nombre(client, seed, admin_headers):
    assert _guardar(client, admin_headers, platform_name="   ").status_code == 400


def test_un_correo_de_soporte_torcido_se_rechaza(client, seed, admin_headers):
    """Si esto está mal, el coach escribe a un buzón que no existe y nadie se
    entera."""
    assert _guardar(client, admin_headers, support_email="soporte-arroba-alzum").status_code == 400
    assert _guardar(client, admin_headers, support_email="soporte@alzum").status_code == 400
    assert _guardar(client, admin_headers, support_email="soporte@alzum.io").status_code == 200
    # Vaciarlo sí vale: es opcional
    assert _guardar(client, admin_headers, support_email="").status_code == 200
    assert _ajustes(client, admin_headers)["support_email"] is None


def test_la_moneda_tiene_que_ser_de_la_lista(client, seed, admin_headers):
    assert _guardar(client, admin_headers, default_currency="BTC").status_code == 400
    assert _guardar(client, admin_headers, default_currency="usd").status_code == 200
    assert _ajustes(client, admin_headers)["default_currency"] == "USD"
    _guardar(client, admin_headers, default_currency="EUR")


def test_los_dias_de_prueba_tienen_limites(client, seed, admin_headers):
    assert _guardar(client, admin_headers, trial_days=-1).status_code == 400
    assert _guardar(client, admin_headers, trial_days=400).status_code == 400
    assert _guardar(client, admin_headers, trial_days=0).status_code == 200


# ── Que los ajustes HAGAN algo ──────────────────────────────────────────────

def test_los_dias_de_prueba_se_convierten_en_una_fecha_de_fin(client, seed, admin_headers):
    """Sin esto, "días de prueba gratuita" sería un número guardado que no le
    pasa a nadie."""
    from datetime import datetime

    assert _guardar(client, admin_headers, trial_days=14).status_code == 200
    d = _crear_cuenta(client, admin_headers, name="Centro en prueba",
                      owner_name="Prueba Dueño", owner_email="prueba.dueno@nutrientrena-qa.com",
                      owner_password="Centro123!", state="prueba").json()["data"]

    assert d["trial_ends_at"] is not None, d
    faltan = (datetime.fromisoformat(d["trial_ends_at"]) - datetime.utcnow()).days
    assert 12 <= faltan <= 14, faltan

    # Una cuenta activa no tiene fin de prueba: no está de prueba
    d2 = _crear_cuenta(client, admin_headers, name="Centro activo sin prueba",
                       owner_name="Activo Dueño", owner_email="activo.dueno@nutrientrena-qa.com",
                       owner_password="Centro123!", state="activa").json()["data"]
    assert d2["trial_ends_at"] is None, d2


def test_el_coach_recibe_el_nombre_y_el_correo_de_soporte(client, seed, admin_headers):
    """Un ajuste que solo se ve en la pantalla donde se escribe no le sirve a
    nadie."""
    _guardar(client, admin_headers, platform_name="Alzum.io", support_email="ayuda@alzum.io")

    _uid, _det, h = _crear_usuario(client, admin_headers, "coach.ve.cfg@nutrientrena-qa.com", role_id=5)
    r = client.get("/api/platform/settings", headers=h)
    assert r.status_code == 200, r.text
    d = r.json()["data"]
    assert d["platform_name"] == "Alzum.io"
    assert d["support_email"] == "ayuda@alzum.io"
    # Y NO le llega lo que no es asunto suyo
    assert "open_registration" not in d and "trial_days" not in d


def test_sin_sesion_no_se_leen_ni_los_ajustes_publicos(client, seed):
    # 403 y no 401 porque sin cabecera el esquema Bearer ni llega a validar el
    # token. Lo que importa es que no se responda.
    assert client.get("/api/platform/settings").status_code in (401, 403)


def test_el_modo_mantenimiento_bloquea_de_verdad(client, seed, admin_headers):
    """El interruptor tiene que hacer algo. Se comprueba que un coach no puede
    guardar, que SÍ puede leer, y que el equipo de Alzum sigue trabajando."""
    _uid, det, h = _crear_usuario(client, admin_headers, "coach.mant@nutrientrena-qa.com", role_id=5)
    _crear_organizacion(det, "Centro en mantenimiento")

    # Antes: puede crear
    assert client.post("/api/trainings", headers=h, json={"name": "Antes del mantenimiento"}).status_code == 200

    try:
        assert _guardar(client, admin_headers, maintenance_mode=True).status_code == 200

        r = client.post("/api/trainings", headers=h, json={"name": "Durante el mantenimiento"})
        assert r.status_code == 503, r.text
        assert "mantenimiento" in r.json()["message"].lower()

        # Leer sigue funcionando: un coach que entra ve sus datos y el aviso,
        # en vez de una aplicación rota que no sabe interpretar.
        assert client.get("/api/trainings/findAll", headers=h).status_code == 200
        assert client.get("/api/platform/settings", headers=h).json()["data"]["maintenance_mode"] is True

        # El equipo de Alzum sigue pudiendo trabajar: si no, no podría ni
        # apagar el mantenimiento desde el panel.
        assert client.get("/api/admin/settings", headers=admin_headers).status_code == 200
        assert _guardar(client, admin_headers, platform_name="Alzum.io").status_code == 200
    finally:
        _apagar_mantenimiento()

    # Y al apagarlo, todo vuelve
    assert client.post("/api/trainings", headers=h, json={"name": "Después del mantenimiento"}).status_code == 200


def test_apagar_el_mantenimiento_tiene_efecto_inmediato(client, seed, admin_headers):
    """El valor se cachea unos segundos para no consultar la base en cada
    guardado. Si la caché no se invalidara al escribir, apagar el mantenimiento
    tardaría en notarse — y eso, en medio de una incidencia, es lo peor."""
    _uid, det, h = _crear_usuario(client, admin_headers, "coach.cache@nutrientrena-qa.com", role_id=5)
    _crear_organizacion(det, "Centro de la caché")
    try:
        _guardar(client, admin_headers, maintenance_mode=True)
        assert client.post("/api/trainings", headers=h, json={"name": "Bloqueado"}).status_code == 503
        _guardar(client, admin_headers, maintenance_mode=False)
        # Sin esperar nada: inmediatamente
        assert client.post("/api/trainings", headers=h, json={"name": "Desbloqueado"}).status_code == 200
    finally:
        _apagar_mantenimiento()


# ── Lo que todavía no gobierna nada ─────────────────────────────────────────

def test_el_registro_abierto_se_guarda_y_se_avisa_de_que_no_hay_pagina(client, seed, admin_headers):
    """No existe alta pública: los entrenadores se meten a mano. La API lo dice
    para que la pantalla lo advierta en vez de fingir que ya gobierna algo."""
    d = _ajustes(client, admin_headers)
    assert d["registro_publico_existe"] is False

    assert _guardar(client, admin_headers, open_registration=True).status_code == 200
    assert _ajustes(client, admin_headers)["open_registration"] is True
    _guardar(client, admin_headers, open_registration=False)


def test_guardar_solo_un_campo_no_borra_los_demas(client, seed, admin_headers):
    """Regresión: con exclude_unset mal puesto, guardar el nombre dejaría el
    correo de soporte en null sin que nadie lo pidiera."""
    _guardar(client, admin_headers, platform_name="Alzum.io",
             support_email="hola@alzum.io", trial_days=21)

    assert _guardar(client, admin_headers, platform_name="Alzum").status_code == 200
    d = _ajustes(client, admin_headers)
    assert d["support_email"] == "hola@alzum.io"
    assert d["trial_days"] == 21
