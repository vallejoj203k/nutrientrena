"""CORS: que el navegador pueda hablar de verdad con la API.

Esto se escribe después de un fallo real en producción. La Librería abierta
desde el panel de plataforma manda `X-Organization-Id` en todas las llamadas;
una cabecera propia obliga al navegador a pedir permiso antes (preflight), y
esa cabecera no estaba en la lista permitida. Resultado: TODAS las peticiones
de esa pantalla se caían con «NetworkError when attempting to fetch resource»,
un mensaje que no dice de qué va y que parece un problema de red.

Los tests de API no lo veían porque el cliente de pruebas no hace preflight: no
es un navegador. Por eso se comprueba aquí a mano, pidiendo el OPTIONS que
haría el navegador.
"""
from urllib.parse import urlsplit

from app.config import Settings


ORIGEN = "https://alzum.io"


def _preflight(client, cabecera, metodo="GET"):
    return client.options(
        "/api/routines/findAll",
        headers={
            "Origin": ORIGEN,
            "Access-Control-Request-Method": metodo,
            "Access-Control-Request-Headers": cabecera,
        },
    )


def test_el_navegador_puede_mandar_el_contexto_de_organizacion(client):
    """La cabecera del "segundo sombrero". Sin esto no funciona ni entrar en una
    cuenta desde el panel ni abrir la Librería como plataforma."""
    r = _preflight(client, "authorization,x-organization-id")
    assert r.status_code < 400, r.text
    permitidas = r.headers.get("access-control-allow-headers", "").lower()
    assert "x-organization-id" in permitidas, permitidas


def test_y_las_de_siempre_siguen_permitidas(client):
    r = _preflight(client, "authorization,content-type")
    assert r.status_code < 400, r.text
    permitidas = r.headers.get("access-control-allow-headers", "").lower()
    assert "authorization" in permitidas and "content-type" in permitidas


def test_una_cabecera_que_nadie_usa_no_se_permite(client):
    """Que la lista siga siendo una lista: si todo valiera, el test de arriba
    pasaría sin que la cabecera estuviera realmente contemplada."""
    r = _preflight(client, "x-inventada")
    permitidas = r.headers.get("access-control-allow-headers", "").lower()
    assert "x-inventada" not in permitidas, permitidas


# ── El origen es esquema + dominio, sin carpetas ───────────────────────────

def test_el_origen_no_lleva_la_carpeta_de_la_app():
    """FRONTEND_URL suele apuntar a la carpeta de la app (".../app"). Un origen
    con ruta no casa nunca con el que manda el navegador."""
    s = Settings(FRONTEND_URL="https://alzum.io/app", ALLOWED_ORIGINS=None)
    assert s.cors_origins == ["https://alzum.io"]


def test_da_igual_con_barra_final_o_sin_ella():
    for url in ("https://alzum.io/app/", "https://alzum.io/", "https://alzum.io"):
        s = Settings(FRONTEND_URL=url, ALLOWED_ORIGINS=None)
        assert s.cors_origins == ["https://alzum.io"], url


def test_se_respeta_el_puerto():
    s = Settings(FRONTEND_URL="https://mi-panel.es:8443/app", ALLOWED_ORIGINS=None)
    assert s.cors_origins == ["https://mi-panel.es:8443"]


def test_la_lista_explicita_tambien_se_normaliza():
    s = Settings(ALLOWED_ORIGINS="https://alzum.io/app, https://otra.com/")
    assert s.cors_origins == ["https://alzum.io", "https://otra.com"]


def test_en_local_sigue_valiendo_el_comodin():
    s = Settings(FRONTEND_URL="http://localhost:3000", ALLOWED_ORIGINS=None)
    assert s.cors_origins == ["*"]


def test_ningun_origen_declarado_lleva_ruta():
    """Vale para la configuración que esté puesta ahora mismo, sea la que sea."""
    from app.config import settings
    for o in settings.cors_origins:
        if o == "*":
            continue
        assert urlsplit(o).path == "", o
