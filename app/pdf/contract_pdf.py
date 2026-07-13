"""
Generador de PDF para contratos usando ReportLab.
"""
import io
import re
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib.colors import HexColor, white
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, HRFlowable,
)
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY

INDIGO      = HexColor("#4F46E5")
INDIGO_PALE = HexColor("#EEF2FF")
GRAY_TEXT   = HexColor("#6B7280")
TEXT_DARK   = HexColor("#111827")
TEXT_MID    = HexColor("#374151")
GRAY_BORDER = HexColor("#E5E7EB")
WHITE       = white

TYPE_LABELS = {
    "servicio": "Contrato de Servicios",
    "consentimiento": "Consentimiento Informado",
    "acuerdo": "Acuerdo de Confidencialidad",
    "otro": "Documento Legal",
}


_BLANK = "__________"


def _contract_values(contract) -> dict:
    """Valores reales con los que se sustituyen las variables {{...}} del contrato."""
    client = getattr(contract, "client", None)
    client_name = ""
    if client:
        client_name = f"{client.name or ''} {client.last_name or ''}".strip()
    coach_name = ""
    try:
        coach_name = (contract.coach.name or "").strip() if getattr(contract, "coach", None) else ""
    except Exception:
        coach_name = ""
    fecha = (contract.created_at or datetime.utcnow()).strftime("%d/%m/%Y")
    precio = ""
    if client and getattr(client, "precio", None) is not None:
        precio = f"{client.precio:.0f} € / mes"
    telefono = client.phone if client and getattr(client, "phone", None) else ""
    servicio = TYPE_LABELS.get(getattr(contract, "type", None), "Servicios")
    return {
        "nombre_cliente": client_name or _BLANK,
        "coach_nombre": coach_name or _BLANK,
        "fecha": fecha,
        "servicio": servicio,
        "precio": precio or _BLANK,
        "duracion": _BLANK,
        "contacto_emergencia": _BLANK,
        "telefono_emergencia": telefono or _BLANK,
    }


def _substitute(text, contract) -> str:
    """Reemplaza las variables {{clave}} por sus valores; cualquier variable
    desconocida se convierte en un espacio en blanco rellenable."""
    text = text or ""
    for key, val in _contract_values(contract).items():
        text = text.replace("{{" + key + "}}", val)
    text = re.sub(r"\{\{\s*\w+\s*\}\}", _BLANK, text)
    return text


def generate_contract_pdf(contract) -> bytes:
    """Recibe un objeto Contract (con relaciones cargadas) y devuelve bytes PDF."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=2.5 * cm,
        rightMargin=2.5 * cm,
        topMargin=2.0 * cm,
        bottomMargin=2.5 * cm,
    )

    styles = {
        "brand": ParagraphStyle(
            "Brand",
            fontName="Helvetica-Bold",
            fontSize=22,
            textColor=INDIGO,
            alignment=TA_CENTER,
            leading=26,
            spaceAfter=8,
        ),
        "doc_type": ParagraphStyle(
            "DocType",
            fontName="Helvetica",
            fontSize=10,
            textColor=GRAY_TEXT,
            alignment=TA_CENTER,
            leading=14,
            spaceBefore=2,
            spaceAfter=10,
        ),
        "title": ParagraphStyle(
            "Title",
            fontName="Helvetica-Bold",
            fontSize=14,
            textColor=TEXT_DARK,
            alignment=TA_CENTER,
            spaceBefore=16,
            spaceAfter=4,
        ),
        "meta": ParagraphStyle(
            "Meta",
            fontName="Helvetica",
            fontSize=9,
            textColor=GRAY_TEXT,
            alignment=TA_CENTER,
            spaceAfter=20,
        ),
        "body": ParagraphStyle(
            "Body",
            fontName="Helvetica",
            fontSize=10,
            textColor=TEXT_MID,
            leading=16,
            alignment=TA_JUSTIFY,
            spaceAfter=8,
        ),
        "footer": ParagraphStyle(
            "Footer",
            fontName="Helvetica",
            fontSize=8,
            textColor=GRAY_TEXT,
            alignment=TA_CENTER,
        ),
    }

    story = []

    # ── Header ───────────────────────────────────────────────────────────────
    story.append(Paragraph(
        "<b>Alzum</b><font color='#818CF8'>.io</font>",
        styles["brand"],
    ))
    story.append(Paragraph(
        TYPE_LABELS.get(contract.type, "Documento Legal"),
        styles["doc_type"],
    ))
    story.append(HRFlowable(width="100%", thickness=1, color=INDIGO))
    story.append(Spacer(1, 0.4 * cm))

    # ── Title & meta ──────────────────────────────────────────────────────────
    story.append(Paragraph(_substitute(contract.title, contract), styles["title"]))

    client_name = ""
    if contract.client:
        client_name = f"{contract.client.name or ''} {contract.client.last_name or ''}".strip()
    meta_parts = []
    if client_name:
        meta_parts.append(f"Cliente: {client_name}")
    if contract.created_at:
        meta_parts.append(f"Fecha: {contract.created_at.strftime('%d/%m/%Y')}")
    if meta_parts:
        story.append(Paragraph("  ·  ".join(meta_parts), styles["meta"]))

    story.append(HRFlowable(width="100%", thickness=0.5, color=GRAY_BORDER))
    story.append(Spacer(1, 0.5 * cm))

    # ── Content ───────────────────────────────────────────────────────────────
    for line in _substitute(contract.content, contract).splitlines():
        stripped = line.strip()
        if not stripped:
            story.append(Spacer(1, 0.2 * cm))
            continue
        # Section headings: lines in ALL CAPS or starting with a digit+dot
        if stripped.isupper() or (len(stripped) > 2 and stripped[0].isdigit() and stripped[1] == "."):
            s = ParagraphStyle(
                "Heading",
                fontName="Helvetica-Bold",
                fontSize=10,
                textColor=INDIGO,
                spaceBefore=10,
                spaceAfter=4,
            )
            story.append(Paragraph(stripped, s))
        else:
            story.append(Paragraph(stripped, styles["body"]))

    # ── Footer ────────────────────────────────────────────────────────────────
    story.append(Spacer(1, 0.6 * cm))
    story.append(HRFlowable(width="100%", thickness=0.5, color=GRAY_BORDER))
    story.append(Spacer(1, 0.2 * cm))
    story.append(Paragraph("Generado por Alzum.io", styles["footer"]))

    doc.build(story)
    return buffer.getvalue()
