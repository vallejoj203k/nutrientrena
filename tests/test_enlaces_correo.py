"""Los enlaces que van dentro de los correos tienen que llevar a algún sitio.

Bug real: el correo de "restablecer contraseña" llegaba bien, pero el botón
llevaba a una página que no existía.

Causa: había DOS convenciones para la misma variable de entorno.

    forms.py:  f"{FRONTEND_URL}/app/public/form.html"   → esperaba la raíz
    email.py:  f"{FRONTEND_URL}/reset-password.html"    → esperaba .../app

Se pusiera como se pusiese FRONTEND_URL, una de las dos salía mal. Con la
variable apuntando a la raíz —que es lo que asumen los formularios y el cálculo
de CORS— el enlace de contraseña salía a /reset-password.html, y el frontend se
sirve bajo /app.

Estas pruebas fijan que el enlace sale bien en las tres formas en que la
variable puede estar puesta, y que apunta a un fichero que existe de verdad.
"""
import os
import pathlib

import pytest

from app.core.email import frontend_url

RAIZ = pathlib.Path(__file__).resolve().parent.parent


@pytest.fixture
def sin_variable(monkeypatch):
    monkeypatch.delenv("FRONTEND_URL", raising=False)


def _pagina(url: str) -> str:
    """El fichero al que apunta el enlace, sin dominio ni parámetros."""
    return url.split("?")[0].split("/app/")[-1].split("://")[-1].split("/", 1)[-1]


# ── Las tres formas de tener puesta la variable ─────────────────────────────

def test_con_la_raiz_del_dominio(monkeypatch):
    """El caso que estaba roto: es como la configura CORS y los formularios."""
    monkeypatch.setenv("FRONTEND_URL", "https://alzum.io")
    assert frontend_url("reset-password.html?token=abc") == \
        "https://alzum.io/app/reset-password.html?token=abc"


def test_con_app_ya_incluido(monkeypatch):
    """No se duplica: sin esto saldría /app/app/reset-password.html."""
    monkeypatch.setenv("FRONTEND_URL", "https://alzum.io/app")
    assert frontend_url("reset-password.html") == "https://alzum.io/app/reset-password.html"


def test_con_barra_final(monkeypatch):
    monkeypatch.setenv("FRONTEND_URL", "https://alzum.io/")
    assert frontend_url("reset-password.html") == "https://alzum.io/app/reset-password.html"


def test_sin_variable_definida(sin_variable):
    """Se cae a la URL de producción, que es donde vive hoy."""
    url = frontend_url("reset-password.html")
    assert url.endswith("/app/reset-password.html"), url
    assert url.startswith("https://"), url


def test_en_desarrollo_no_se_mete_app(monkeypatch):
    """En local el frontend lo sirve otro proceso y sus páginas cuelgan de la
    raíz; añadirle /app rompería el enlace al revés."""
    monkeypatch.setenv("FRONTEND_URL", "http://localhost:8011")
    assert frontend_url("reset-password.html") == "http://localhost:8011/reset-password.html"
    monkeypatch.setenv("FRONTEND_URL", "http://127.0.0.1:3000")
    assert frontend_url("x.html") == "http://127.0.0.1:3000/x.html"


# ── Que la página exista de verdad ──────────────────────────────────────────

@pytest.mark.parametrize("pagina", ["reset-password.html", "public/form.html"])
def test_las_paginas_enlazadas_existen(pagina, monkeypatch):
    """Lo que falló en producción no fue el correo, fue el destino. Si alguien
    renombra o mueve una de estas páginas, esto salta antes de que un usuario
    se coma el 404."""
    monkeypatch.setenv("FRONTEND_URL", "https://alzum.io")
    url = frontend_url(pagina)
    assert f"/app/{pagina}" in url, url
    assert (RAIZ / "frontend" / pagina).is_file(), f"No existe frontend/{pagina}"


def test_el_correo_de_contrasena_lleva_el_enlace_bueno(monkeypatch):
    """Se comprueba sobre el HTML que se envía, no sobre el ayudante: entre uno
    y otro hay una plantilla donde también se puede meter la pata."""
    enviados = {}
    import app.core.email as correo

    monkeypatch.setenv("FRONTEND_URL", "https://alzum.io")
    monkeypatch.setattr(correo, "_send", lambda to, asunto, html: enviados.update(
        {"to": to, "html": html}) or (True, "ok"))

    assert correo.send_recover_password_email(to="a@b.com", name="Ana", token="TOK") is True
    assert 'href="https://alzum.io/app/reset-password.html?token=TOK"' in enviados["html"], \
        enviados["html"][:400]


def test_el_correo_del_formulario_tambien(monkeypatch):
    """Era la otra mitad del problema: con la variable puesta con /app, este
    salía a /app/app/public/form.html."""
    monkeypatch.setenv("FRONTEND_URL", "https://alzum.io/app")
    assert frontend_url("public/form.html?id=7") == "https://alzum.io/app/public/form.html?id=7"


def test_la_pagina_de_reset_lee_el_token_de_la_url():
    """Contrato entre el correo y la página: si una cambia el nombre del
    parámetro, el enlace deja de funcionar sin que nada más se entere."""
    html = (RAIZ / "frontend" / "reset-password.html").read_text()
    assert "URLSearchParams(location.search).get('token')" in html
    assert "/auth/reset-password" in html
