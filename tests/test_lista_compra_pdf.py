"""La lista de la compra en PDF.

El endpoint DIBUJA, no calcula: las cuentas están en el módulo del navegador y
llegan hechas. Eso es a propósito — rehacerlas aquí daría dos versiones de la
misma suma, y tarde o temprano el papel diría una cosa y la pantalla otra.

Lo que hay que comprobar, entonces, no son las cantidades sino que el fichero
salga: que sea un PDF de verdad, que no lo pueda pedir cualquiera, y que un
nombre raro no lo tumbe. Un PDF que se descarga y no abre es peor que un botón
que no existe.
"""
import base64
import re
import zlib

from app.pdf.shopping_list_pdf import MAX_ITEMS, generar_lista_compra_pdf

from tests.test_org_scope import _crear_usuario


def _texto(pdf):
    """El texto que hay DENTRO del PDF.

    Sin esto, las pruebas solo pueden decir "empieza por %PDF", que es
    compatible con una página en blanco. ReportLab comprime los flujos con
    ASCII85 sobre zlib; los dos vienen en la biblioteca estándar, así que
    leerlos no obliga a instalar nada ni en local ni en CI.
    """
    partes = []
    for m in re.finditer(rb"stream\r?\n(.*?)endstream", pdf, re.S):
        d = m.group(1).strip()
        try:
            d = base64.a85decode(d, adobe=True, ignorechars=b" \t\r\n")
        except Exception:
            pass
        try:
            partes.append(zlib.decompress(d))
        except Exception:
            partes.append(d)
    return b"".join(partes)

GRUPOS = [
    {"categoria": "Aves", "items": [{"nombre": "Pechuga de pollo", "cantidad": "1,4 kg"}]},
    {"categoria": "Frutas", "items": [{"nombre": "Manzana", "cantidad": "7 ud"}]},
]


def _pedir(client, headers, cuerpo=None):
    return client.post("/api/client/shopping-list/pdf", headers=headers,
                       json=cuerpo if cuerpo is not None else {
                           "titulo": "Lista de la compra",
                           "subtitulo": "Semana completa",
                           "grupos": GRUPOS})


# ── Que salga un PDF, no un fichero cualquiera ─────────────────────────────

def test_SALE_UN_PDF_DE_VERDAD(client, seed, admin_headers):
    """Los cuatro primeros bytes de todo PDF son %PDF. Comprobar solo que la
    respuesta es 200 dejaría pasar un fichero vacío o un JSON de error."""
    suf = "pdf1"
    _uid, _det, h_cli = _crear_usuario(
        client, admin_headers, f"cli.{suf}@nutrientrena-qa.com", role_id=6)

    r = _pedir(client, h_cli)
    assert r.status_code == 200, r.text
    assert r.content[:4] == b"%PDF", r.content[:40]
    assert r.headers["content-type"].startswith("application/pdf")
    assert "lista-compra.pdf" in r.headers.get("content-disposition", "")
    # Un PDF con dos alimentos no pesa 200 bytes: eso sería una página en blanco.
    assert len(r.content) > 1500, len(r.content)


def test_una_lista_vacia_no_revienta(client, seed, admin_headers):
    """Se puede pulsar con el plan sin asignar. Mejor un PDF que lo diga que un
    error."""
    pdf = generar_lista_compra_pdf("Lista", "Lunes", [])
    assert pdf[:4] == b"%PDF"


def test_UN_NOMBRE_CON_SIGNOS_NO_PIERDE_LETRAS(client, seed, admin_headers):
    """ReportLab lee un subconjunto de HTML dentro de los párrafos, y lo que no
    reconoce se lo TRAGA sin decir nada: "Pan <integral>" salía como "Pan " a
    secas. No revienta, que sería mejor — sale un PDF perfecto al que le falta
    media palabra, y eso no se nota hasta estar en el supermercado.

    "Aceite d'oliva" y "Café & leche" están en el catálogo de verdad.
    """
    pdf = generar_lista_compra_pdf("Lista", "Lunes", [
        {"categoria": "Panadería & más", "items": [
            {"nombre": "Pan <integral>", "cantidad": "200 g"},
            {"nombre": "Aceite d'oliva \"virgen\"", "cantidad": "1 ud"},
            {"nombre": "Café & leche", "cantidad": "250 ml"},
        ]}])
    assert pdf[:4] == b"%PDF"
    t = _texto(pdf)
    assert b"integral" in t, "se ha comido la palabra que iba entre < >"
    assert b"oliva" in t and b"virgen" in t, t[:400]
    assert b"leche" in t, "el & se ha llevado por delante lo que venía detrás"


def test_UNA_LISTA_LARGUISIMA_SE_CORTA_EN_EL_TOPE(client, seed, admin_headers):
    """Sin tope, una petición cualquiera puede pedir cien mil renglones y dejar
    al servidor dibujando un rato."""
    def hacer(n):
        return generar_lista_compra_pdf("Lista", "Semana", [{"categoria": "Otros", "items": [
            {"nombre": f"Alimento {i}", "cantidad": "100 g"} for i in range(n)]}])

    pasado = hacer(MAX_ITEMS * 3)
    justo = hacer(MAX_ITEMS)
    assert pasado[:4] == b"%PDF"
    # Pedir el triple tiene que dar exactamente lo mismo que pedir el tope: si
    # el tope no se aplicara, el de tres veces sería mucho más gordo.
    assert len(pasado) == len(justo), (len(pasado), len(justo))
    # Y el tope tiene que ser el tope, no un número menor por accidente.
    assert b"Alimento " + str(MAX_ITEMS - 1).encode() in _texto(justo)
    assert b"Alimento " + str(MAX_ITEMS).encode() not in _texto(pasado)


def test_LO_QUE_SE_PIDE_ESTA_ESCRITO_EN_EL_PAPEL(client, seed, admin_headers):
    """Que el fichero sea un PDF no dice que ponga nada: una página en blanco
    también empieza por %PDF. Aquí se lee lo que hay dentro."""
    pdf = generar_lista_compra_pdf("Lista de la compra", "Miércoles", [
        {"categoria": "Lácteos", "items": [
            {"nombre": "Plátano", "cantidad": "1 ud"},
            {"nombre": "Yogur griego", "cantidad": "1,1 kg"}]}])
    t = _texto(pdf)
    assert b"Yogur griego" in t, t[:400]
    assert b"1,1 kg" in t, "falta la cantidad, que es la mitad de una lista de la compra"
    # La categoría va en mayúsculas y con su acento: dentro del flujo la Á
    # se escribe escapada en octal (L\\301CTEOS), no se pierde.
    assert b"CTEOS" in t, t[:400]
    # Los acentos van escapados en octal dentro del flujo, no se pierden.
    assert b"Pl" in t and b"tano" in t, "el acento se ha comido el nombre"


def test_LA_CASILLA_ES_UN_CUADRO_DIBUJADO_NO_UNA_LETRA(client, seed, admin_headers):
    """El carácter ☐ no existe en Helvetica y ReportLab lo sustituye por otro
    SIN AVISAR: en el papel salía una "n" delante de cada alimento. El PDF se
    generaba perfecto, pesaba lo suyo y empezaba por %PDF — solo estaba mal
    para quien lo mirase.
    """
    pdf = generar_lista_compra_pdf("Lista", "Semana", [
        {"categoria": "Aves", "items": [{"nombre": "Pechuga de pollo", "cantidad": "1,4 kg"}]}])
    t = _texto(pdf).decode("latin-1")
    escritos = re.findall(r"\((.*?)\) Tj", t)
    # Nada suelto de una sola letra: la casilla no es texto.
    assert not [x for x in escritos if len(x) == 1], escritos
    assert "Pechuga de pollo" in escritos, escritos
    # Y el cuadro está dibujado de verdad (operador `re` de rectángulo).
    assert re.search(r"\bre\b", t), "no se ha dibujado ninguna casilla"


# ── Y que no lo pida cualquiera ────────────────────────────────────────────

def test_SIN_ENTRAR_NO_SE_PIDE_UN_PDF(client, seed):
    """El endpoint dibuja lo que le manden: sin autenticar sería un generador
    de PDF abierto a quien pase por ahí."""
    r = client.post("/api/client/shopping-list/pdf", json={
        "titulo": "x", "subtitulo": "", "grupos": GRUPOS})
    assert r.status_code in (401, 403), r.status_code


def test_un_texto_desmedido_se_rechaza(client, seed, admin_headers):
    """Los campos tienen tope. Sin él, un nombre de un megabyte entra tal cual
    en el dibujo."""
    _uid, _det, h_cli = _crear_usuario(
        client, admin_headers, "cli.pdf2@nutrientrena-qa.com", role_id=6)
    r = _pedir(client, h_cli, {"titulo": "x" * 5000, "subtitulo": "", "grupos": []})
    assert r.status_code == 422, r.status_code
