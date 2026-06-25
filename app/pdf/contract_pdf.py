"""
Generador de PDF para contratos usando ReportLab.
"""
import io
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
            spaceAfter=2,
        ),
        "doc_type": ParagraphStyle(
            "DocType",
            fontName="Helvetica",
            fontSize=10,
            textColor=GRAY_TEXT,
            alignment=TA_CENTER,
            spaceAfter=4,
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
    story.append(Paragraph(contract.title, styles["title"]))

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
    for line in (contract.content or "").splitlines():
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
