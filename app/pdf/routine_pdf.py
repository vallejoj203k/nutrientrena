"""
Generador de PDF para rutinas usando ReportLab.
"""
import io
import urllib.request
import ssl
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib.colors import HexColor, white
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, KeepTogether, Image,
)
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT

# ── Brand colors (Alzum.io) ───────────────────────────────────────────────────
INDIGO       = HexColor("#4F46E5")
INDIGO_DARK  = HexColor("#4338CA")
INDIGO_PALE  = HexColor("#EEF2FF")
INDIGO_MID   = HexColor("#6366F1")
INDIGO_LIGHT = HexColor("#818CF8")
GRAY_BG      = HexColor("#F9FAFB")
GRAY_BORDER  = HexColor("#E5E7EB")
GRAY_TEXT    = HexColor("#6B7280")
TEXT_DARK    = HexColor("#111827")
TEXT_MID     = HexColor("#374151")
WHITE        = white


def _styles():
    return {
        "doc_type": ParagraphStyle(
            "DocType",
            fontName="Helvetica",
            fontSize=10,
            textColor=HexColor("#C7D2FE"),
            alignment=TA_RIGHT,
        ),
        "subtitle": ParagraphStyle(
            "Subtitle",
            fontName="Helvetica-Bold",
            fontSize=13,
            textColor=WHITE,
            alignment=TA_RIGHT,
        ),
        "section": ParagraphStyle(
            "Section",
            fontName="Helvetica-Bold",
            fontSize=11,
            textColor=INDIGO,
            spaceBefore=16,
            spaceAfter=6,
        ),
        "day_name": ParagraphStyle(
            "DayName",
            fontName="Helvetica-Bold",
            fontSize=10,
            textColor=WHITE,
        ),
        "body": ParagraphStyle(
            "Body",
            fontName="Helvetica",
            fontSize=8,
            textColor=TEXT_MID,
            spaceAfter=2,
        ),
        "body_bold": ParagraphStyle(
            "BodyBold",
            fontName="Helvetica-Bold",
            fontSize=8,
            textColor=TEXT_DARK,
        ),
        "tag": ParagraphStyle(
            "Tag",
            fontName="Helvetica-Bold",
            fontSize=8,
            textColor=INDIGO,
        ),
        "info_label": ParagraphStyle(
            "InfoLabel",
            fontName="Helvetica-Bold",
            fontSize=8,
            textColor=INDIGO,
        ),
        "info_value": ParagraphStyle(
            "InfoValue",
            fontName="Helvetica",
            fontSize=8,
            textColor=TEXT_MID,
        ),
        "footer": ParagraphStyle(
            "Footer",
            fontName="Helvetica",
            fontSize=8,
            textColor=GRAY_TEXT,
            alignment=TA_CENTER,
        ),
    }


IMG_SIZE = 1.8 * cm


def _fetch_image(url: str):
    """Download image and return a ReportLab Image flowable, or None."""
    if not url:
        return None

    try:
        from app.config import settings
        import boto3
        base = (settings.R2_PUBLIC_URL or "").rstrip("/")
        if settings.AWS_ACCESS_KEY_ID and settings.AWS_BUCKET and base and url.startswith(base):
            key = url[len(base):].lstrip("/")
            r2 = boto3.client(
                "s3",
                endpoint_url="https://77925e3b1a6f6513bce155f71f6aa790.r2.cloudflarestorage.com",
                aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                region_name="auto",
            )
            obj = r2.get_object(Bucket=settings.AWS_BUCKET, Key=key)
            data = obj["Body"].read()
            img = Image(io.BytesIO(data), width=IMG_SIZE, height=IMG_SIZE)
            img.hAlign = "CENTER"
            return img
    except Exception as e:
        print(f"PDF image R2 error ({url}): {e}")

    try:
        ctx = ssl.create_default_context()
        req = urllib.request.Request(url, headers={"User-Agent": "Alzum.io/1.0"})
        with urllib.request.urlopen(req, timeout=10, context=ctx) as resp:
            data = resp.read()
        img = Image(io.BytesIO(data), width=IMG_SIZE, height=IMG_SIZE)
        img.hAlign = "CENTER"
        return img
    except Exception as e:
        print(f"PDF image HTTP error ({url}): {e}")
        return None


def _header_table(title, doc_width, styles):
    """Banner superior con branding Alzum.io y nombre de la rutina."""
    brand_cell = Paragraph("<b>Alzum</b><font color='#818CF8'>.io</font>", ParagraphStyle(
        "BrandInline",
        fontName="Helvetica-Bold",
        fontSize=22,
        textColor=WHITE,
    ))
    type_cell  = Paragraph("Plan de Entrenamiento", styles["doc_type"])
    title_cell = Paragraph(title or "Rutina", styles["subtitle"])

    tbl = Table(
        [[brand_cell, title_cell], ["", type_cell]],
        colWidths=[doc_width * 0.45, doc_width * 0.55],
    )
    tbl.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), INDIGO),
        ("TOPPADDING",    (0, 0), (-1, -1), 16),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 16),
        ("LEFTPADDING",   (0, 0), (-1, -1), 18),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 18),
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
        ("SPAN",          (0, 0), (0, 1)),
    ]))
    return tbl


def _section_header(text, styles):
    """Título de sección con barra izquierda de color."""
    tbl = Table(
        [[Paragraph(text, styles["section"])]],
        colWidths=None,
    )
    tbl.setStyle(TableStyle([
        ("LEFTPADDING",   (0, 0), (-1, -1), 10),
        ("TOPPADDING",    (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
        ("LINEBEFORE",    (0, 0), (-1, -1), 3, INDIGO),
    ]))
    return tbl


def _info_table(routine, styles, doc_width):
    """Tarjeta con info general de la rutina."""
    rows = []
    if routine.training:
        rows.append([Paragraph("Tipo de entrenamiento", styles["info_label"]),
                     Paragraph(routine.training,         styles["info_value"])])
    if routine.days:
        rows.append([Paragraph("Días por semana",       styles["info_label"]),
                     Paragraph(str(routine.days),        styles["info_value"])])
    if routine.time:
        rows.append([Paragraph("Duración por sesión",   styles["info_label"]),
                     Paragraph(f"{routine.time} min",   styles["info_value"])])
    if routine.training_level and routine.training_level.description:
        rows.append([Paragraph("Nivel",                 styles["info_label"]),
                     Paragraph(routine.training_level.description, styles["info_value"])])
    if routine.gender and routine.gender.description:
        rows.append([Paragraph("Género",                styles["info_label"]),
                     Paragraph(routine.gender.description, styles["info_value"])])

    if not rows:
        return None

    col_label = 5 * cm
    tbl = Table(rows, colWidths=[col_label, doc_width - col_label])
    tbl.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), GRAY_BG),
        ("TOPPADDING",    (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING",   (0, 0), (-1, -1), 12),
        ("LINEBELOW",     (0, 0), (-1, -2), 0.3, GRAY_BORDER),
        ("BOX",           (0, 0), (-1, -1), 0.5, GRAY_BORDER),
    ]))
    return tbl


def generate_routine_pdf(routine) -> bytes:
    """Recibe un objeto Routine (con relaciones cargadas) y devuelve bytes PDF."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=1.8 * cm,
        rightMargin=1.8 * cm,
        topMargin=1.8 * cm,
        bottomMargin=2 * cm,
    )

    styles = _styles()
    story = []

    # ── Header ───────────────────────────────────────────────────────────────
    story.append(_header_table(routine.name, doc.width, styles))
    story.append(Spacer(1, 0.6 * cm))

    # ── Info general ──────────────────────────────────────────────────────────
    info_tbl = _info_table(routine, styles, doc.width)
    if info_tbl:
        story.append(info_tbl)
        story.append(Spacer(1, 0.5 * cm))

    # ── Programa de entrenamiento ─────────────────────────────────────────────
    story.append(_section_header("Programa de entrenamiento", styles))
    story.append(Spacer(1, 0.2 * cm))

    # col widths: img | ejercicio | músculo | series | reps | descanso
    img_col = IMG_SIZE + 0.2 * cm
    remaining = doc.width - img_col
    col_w = [
        img_col,
        remaining * 0.30,
        remaining * 0.22,
        remaining * 0.12,
        remaining * 0.18,
        remaining * 0.18,
    ]

    for day in (routine.days_list or []):
        day_header = Table(
            [[Paragraph(day.day_name or "Día", styles["day_name"])]],
            colWidths=[doc.width],
        )
        day_header.setStyle(TableStyle([
            ("BACKGROUND",    (0, 0), (-1, -1), INDIGO),
            ("TOPPADDING",    (0, 0), (-1, -1), 7),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
            ("LEFTPADDING",   (0, 0), (-1, -1), 12),
        ]))

        rows = [[
            Paragraph("<b>Img</b>",          styles["body"]),
            Paragraph("<b>Ejercicio</b>",    styles["body"]),
            Paragraph("<b>Músculo</b>",      styles["body"]),
            Paragraph("<b>Series</b>",       styles["body"]),
            Paragraph("<b>Reps</b>",         styles["body"]),
            Paragraph("<b>Descanso</b>",     styles["body"]),
        ]]

        all_details = list(day.details or [])
        for block in (day.blocks or []):
            all_details.extend(block.exercises or [])
        all_details.sort(key=lambda d: d.order_index or 0)

        for detail in all_details:
            training      = detail.training
            exercise_name = training.name if training else "—"
            muscle_name   = (
                detail.muscle_group.name
                if detail.muscle_group
                else (training.muscle_group.name
                      if training and training.muscle_group
                      else "—")
            )
            img_cell = _fetch_image(training.image if training else None) or Paragraph("—", styles["body"])
            rows.append([
                img_cell,
                Paragraph(exercise_name,               styles["body"]),
                Paragraph(muscle_name,                 styles["body"]),
                Paragraph(str(detail.series or "—"),   styles["body"]),
                Paragraph(str(detail.repetitions or "—"), styles["body"]),
                Paragraph(str(detail.break_time or "—"),  styles["body"]),
            ])

        # Día con solo descripción libre
        if len(rows) == 1 and not all_details and day.description:
            rows.append([
                "",
                Paragraph(day.description, styles["body"]),
                "", "", "", "",
            ])
            exercise_tbl = Table(rows, colWidths=col_w)
            exercise_tbl.setStyle(TableStyle([
                ("BACKGROUND",    (0, 0), (-1, 0), INDIGO_PALE),
                ("TEXTCOLOR",     (0, 0), (-1, 0), INDIGO),
                ("SPAN",          (1, 1), (-1, 1)),
                ("FONTSIZE",      (0, 0), (-1, -1), 8),
                ("GRID",          (0, 0), (-1, -1), 0.3, GRAY_BORDER),
                ("TOPPADDING",    (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ("LEFTPADDING",   (0, 0), (-1, -1), 7),
                ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
            ]))
        else:
            n = len(rows)
            row_bgs = []
            for i in range(1, n):
                row_bgs.append(("BACKGROUND", (0, i), (-1, i), WHITE if i % 2 else GRAY_BG))

            exercise_tbl = Table(
                rows,
                colWidths=col_w,
                rowHeights=[None] + [IMG_SIZE + 0.4 * cm] * (n - 1),
            )
            exercise_tbl.setStyle(TableStyle([
                ("BACKGROUND",    (0, 0), (-1, 0), INDIGO_PALE),
                ("TEXTCOLOR",     (0, 0), (-1, 0), INDIGO),
                ("FONTSIZE",      (0, 0), (-1, -1), 8),
                ("GRID",          (0, 0), (-1, -1), 0.3, GRAY_BORDER),
                ("TOPPADDING",    (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("LEFTPADDING",   (0, 0), (-1, -1), 7),
                ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
            ] + row_bgs))

        story.append(KeepTogether([day_header, exercise_tbl, Spacer(1, 0.35 * cm)]))

    # ── Footer ────────────────────────────────────────────────────────────────
    story.append(Spacer(1, 0.4 * cm))
    story.append(HRFlowable(width="100%", thickness=0.5, color=GRAY_BORDER))
    story.append(Spacer(1, 0.2 * cm))
    story.append(Paragraph("Generado por Alzum.io", styles["footer"]))

    doc.build(story)
    return buffer.getvalue()
