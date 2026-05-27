"""
Generador de PDF para rutinas usando ReportLab.
"""
import io
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib.colors import HexColor, white
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, KeepTogether,
)
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_CENTER

# ── Brand colors ──────────────────────────────────────────────────────────────
PURPLE       = HexColor("#5B2D8E")
PURPLE_LIGHT = HexColor("#EDE7F6")
PURPLE_MID   = HexColor("#7E57C2")
PURPLE_DARK  = HexColor("#3A1060")
GRAY_BG      = HexColor("#F8F6FC")
GRAY_TEXT    = HexColor("#555555")
GRAY_BORDER  = HexColor("#DDDDDD")
GREEN        = HexColor("#43A047")


def _styles():
    return {
        "title": ParagraphStyle(
            "Title",
            fontName="Helvetica-Bold",
            fontSize=22,
            textColor=white,
            alignment=TA_CENTER,
            spaceAfter=4,
        ),
        "subtitle": ParagraphStyle(
            "Subtitle",
            fontName="Helvetica",
            fontSize=11,
            textColor=HexColor("#E0D0FF"),
            alignment=TA_CENTER,
        ),
        "section": ParagraphStyle(
            "Section",
            fontName="Helvetica-Bold",
            fontSize=13,
            textColor=PURPLE,
            spaceBefore=14,
            spaceAfter=6,
        ),
        "day_name": ParagraphStyle(
            "DayName",
            fontName="Helvetica-Bold",
            fontSize=11,
            textColor=white,
        ),
        "body": ParagraphStyle(
            "Body",
            fontName="Helvetica",
            fontSize=9,
            textColor=GRAY_TEXT,
            spaceAfter=2,
        ),
        "tag": ParagraphStyle(
            "Tag",
            fontName="Helvetica-Bold",
            fontSize=8,
            textColor=PURPLE,
        ),
        "footer": ParagraphStyle(
            "Footer",
            fontName="Helvetica",
            fontSize=8,
            textColor=HexColor("#AAAAAA"),
            alignment=TA_CENTER,
        ),
    }


def _info_table(routine, styles, doc_width):
    """Tarjeta con info general de la rutina."""
    rows = []
    if routine.training:
        rows.append(["Tipo de entrenamiento", routine.training])
    if routine.days:
        rows.append(["Días por semana", str(routine.days)])
    if routine.time:
        rows.append(["Duración por sesión", f"{routine.time} min"])
    if routine.training_level and routine.training_level.description:
        rows.append(["Nivel", routine.training_level.description])
    if routine.gender and routine.gender.description:
        rows.append(["Género", routine.gender.description])

    if not rows:
        return None

    tbl = Table(rows, colWidths=[5 * cm, doc_width - 5 * cm])
    tbl.setStyle(TableStyle([
        ("FONTNAME",     (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTNAME",     (1, 0), (1, -1), "Helvetica"),
        ("FONTSIZE",     (0, 0), (-1, -1), 9),
        ("TEXTCOLOR",    (0, 0), (0, -1), PURPLE),
        ("TEXTCOLOR",    (1, 0), (1, -1), GRAY_TEXT),
        ("BACKGROUND",   (0, 0), (-1, -1), GRAY_BG),
        ("TOPPADDING",   (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING",(0, 0), (-1, -1), 5),
        ("LEFTPADDING",  (0, 0), (-1, -1), 10),
        ("LINEBELOW",    (0, 0), (-1, -2), 0.3, GRAY_BORDER),
    ]))
    return tbl


def generate_routine_pdf(routine) -> bytes:
    """
    Recibe un objeto Routine (con relaciones cargadas) y devuelve bytes PDF.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=1.8 * cm,
        rightMargin=1.8 * cm,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
    )

    styles = _styles()
    story = []

    # ── Header banner ─────────────────────────────────────────────────────────
    header_data = [[
        Paragraph("NUTRIENTRENA", styles["title"]),
    ], [
        Paragraph(routine.name or "Plan de Entrenamiento", styles["subtitle"]),
    ]]
    header_tbl = Table(header_data, colWidths=[doc.width])
    header_tbl.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), PURPLE),
        ("TOPPADDING",    (0, 0), (-1, -1), 14),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 14),
        ("LEFTPADDING",   (0, 0), (-1, -1), 10),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 10),
    ]))
    story.append(header_tbl)
    story.append(Spacer(1, 0.5 * cm))

    # ── Info general ──────────────────────────────────────────────────────────
    info_tbl = _info_table(routine, styles, doc.width)
    if info_tbl:
        story.append(info_tbl)
        story.append(Spacer(1, 0.5 * cm))

    # ── Días ──────────────────────────────────────────────────────────────────
    story.append(Paragraph("Programa de entrenamiento", styles["section"]))

    col_w = [doc.width * 0.30, doc.width * 0.22, doc.width * 0.12,
             doc.width * 0.18, doc.width * 0.18]

    for day in (routine.days_list or []):
        # Encabezado del día
        day_header = Table(
            [[Paragraph(day.day_name or "Día", styles["day_name"])]],
            colWidths=[doc.width],
        )
        day_header.setStyle(TableStyle([
            ("BACKGROUND",    (0, 0), (-1, -1), PURPLE_MID),
            ("TOPPADDING",    (0, 0), (-1, -1), 7),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
            ("LEFTPADDING",   (0, 0), (-1, -1), 10),
        ]))

        rows = [[
            Paragraph("<b>Ejercicio</b>",       styles["body"]),
            Paragraph("<b>Músculo</b>",          styles["body"]),
            Paragraph("<b>Series</b>",           styles["body"]),
            Paragraph("<b>Repeticiones</b>",     styles["body"]),
            Paragraph("<b>Descanso (seg)</b>",   styles["body"]),
        ]]

        for detail in (day.details or []):
            exercise_name = (
                detail.training.name if detail.training else "—"
            )
            muscle_name = (
                detail.muscle_group.name
                if detail.muscle_group
                else (detail.training.muscle_group.name
                      if detail.training and detail.training.muscle_group
                      else "—")
            )
            rows.append([
                Paragraph(exercise_name, styles["body"]),
                Paragraph(muscle_name,   styles["body"]),
                Paragraph(str(detail.series or "—"),      styles["body"]),
                Paragraph(str(detail.repetitions or "—"), styles["body"]),
                Paragraph(str(detail.break_time or "—"),  styles["body"]),
            ])

        # Si el día solo tiene descripción libre (sin detalles estructurados)
        if len(rows) == 1 and day.description:
            rows.append([
                Paragraph(day.description, styles["body"]),
                "", "", "", "",
            ])
            exercise_tbl = Table(rows, colWidths=col_w)
            exercise_tbl.setStyle(TableStyle([
                ("BACKGROUND",   (0, 0), (-1, 0), PURPLE_LIGHT),
                ("SPAN",         (0, 1), (-1, 1)),
                ("FONTSIZE",     (0, 0), (-1, -1), 8),
                ("GRID",         (0, 0), (-1, -1), 0.3, GRAY_BORDER),
                ("TOPPADDING",   (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING",(0, 0), (-1, -1), 5),
                ("LEFTPADDING",  (0, 0), (-1, -1), 6),
                ("VALIGN",       (0, 0), (-1, -1), "MIDDLE"),
            ]))
        else:
            exercise_tbl = Table(rows, colWidths=col_w)
            exercise_tbl.setStyle(TableStyle([
                ("BACKGROUND",   (0, 0), (-1, 0), PURPLE_LIGHT),
                ("FONTNAME",     (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE",     (0, 0), (-1, -1), 8),
                ("GRID",         (0, 0), (-1, -1), 0.3, GRAY_BORDER),
                ("TOPPADDING",   (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING",(0, 0), (-1, -1), 5),
                ("LEFTPADDING",  (0, 0), (-1, -1), 6),
                ("VALIGN",       (0, 0), (-1, -1), "MIDDLE"),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [white, GRAY_BG]),
            ]))

        story.append(KeepTogether([day_header, exercise_tbl, Spacer(1, 0.35 * cm)]))

    # ── Footer ────────────────────────────────────────────────────────────────
    story.append(Spacer(1, 0.5 * cm))
    story.append(HRFlowable(width="100%", thickness=0.5, color=GRAY_BORDER))
    story.append(Spacer(1, 0.2 * cm))
    story.append(Paragraph(
        "Generado por Nutrientrena · nutrientrena.up.railway.app",
        styles["footer"],
    ))

    doc.build(story)
    return buffer.getvalue()
