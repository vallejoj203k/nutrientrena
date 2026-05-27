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
from reportlab.lib.enums import TA_CENTER

# ── Brand colors ──────────────────────────────────────────────────────────────
PURPLE      = HexColor("#5B2D8E")
PURPLE_LIGHT = HexColor("#EDE7F6")
PURPLE_MID  = HexColor("#7E57C2")
GRAY_BG     = HexColor("#F8F6FC")
GRAY_TEXT   = HexColor("#555555")
GRAY_BORDER = HexColor("#DDDDDD")


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
        "meal_name": ParagraphStyle(
            "MealName",
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
            fontSize=14,
            textColor=PURPLE,
            alignment=TA_CENTER,
        ),
        "footer": ParagraphStyle(
            "Footer",
            fontName="Helvetica",
            fontSize=8,
            textColor=HexColor("#AAAAAA"),
            alignment=TA_CENTER,
        ),
    }


def _macro_table(kcal, proteins, carbs, fats, styles):
    """Tarjeta de macros en la parte superior del documento."""
    def cell(value, label):
        return [
            Paragraph(str(value) if value is not None else "—", styles["macro_value"]),
            Paragraph(label, styles["macro_label"]),
        ]

    data = [[
        cell(f"{round(kcal)} kcal" if kcal else "—", "Calorías"),
        cell(f"{round(proteins)} g" if proteins else "—", "Proteínas"),
        cell(f"{round(carbs)} g" if carbs else "—", "Carbohidratos"),
        cell(f"{round(fats)} g" if fats else "—", "Grasas"),
    ]]

    tbl = Table(data, colWidths=[4.3 * cm] * 4)
    tbl.setStyle(TableStyle([
        ("BACKGROUND",   (0, 0), (-1, -1), GRAY_BG),
        ("GRID",         (0, 0), (-1, -1), 0.5, GRAY_BORDER),
        ("ALIGN",        (0, 0), (-1, -1), "CENTER"),
        ("VALIGN",       (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING",   (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING",(0, 0), (-1, -1), 10),
        ("ROUNDEDCORNERS", [6]),
    ]))
    return tbl


def generate_diet_pdf(diet) -> bytes:
    """
    Recibe un objeto Diet (con relaciones cargadas) y devuelve bytes PDF.
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
        Paragraph(diet.title or "Plan de Alimentación", styles["subtitle"]),
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

    # ── Macros ────────────────────────────────────────────────────────────────
    detail = diet.detail
    kcal = diet.calories
    proteins = detail.proteins if detail else None
    carbs    = detail.carbs    if detail else None
    fats     = detail.fats     if detail else None

    story.append(_macro_table(kcal, proteins, carbs, fats, styles))
    story.append(Spacer(1, 0.6 * cm))

    # ── Detalle del cliente (si existe) ───────────────────────────────────────
    if detail and any([detail.weight, detail.height, detail.age]):
        story.append(Paragraph("Datos del cliente", styles["section"]))
        info_rows = []
        if detail.weight:
            info_rows.append(["Peso", f"{detail.weight} kg"])
        if detail.height:
            info_rows.append(["Altura", f"{detail.height} cm"])
        if detail.age:
            info_rows.append(["Edad", f"{detail.age} años"])
        if detail.body_fat:
            info_rows.append(["Grasa corporal", f"{detail.body_fat}%"])

        info_tbl = Table(info_rows, colWidths=[4 * cm, 6 * cm])
        info_tbl.setStyle(TableStyle([
            ("FONTNAME",     (0, 0), (0, -1), "Helvetica-Bold"),
            ("FONTNAME",     (1, 0), (1, -1), "Helvetica"),
            ("FONTSIZE",     (0, 0), (-1, -1), 9),
            ("TEXTCOLOR",    (0, 0), (0, -1), PURPLE),
            ("TEXTCOLOR",    (1, 0), (1, -1), GRAY_TEXT),
            ("TOPPADDING",   (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING",(0, 0), (-1, -1), 4),
            ("LINEBELOW",    (0, 0), (-1, -2), 0.3, GRAY_BORDER),
        ]))
        story.append(info_tbl)
        story.append(Spacer(1, 0.4 * cm))

    # ── Comidas ───────────────────────────────────────────────────────────────
    story.append(Paragraph("Plan de comidas", styles["section"]))

    col_w = [doc.width * 0.42, doc.width * 0.15,
             doc.width * 0.14, doc.width * 0.14, doc.width * 0.15]

    for food in (diet.foods or []):
        # Encabezado de la comida
        meal_header = Table(
            [[Paragraph(food.name or "Comida", styles["meal_name"])]],
            colWidths=[doc.width],
        )
        meal_header.setStyle(TableStyle([
            ("BACKGROUND",    (0, 0), (-1, -1), PURPLE_MID),
            ("TOPPADDING",    (0, 0), (-1, -1), 7),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
            ("LEFTPADDING",   (0, 0), (-1, -1), 10),
        ]))

        # Tabla de alimentos
        rows = [[
            Paragraph("<b>Alimento</b>", styles["body"]),
            Paragraph("<b>Cantidad</b>", styles["body"]),
            Paragraph("<b>Prot.</b>",    styles["body"]),
            Paragraph("<b>Carbs.</b>",   styles["body"]),
            Paragraph("<b>Grasas</b>",   styles["body"]),
        ]]

        total_kcal = 0
        for dfa in (food.detail or []):
            aliment = dfa.aliment
            if not aliment:
                continue
            qty = dfa.quantity or aliment.quantity or 0
            name = aliment.name or "—"
            proteins_a = round(aliment.proteins or 0, 1)
            carbs_a    = round(aliment.carbohydrates or 0, 1)
            fats_a     = round(aliment.fats or 0, 1)
            kcal_a     = round(aliment.calories or 0, 1)
            total_kcal += kcal_a

            rows.append([
                Paragraph(name, styles["body"]),
                Paragraph(f"{qty} g", styles["body"]),
                Paragraph(f"{proteins_a} g", styles["body"]),
                Paragraph(f"{carbs_a} g", styles["body"]),
                Paragraph(f"{fats_a} g", styles["body"]),
            ])

        if total_kcal:
            rows.append([
                Paragraph(f"<b>Total: {round(total_kcal)} kcal</b>", styles["body"]),
                "", "", "", "",
            ])

        aliment_tbl = Table(rows, colWidths=col_w)
        aliment_tbl.setStyle(TableStyle([
            ("BACKGROUND",   (0, 0), (-1, 0), PURPLE_LIGHT),
            ("FONTNAME",     (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE",     (0, 0), (-1, -1), 8),
            ("GRID",         (0, 0), (-1, -1), 0.3, GRAY_BORDER),
            ("TOPPADDING",   (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING",(0, 0), (-1, -1), 4),
            ("LEFTPADDING",  (0, 0), (-1, -1), 6),
            ("VALIGN",       (0, 0), (-1, -1), "MIDDLE"),
            ("BACKGROUND",   (0, -1), (-1, -1), GRAY_BG),
            ("SPAN",         (0, -1), (-1, -1)),
        ]))

        story.append(KeepTogether([meal_header, aliment_tbl, Spacer(1, 0.3 * cm)]))

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
