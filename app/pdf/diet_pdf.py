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


def _num(v):
    """80.0 se escribe 80, y 0.5 se queda en 0.5."""
    try:
        f = float(v)
    except (TypeError, ValueError):
        return "\u2014"
    return str(int(f)) if f == int(f) else str(round(f, 2))


def _txt(v) -> str:
    """Texto para reportlab, que interpreta `< >` como etiquetas.

    Sin esto, un alimento llamado "Yogur <2% MG>" no sale mal: DESAPARECE, y
    el PDF se entrega con una línea menos sin que nada avise.
    """
    return (str(v or "")
            .replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


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
        # ── El diseño del plan ──────────────────────────────────────────
        "hero_eye": ParagraphStyle(
            "HeroEye", fontName="Helvetica-Bold", fontSize=8,
            textColor=HexColor("#C7D2FE"), alignment=TA_LEFT, leading=11),
        "hero_title": ParagraphStyle(
            "HeroTitle", fontName="Helvetica-Bold", fontSize=19,
            textColor=WHITE, alignment=TA_LEFT, leading=23),
        "hero_sub": ParagraphStyle(
            "HeroSub", fontName="Helvetica", fontSize=9.5,
            textColor=HexColor("#DDE1FB"), alignment=TA_LEFT, leading=13),
        "hero_who": ParagraphStyle(
            "HeroWho", fontName="Helvetica-Bold", fontSize=11,
            textColor=WHITE, alignment=TA_RIGHT, leading=14),
        "hero_coach": ParagraphStyle(
            "HeroCoach", fontName="Helvetica", fontSize=8.5,
            textColor=HexColor("#DDE1FB"), alignment=TA_RIGHT, leading=12),
        "hero_pill": ParagraphStyle(
            "HeroPill", fontName="Helvetica-Bold", fontSize=8.5,
            textColor=WHITE, alignment=TA_RIGHT),
        "stat_lbl": ParagraphStyle(
            "StatLbl", fontName="Helvetica-Bold", fontSize=7,
            textColor=GRAY_TEXT, alignment=TA_LEFT, leading=9),
        "stat_val": ParagraphStyle(
            "StatVal", fontName="Helvetica-Bold", fontSize=15,
            textColor=TEXT_DARK, alignment=TA_LEFT, leading=18),
        "meal_kcal": ParagraphStyle(
            "MealKcal", fontName="Helvetica-Bold", fontSize=9.5,
            textColor=WHITE, alignment=TA_RIGHT),
        "th": ParagraphStyle(
            "Th", fontName="Helvetica-Bold", fontSize=7,
            textColor=GRAY_TEXT, alignment=TA_LEFT),
        "th_r": ParagraphStyle(
            "ThR", fontName="Helvetica-Bold", fontSize=7,
            textColor=GRAY_TEXT, alignment=TA_RIGHT),
        "food": ParagraphStyle(
            "Food", fontName="Helvetica", fontSize=10,
            textColor=TEXT_DARK, leading=13),
        "food_qty": ParagraphStyle(
            "FoodQty", fontName="Helvetica-Bold", fontSize=10,
            textColor=TEXT_DARK, alignment=TA_RIGHT),
        "total_row": ParagraphStyle(
            "TotalRow",
            fontName="Helvetica-Bold",
            fontSize=8,
            textColor=INDIGO,
        ),
    }


def _quien(diet):
    """El cliente de la dieta y su coach, para la cabecera.

    Va aquí y no en el router porque el PDF se genera desde tres sitios; si
    cada uno tuviera que pasarlos, el que se olvidara sacaría un plan sin
    nombre y nadie lo notaría hasta tenerlo impreso. Si algo falla se
    devuelven vacíos: un PDF sin nombre es peor que ninguno, pero un PDF que
    no se genera es todavía peor.
    """
    cliente = coach = ""
    try:
        u = getattr(diet, "user", None)
        if u is not None:
            cliente = (getattr(u, "name", "") or "").strip()
        from sqlalchemy.orm import object_session
        ses = object_session(diet)
        if ses is not None and u is not None:
            from app.models.user import User, UserDetail, UserParent
            det = ses.query(UserDetail).filter(UserDetail.user_id == u.id).first()
            if det is not None:
                if not cliente:
                    cliente = (f"{det.name or ''} {det.last_name or ''}").strip()
                lazo = ses.query(UserParent).filter(
                    UserParent.user_detail_id == det.id).first()
                if lazo is not None:
                    pa = ses.query(UserDetail).filter(
                        UserDetail.id == lazo.parent_user_detail_id).first()
                    if pa is not None:
                        coach = (f"{pa.name or ''} {pa.last_name or ''}").strip()
    except Exception:
        pass
    return cliente, coach


def _hero(diet, kcal, n_comidas, doc_width, styles):
    """La cabecera del plan: quién, qué y cuánto."""
    tipo = None
    try:
        tipo = (diet.type.description if diet.type else None) or None
    except Exception:
        tipo = None
    sub = " \u00b7 ".join([x for x in [
        tipo,
        f"{round(kcal)} kcal" if kcal else None,
        f"{n_comidas} comida{'s' if n_comidas != 1 else ''}/d\u00eda" if n_comidas else None,
    ] if x])

    titulo = _txt(diet.title or "Plan de alimentaci\u00f3n")
    if kcal:
        titulo += f" \u00b7 {round(kcal)}kcal"

    izq = [
        Paragraph("PLAN DE ALIMENTACI\u00d3N", styles["hero_eye"]),
        Spacer(1, 3),
        Paragraph(titulo, styles["hero_title"]),
    ]
    if sub:
        izq += [Spacer(1, 2), Paragraph(_txt(sub), styles["hero_sub"])]

    cliente, coach = _quien(diet)
    der = []
    if cliente:
        der.append(Paragraph(_txt(cliente), styles["hero_who"]))
    if coach:
        der.append(Paragraph("Coach \u00b7 " + _txt(coach), styles["hero_coach"]))
    der.append(Spacer(1, 5))
    # Con el ancho a ojo la pastilla se estira a toda la columna y deja una
    # barra de color cruzando la cabecera. Se le da el de su texto.
    pill = Table([[Paragraph("Alzum.io", styles["hero_pill"])]], colWidths=[2.1 * cm])
    pill.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), HexColor("#6F72E8")),
        ("TOPPADDING",    (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING",   (0, 0), (-1, -1), 9),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 9),
    ]))
    der.append(Table([[pill]], style=TableStyle([
        ("ALIGN", (0, 0), (-1, -1), "RIGHT"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0), ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ])))

    tbl = Table([[izq, der]], colWidths=[doc_width * 0.62, doc_width * 0.38])
    tbl.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), INDIGO_MID),
        ("VALIGN",        (0, 0), (0, 0), "MIDDLE"),
        ("VALIGN",        (1, 0), (1, 0), "TOP"),
        ("TOPPADDING",    (0, 0), (-1, -1), 18),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 18),
        ("LEFTPADDING",   (0, 0), (-1, -1), 20),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 20),
    ]))
    return tbl


# El punto de color de cada cifra. Un icono de verdad necesitaría una fuente
# con esos glifos, y Helvetica los sustituye en silencio: la lección de la
# casilla ☐ que salía como una "n" en la lista de la compra.
_PUNTOS = [("#F97316", "Calor\u00edas"), ("#16A34A", "Prote\u00ednas"),
           ("#F59E0B", "Carbohidratos"), ("#EF4444", "Grasas")]


def _macro_table(kcal, proteins, carbs, fats, styles, doc_width):
    """Las cuatro cifras del día, cada una en su caja."""
    valores = [
        (f"{round(kcal)}" if kcal else "0", "kcal"),
        (f"{round(proteins)}" if proteins else "0", "g"),
        (f"{round(carbs)}" if carbs else "0", "g"),
        (f"{round(fats)}" if fats else "0", "g"),
    ]

    cajas = []
    for (color, etiqueta), (valor, unidad) in zip(_PUNTOS, valores):
        cabecera = Paragraph(
            f'<font color="{color}">\u25cf</font> {etiqueta.upper()}', styles["stat_lbl"])
        cifra = Paragraph(
            f'{valor} <font size="8" color="#9CA3AF">{unidad}</font>', styles["stat_val"])
        caja = Table([[cabecera], [cifra]], colWidths=[(doc_width - 3 * 8) / 4])
        caja.setStyle(TableStyle([
            ("BOX",           (0, 0), (-1, -1), 0.7, GRAY_BORDER),
            ("TOPPADDING",    (0, 0), (-1, 0), 10),
            ("BOTTOMPADDING", (0, 0), (-1, 0), 1),
            ("TOPPADDING",    (0, 1), (-1, 1), 0),
            ("BOTTOMPADDING", (0, 1), (-1, 1), 10),
            ("LEFTPADDING",   (0, 0), (-1, -1), 11),
            ("RIGHTPADDING",  (0, 0), (-1, -1), 8),
        ]))
        cajas.append(caja)

    fila = Table([cajas], colWidths=[doc_width / 4] * 4)
    fila.setStyle(TableStyle([
        ("LEFTPADDING",   (0, 0), (0, -1), 0),
        ("RIGHTPADDING",  (-1, 0), (-1, -1), 0),
        ("LEFTPADDING",   (1, 0), (-1, -1), 4),
        ("RIGHTPADDING",  (0, 0), (-2, -1), 4),
        ("TOPPADDING",    (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
        ("VALIGN",        (0, 0), (-1, -1), "TOP"),
    ]))
    return fila


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
    from app.core.macros import escalar, unidad_de

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        leftMargin=1.6 * cm, rightMargin=1.6 * cm,
        topMargin=1.5 * cm, bottomMargin=1.8 * cm,
    )
    styles = _styles()
    story = []
    comidas = list(diet.foods or [])

    # Las cuatro cifras se SUMAN de los alimentos, con su porción. Antes las
    # kcal de cada comida sumaban `aliment.calories` a pelo —el valor por 100 g,
    # sin mirar cuántos gramos había— y los macros de la cabecera salían de lo
    # que se escribió al crear la dieta. El PDF es lo que el cliente se lleva
    # impreso: ahí un número inventado no tiene quien lo desmienta.
    def _suma(campo):
        return sum(
            escalar(getattr(d.aliment, campo, None), d.aliment, d.quantity)
            for f in comidas for d in (f.detail or []) if d.aliment)

    kcal = _suma("calories")
    prot = _suma("proteins")
    carb = _suma("carbohydrates")
    gras = _suma("fats")

    story.append(_hero(diet, kcal, len(comidas), doc.width, styles))
    story.append(Spacer(1, 0.55 * cm))
    story.append(_macro_table(kcal, prot, carb, gras, styles, doc.width))
    story.append(Spacer(1, 0.6 * cm))

    # ── Las comidas ──────────────────────────────────────────────────────────
    for food in comidas:
        titulo = _txt(food.name or "Comida")
        if getattr(food, "time", None):
            titulo += f'  <font color="#C7D2FE">{_txt(str(food.time)[:5])}</font>'
        if food.subtitle:
            # El cliente se lleva el PDF impreso a la cocina: si el subtítulo
            # solo estuviera en la app, ahí abajo pondría "Desayuno" y nada más.
            titulo += f'  <font size="9" color="#C7D2FE">\u00b7 {_txt(food.subtitle)}</font>'

        kcal_comida = sum(
            escalar(d.aliment.calories, d.aliment, d.quantity)
            for d in (food.detail or []) if d.aliment)

        barra = Table(
            [[Paragraph(titulo, styles["meal_name"]),
              Paragraph(f"{round(kcal_comida)} kcal", styles["meal_kcal"])]],
            colWidths=[doc.width * 0.68, doc.width * 0.32])
        barra.setStyle(TableStyle([
            ("BACKGROUND",    (0, 0), (-1, -1), INDIGO_MID),
            ("TOPPADDING",    (0, 0), (-1, -1), 9),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 9),
            ("LEFTPADDING",   (0, 0), (-1, -1), 14),
            ("RIGHTPADDING",  (0, 0), (-1, -1), 14),
            ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
        ]))

        filas = [[Paragraph("INGREDIENTE", styles["th"]),
                  Paragraph("CANTIDAD", styles["th_r"])]]
        for d in (food.detail or []):
            a = d.aliment
            if not a:
                continue
            cant = d.quantity if d.quantity is not None else a.quantity
            nombre = _txt(a.name or "\u2014")
            if getattr(d, "subtitle", None):
                nombre += f'<br/><font size="8" color="#9CA3AF">{_txt(d.subtitle)}</font>'
            # La unidad, del alimento. Poner "g" a todo convertía dos huevos en
            # "2 g" con las kcal de dos unidades enteras.
            filas.append([
                Paragraph(nombre, styles["food"]),
                Paragraph(f"{_num(cant)} {unidad_de(a)}", styles["food_qty"]),
            ])
        if len(filas) == 1:
            filas.append([Paragraph("Sin alimentos en esta comida", styles["body"]), ""])

        tabla = Table(filas, colWidths=[doc.width * 0.72, doc.width * 0.28])
        tabla.setStyle(TableStyle([
            ("BACKGROUND",    (0, 0), (-1, 0), HexColor("#F8F9FB")),
            ("LINEBELOW",     (0, 0), (-1, -2), 0.5, HexColor("#F1F2F6")),
            ("BOX",           (0, 0), (-1, -1), 0.7, GRAY_BORDER),
            ("TOPPADDING",    (0, 0), (-1, 0), 6),
            ("BOTTOMPADDING", (0, 0), (-1, 0), 6),
            ("TOPPADDING",    (0, 1), (-1, -1), 9),
            ("BOTTOMPADDING", (0, 1), (-1, -1), 9),
            ("LEFTPADDING",   (0, 0), (-1, -1), 14),
            ("RIGHTPADDING",  (0, 0), (-1, -1), 14),
            ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
        ]))
        story.append(KeepTogether([barra, tabla, Spacer(1, 0.45 * cm)]))

    # ── Datos del cliente, al final ──────────────────────────────────────────
    detail = diet.detail
    if detail and any([detail.weight, detail.height, detail.age]):
        story.append(_section_header("Datos del cliente", styles))
        story.append(Spacer(1, 0.2 * cm))
        campos = [("Peso", detail.weight, "kg"), ("Altura", detail.height, "cm"),
                  ("Edad", detail.age, "a\u00f1os"), ("Grasa corporal", detail.body_fat, "%")]
        cr = [[Paragraph(n, styles["client_label"]),
               Paragraph(f"{v}{u}" if u == "%" else f"{v} {u}".strip(), styles["client_value"])]
              for n, v, u in campos if v]
        info = Table(cr, colWidths=[4 * cm, doc.width - 4 * cm])
        info.setStyle(TableStyle([
            ("BACKGROUND",    (0, 0), (-1, -1), GRAY_BG),
            ("TOPPADDING",    (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("LEFTPADDING",   (0, 0), (-1, -1), 10),
            ("LINEBELOW",     (0, 0), (-1, -2), 0.3, GRAY_BORDER),
            ("BOX",           (0, 0), (-1, -1), 0.5, GRAY_BORDER),
        ]))
        story.append(info)

    story.append(Spacer(1, 0.4 * cm))
    story.append(HRFlowable(width="100%", thickness=0.5, color=GRAY_BORDER))
    story.append(Spacer(1, 0.2 * cm))
    story.append(Paragraph("Generado por Alzum.io", styles["footer"]))

    doc.build(story)
    return buffer.getvalue()
