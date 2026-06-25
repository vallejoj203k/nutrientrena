"""
Generador de PDF para dietas usando ReportLab.
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
        "brand": ParagraphStyle(
            "Brand",
            fontName="Helvetica-Bold",
            fontSize=20,
            textColor=WHITE,
            alignment=TA_LEFT,
        ),
        "brand_dot": ParagraphStyle(
            "BrandDot",
            fontName="Helvetica",
            fontSize=20,
            textColor=INDIGO_LIGHT,
            alignment=TA_LEFT,
        ),
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
        "meal_name": ParagraphStyle(
            "MealName",
            fontName="Helvetica-Bold",
            fontSize=10,
            textColor=WHITE,
        ),
        "body": ParagraphStyle(
            "Body",
            fontName="Helvetica",
            fontSize=9,
            textColor=TEXT_MID,
            spaceAfter=2,
        ),
        "body_bold": ParagraphStyle(
            "BodyBold",
            fontName="Helvetica-Bold",
            fontSize=9,
            textColor=TEXT_DARK,
        ),
        "macro_label": ParagraphStyle(
            "MacroLabel",
            fontName="Helvetica",
            fontSize=8,
            textColor=GRAY_TEXT,
            alignment=TA_CENTER,
        ),
        "macro_value": ParagraphStyle(
            "MacroValue",
            fontName="Helvetica-Bold",
            fontSize=15,
            textColor=INDIGO,
            alignment=TA_CENTER,
        ),
        "client_label": ParagraphStyle(
            "ClientLabel",
            fontName="Helvetica-Bold",
            fontSize=8,
            textColor=INDIGO,
        ),
        "client_value": ParagraphStyle(
            "ClientValue",
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
        "total_row": ParagraphStyle(
            "TotalRow",
            fontName="Helvetica-Bold",
            fontSize=8,
            textColor=INDIGO,
        ),
    }


def _header_table(title, doc_width, styles):
    """Banner superior con branding Alzum.io y título del plan."""
    brand_cell = Paragraph("<b>Alzum</b><font color='#818CF8'>.io</font>", ParagraphStyle(
        "BrandInline",
        fontName="Helvetica-Bold",
        fontSize=22,
        textColor=WHITE,
    ))
    type_cell = Paragraph("Plan de Alimentación", styles["doc_type"])
    title_cell = Paragraph(title or "Dieta", styles["subtitle"])

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


def _macro_table(kcal, proteins, carbs, fats, styles, doc_width):
    """Tarjeta de macros con 4 celdas."""
    def cell(value, label, color=INDIGO):
        return [
            Paragraph(str(value) if value is not None else "—",
                      ParagraphStyle("MV", fontName="Helvetica-Bold",
                                     fontSize=16, textColor=color, alignment=TA_CENTER)),
            Paragraph(label, styles["macro_label"]),
        ]

    data = [[
        cell(f"{round(kcal)} kcal" if kcal else "—",    "Calorías",      INDIGO),
        cell(f"{round(proteins)} g" if proteins else "—", "Proteínas",    INDIGO_MID),
        cell(f"{round(carbs)} g" if carbs else "—",       "Carbohidratos", INDIGO_MID),
        cell(f"{round(fats)} g" if fats else "—",         "Grasas",        INDIGO_LIGHT),
    ]]

    col = doc_width / 4
    tbl = Table(data, colWidths=[col] * 4)
    tbl.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (0, -1), INDIGO_PALE),
        ("BACKGROUND",    (1, 0), (2, -1), HexColor("#F0F0FF")),
        ("BACKGROUND",    (3, 0), (3, -1), GRAY_BG),
        ("LINEAFTER",     (0, 0), (2, -1), 0.5, GRAY_BORDER),
        ("ALIGN",         (0, 0), (-1, -1), "CENTER"),
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING",    (0, 0), (-1, -1), 12),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
        ("BOX",           (0, 0), (-1, -1), 0.5, GRAY_BORDER),
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


def generate_diet_pdf(diet) -> bytes:
    """Recibe un objeto Diet (con relaciones cargadas) y devuelve bytes PDF."""
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
    story.append(_header_table(diet.title, doc.width, styles))
    story.append(Spacer(1, 0.6 * cm))

    # ── Macros ───────────────────────────────────────────────────────────────
    detail   = diet.detail
    kcal     = diet.calories
    proteins = detail.proteins if detail else None
    carbs    = detail.carbs    if detail else None
    fats     = detail.fats     if detail else None

    story.append(_macro_table(kcal, proteins, carbs, fats, styles, doc.width))
    story.append(Spacer(1, 0.6 * cm))

    # ── Datos del cliente ─────────────────────────────────────────────────────
    if detail and any([detail.weight, detail.height, detail.age]):
        story.append(_section_header("Datos del cliente", styles))
        story.append(Spacer(1, 0.2 * cm))

        client_rows = []
        if detail.weight:
            client_rows.append([Paragraph("Peso",           styles["client_label"]), Paragraph(f"{detail.weight} kg",  styles["client_value"])])
        if detail.height:
            client_rows.append([Paragraph("Altura",         styles["client_label"]), Paragraph(f"{detail.height} cm",  styles["client_value"])])
        if detail.age:
            client_rows.append([Paragraph("Edad",           styles["client_label"]), Paragraph(f"{detail.age} años",   styles["client_value"])])
        if detail.body_fat:
            client_rows.append([Paragraph("Grasa corporal", styles["client_label"]), Paragraph(f"{detail.body_fat}%",  styles["client_value"])])

        info_tbl = Table(client_rows, colWidths=[4 * cm, doc.width - 4 * cm])
        info_tbl.setStyle(TableStyle([
            ("BACKGROUND",    (0, 0), (-1, -1), GRAY_BG),
            ("TOPPADDING",    (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("LEFTPADDING",   (0, 0), (-1, -1), 10),
            ("LINEBELOW",     (0, 0), (-1, -2), 0.3, GRAY_BORDER),
            ("BOX",           (0, 0), (-1, -1), 0.5, GRAY_BORDER),
        ]))
        story.append(info_tbl)
        story.append(Spacer(1, 0.4 * cm))

    # ── Plan de comidas ───────────────────────────────────────────────────────
    story.append(_section_header("Plan de comidas", styles))
    story.append(Spacer(1, 0.2 * cm))

    col_w = [
        doc.width * 0.38,
        doc.width * 0.14,
        doc.width * 0.14,
        doc.width * 0.14,
        doc.width * 0.20,
    ]

    for food in (diet.foods or []):
        meal_header = Table(
            [[Paragraph(food.name or "Comida", styles["meal_name"])]],
            colWidths=[doc.width],
        )
        meal_header.setStyle(TableStyle([
            ("BACKGROUND",    (0, 0), (-1, -1), INDIGO),
            ("TOPPADDING",    (0, 0), (-1, -1), 7),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
            ("LEFTPADDING",   (0, 0), (-1, -1), 12),
        ]))

        rows = [[
            Paragraph("<b>Alimento</b>",   styles["body"]),
            Paragraph("<b>Cantidad</b>",   styles["body"]),
            Paragraph("<b>Prot.</b>",      styles["body"]),
            Paragraph("<b>Carbs.</b>",     styles["body"]),
            Paragraph("<b>Grasas</b>",     styles["body"]),
        ]]

        total_kcal = 0
        for dfa in (food.detail or []):
            aliment = dfa.aliment
            if not aliment:
                continue
            qty        = dfa.quantity or aliment.quantity or 0
            name       = aliment.name or "—"
            proteins_a = round(aliment.proteins or 0, 1)
            carbs_a    = round(aliment.carbohydrates or 0, 1)
            fats_a     = round(aliment.fats or 0, 1)
            kcal_a     = round(aliment.calories or 0, 1)
            total_kcal += kcal_a

            rows.append([
                Paragraph(name,             styles["body"]),
                Paragraph(f"{qty} g",       styles["body"]),
                Paragraph(f"{proteins_a} g", styles["body"]),
                Paragraph(f"{carbs_a} g",   styles["body"]),
                Paragraph(f"{fats_a} g",    styles["body"]),
            ])

        if total_kcal:
            rows.append([
                Paragraph(f"Total: {round(total_kcal)} kcal", styles["total_row"]),
                "", "", "", "",
            ])

        n = len(rows)
        row_bgs = []
        for i in range(1, n - (1 if total_kcal else 0)):
            row_bgs.append(("BACKGROUND", (0, i), (-1, i), WHITE if i % 2 else GRAY_BG))

        aliment_tbl = Table(rows, colWidths=col_w)
        style_cmds = [
            ("BACKGROUND",    (0, 0), (-1, 0), INDIGO_PALE),
            ("TEXTCOLOR",     (0, 0), (-1, 0), INDIGO),
            ("FONTSIZE",      (0, 0), (-1, -1), 8),
            ("GRID",          (0, 0), (-1, -1), 0.3, GRAY_BORDER),
            ("TOPPADDING",    (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("LEFTPADDING",   (0, 0), (-1, -1), 7),
            ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
            ("BACKGROUND",    (0, n - 1), (-1, n - 1), INDIGO_PALE),
            ("SPAN",          (0, n - 1), (-1, n - 1)),
            ("TEXTCOLOR",     (0, n - 1), (-1, n - 1), INDIGO),
        ] + row_bgs

        aliment_tbl.setStyle(TableStyle(style_cmds))
        story.append(KeepTogether([meal_header, aliment_tbl, Spacer(1, 0.35 * cm)]))

    # ── Footer ────────────────────────────────────────────────────────────────
    story.append(Spacer(1, 0.4 * cm))
    story.append(HRFlowable(width="100%", thickness=0.5, color=GRAY_BORDER))
    story.append(Spacer(1, 0.2 * cm))
    story.append(Paragraph("Generado por Alzum.io", styles["footer"]))

    doc.build(story)
    return buffer.getvalue()
