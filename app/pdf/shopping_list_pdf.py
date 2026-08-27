"""PDF de la lista de la compra.

Dibuja, no calcula. Las cuentas —juntar el mismo alimento, sumar solo lo que
comparte unidad, pasar de gramos a kilos— viven en `frontend/js/lista-compra.js`
y llegan aquí ya hechas. Rehacerlas en Python daría dos implementaciones que
tienen que coincidir, y de esas dos una se queda atrás: el cliente vería una
cantidad en pantalla y otra distinta en el papel que se lleva al supermercado.
"""
import io

from reportlab.lib.colors import HexColor, white
from reportlab.lib.enums import TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.graphics.shapes import Drawing, Rect
from reportlab.platypus import (
    KeepTogether, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle,
)

INDIGO = HexColor("#4F46E5")
INDIGO_LIGHT = HexColor("#818CF8")
GRAY_BORDER = HexColor("#E5E7EB")
GRAY_TEXT = HexColor("#6B7280")
TEXT_DARK = HexColor("#111827")

# Un tope por si llega una barbaridad: nadie compra mil cosas en una semana, y
# sin límite una petición cualquiera puede tener al servidor dibujando un rato.
MAX_ITEMS = 400


def _txt(v):
    """Texto plano dentro de un Paragraph.

    ReportLab interpreta un subconjunto de HTML: un alimento que se llamara
    "Pan <integral>" rompería el párrafo entero.
    """
    return (str(v if v is not None else "")
            .replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def _cabecera(titulo, subtitulo, ancho):
    marca = Paragraph(
        "<b>Alzum</b><font color='#818CF8'>.io</font>",
        ParagraphStyle("Marca", fontName="Helvetica-Bold", fontSize=22, textColor=white))
    tit = Paragraph(_txt(titulo), ParagraphStyle(
        "Tit", fontName="Helvetica-Bold", fontSize=13, textColor=white, alignment=TA_RIGHT))
    sub = Paragraph(_txt(subtitulo), ParagraphStyle(
        "Sub", fontName="Helvetica", fontSize=10, textColor=HexColor("#C7D2FE"),
        alignment=TA_RIGHT))

    t = Table([[marca, tit], ["", sub]], colWidths=[ancho * 0.45, ancho * 0.55])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), INDIGO),
        ("TOPPADDING", (0, 0), (-1, -1), 16),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 16),
        ("LEFTPADDING", (0, 0), (-1, -1), 18),
        ("RIGHTPADDING", (0, 0), (-1, -1), 18),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("SPAN", (0, 0), (0, 1)),
    ]))
    return t


def _casilla():
    """La casilla que se marca A MANO: el papel se lleva al supermercado, y ahí
    no hay pantalla que tocar.

    Se DIBUJA, no se escribe. El carácter ☐ no existe en Helvetica y ReportLab
    lo sustituye por otro sin avisar: en el papel salía una "n" en cada
    renglón. Un rectángulo se ve igual en cualquier lector.
    """
    lado = 0.36 * cm
    d = Drawing(lado, lado)
    d.add(Rect(0, 0, lado, lado, rx=1, ry=1,
               strokeColor=HexColor("#9CA3AF"), strokeWidth=0.8, fillColor=None))
    return d


def _grupo(categoria, items, ancho):
    """Una categoría con sus alimentos, en una tabla que no se parte."""
    titulo = Table([[Paragraph(_txt(categoria).upper(), ParagraphStyle(
        "Cat", fontName="Helvetica-Bold", fontSize=9, textColor=GRAY_TEXT))]],
        colWidths=[ancho])
    titulo.setStyle(TableStyle([
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LINEBEFORE", (0, 0), (-1, -1), 3, INDIGO),
    ]))

    est_nombre = ParagraphStyle("N", fontName="Helvetica", fontSize=10.5, textColor=TEXT_DARK)
    est_cant = ParagraphStyle("C", fontName="Helvetica-Bold", fontSize=10.5,
                              textColor=GRAY_TEXT, alignment=TA_RIGHT)
    filas = []
    for it in items:
        filas.append([
            _casilla(),
            Paragraph(_txt(it.get("nombre")), est_nombre),
            Paragraph(_txt(it.get("cantidad")), est_cant),
        ])

    tabla = Table(filas, colWidths=[0.9 * cm, ancho - 4.4 * cm, 3.5 * cm])
    tabla.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("LINEBELOW", (0, 0), (-1, -2), 0.4, GRAY_BORDER),
    ]))
    return KeepTogether([titulo, Spacer(1, 0.15 * cm), tabla, Spacer(1, 0.45 * cm)])


def generar_lista_compra_pdf(titulo, subtitulo, grupos) -> bytes:
    """`grupos` es [{categoria, items:[{nombre, cantidad}]}], ya calculado."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, title=str(titulo or "Lista de la compra"),
                            leftMargin=1.8 * cm, rightMargin=1.8 * cm,
                            topMargin=1.8 * cm, bottomMargin=2 * cm)

    story = [_cabecera(titulo, subtitulo, doc.width), Spacer(1, 0.7 * cm)]

    restantes = MAX_ITEMS
    pintados = 0
    for g in (grupos or []):
        items = (g.get("items") or [])[:max(0, restantes)]
        if not items:
            continue
        restantes -= len(items)
        pintados += len(items)
        story.append(_grupo(g.get("categoria") or "Otros", items, doc.width))

    if not pintados:
        story.append(Paragraph("No hay alimentos en este plan.", ParagraphStyle(
            "Vacio", fontName="Helvetica", fontSize=11, textColor=GRAY_TEXT)))

    story.append(Spacer(1, 0.3 * cm))
    story.append(Paragraph(
        f"{pintados} alimento{'s' if pintados != 1 else ''} · Alzum.io",
        ParagraphStyle("Pie", fontName="Helvetica", fontSize=8.5,
                       textColor=INDIGO_LIGHT, alignment=TA_LEFT)))

    doc.build(story)
    return buffer.getvalue()
