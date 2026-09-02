"""
Generador de PDF para rutinas usando ReportLab.
"""
import io
import urllib.request
import ssl
import re
import json as _json
import html as _html
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


IMG_SIZE  = 1.8 * cm
THUMB_W   = 3.0 * cm
THUMB_H   = 1.7 * cm  # ~16:9


from app.pdf.comun import descanso as _descanso, num as _num, quien_de as _quien, txt as _txt  # noqa: E402

# Los días de la semana, para el reparto. Es la misma lista que la pantalla.
DIAS_SEMANA = ["Lunes", "Martes", "Mi\u00e9rcoles", "Jueves", "Viernes", "S\u00e1bado", "Domingo"]


def _estilos_plan():
    return {
        "eye": ParagraphStyle("Eye", fontName="Helvetica-Bold", fontSize=8,
                              textColor=HexColor("#C7D2FE"), leading=11),
        "tit": ParagraphStyle("Tit", fontName="Helvetica-Bold", fontSize=19,
                              textColor=WHITE, leading=23),
        "sub": ParagraphStyle("Sub", fontName="Helvetica", fontSize=9.5,
                              textColor=HexColor("#DDE1FB"), leading=13),
        "quien": ParagraphStyle("Quien", fontName="Helvetica-Bold", fontSize=11,
                                textColor=WHITE, alignment=TA_RIGHT, leading=14),
        "coach": ParagraphStyle("Coach", fontName="Helvetica", fontSize=8.5,
                                textColor=HexColor("#DDE1FB"), alignment=TA_RIGHT, leading=12),
        "pill": ParagraphStyle("Pill", fontName="Helvetica-Bold", fontSize=8.5,
                               textColor=WHITE, alignment=TA_RIGHT),
        "dia": ParagraphStyle("Dia", fontName="Helvetica-Bold", fontSize=15,
                              textColor=TEXT_DARK, leading=19),
        "dia_sub": ParagraphStyle("DiaSub", fontName="Helvetica", fontSize=9,
                                  textColor=GRAY_TEXT, leading=12),
        "dia_tag": ParagraphStyle("DiaTag", fontName="Helvetica-Bold", fontSize=7.5,
                                  textColor=INDIGO, alignment=TA_CENTER),
        "th": ParagraphStyle("Th", fontName="Helvetica-Bold", fontSize=7,
                             textColor=WHITE, alignment=TA_CENTER),
        "th_l": ParagraphStyle("ThL", fontName="Helvetica-Bold", fontSize=7,
                               textColor=WHITE, alignment=TA_LEFT),
        "ex": ParagraphStyle("Ex", fontName="Helvetica-Bold", fontSize=9.5,
                             textColor=TEXT_DARK, leading=12),
        "mg": ParagraphStyle("Mg", fontName="Helvetica", fontSize=8,
                             textColor=GRAY_TEXT, leading=11),
        "celda": ParagraphStyle("Celda", fontName="Helvetica-Bold", fontSize=9.5,
                                textColor=TEXT_DARK, alignment=TA_CENTER),
        "celda_g": ParagraphStyle("CeldaG", fontName="Helvetica", fontSize=9.5,
                                  textColor=GRAY_TEXT, alignment=TA_CENTER),
        "inten": ParagraphStyle("Inten", fontName="Helvetica-Bold", fontSize=9,
                                textColor=INDIGO, alignment=TA_CENTER),
    }


def _hero_rutina(routine, n_ejercicios, doc_width, e):
    """La cabecera: quién, qué plan y cuánto."""
    sub = " \u00b7 ".join([x for x in [
        routine.training,
        f"{routine.days} d\u00edas/semana" if routine.days else None,
        f"{n_ejercicios} ejercicios" if n_ejercicios else None,
    ] if x])

    izq = [Paragraph("PLAN DE ENTRENAMIENTO", e["eye"]), Spacer(1, 3),
           Paragraph(_txt(routine.name or "Rutina"), e["tit"])]
    if sub:
        izq += [Spacer(1, 2), Paragraph(_txt(sub), e["sub"])]

    cliente, coach = _quien(routine)
    der = []
    if cliente:
        der.append(Paragraph(_txt(cliente), e["quien"]))
    if coach:
        der.append(Paragraph("Coach \u00b7 " + _txt(coach), e["coach"]))
    der.append(Spacer(1, 5))
    pill = Table([[Paragraph("Alzum.io", e["pill"])]], colWidths=[2.1 * cm])
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


def _reparto(days):
    """En qué día de la semana cae cada día de la rutina.

    Igual que la pantalla: manda `weekday` si alguien lo ha repartido, y si no
    se cae al orden, que es lo que se hacía siempre.
    """
    hay = any(getattr(d, "weekday", None) is not None for d in days)
    fuera = {}
    for i, d in enumerate(days):
        wd = getattr(d, "weekday", None) if hay else i
        if wd is None or not (0 <= wd <= 6):
            continue
        fuera.setdefault(i, wd)
    return fuera


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


def generate_routine_pdf(routine) -> bytes:
    """Recibe un objeto Routine (con relaciones cargadas) y devuelve bytes PDF."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        leftMargin=1.6 * cm, rightMargin=1.6 * cm,
        topMargin=1.5 * cm, bottomMargin=1.8 * cm,
    )
    styles = _styles()
    e = _estilos_plan()
    story = []

    dias = list(routine.days_list or [])

    def _ejercicios_de(day):
        todos = list(day.details or [])
        for bloque in (day.blocks or []):
            todos.extend(bloque.exercises or [])
        todos.sort(key=lambda d: d.order_index or 0)
        return todos

    total = sum(len(_ejercicios_de(d)) for d in dias)
    story.append(_hero_rutina(routine, total, doc.width, e))
    story.append(Spacer(1, 0.6 * cm))

    reparto = _reparto(dias)
    # La columna de la imagen solo si algún ejercicio la tiene: vacía se lleva
    # dos centímetros de ancho a cambio de nada.
    hay_fotos = any((d.training.image if d.training else None)
                    for day in dias for d in _ejercicios_de(day))
    img_col = (IMG_SIZE + 0.25 * cm) if hay_fotos else 0
    resto = doc.width - img_col
    col_w = [c for c in
             [img_col, resto * 0.40, resto * 0.13, resto * 0.15, resto * 0.17, resto * 0.15]
             if c]

    for i, day in enumerate(dias):
        ejercicios = _ejercicios_de(day)
        nombre = day.day_name or f"D\u00eda {i + 1}"
        wd = reparto.get(i)
        # El título es el DÍA DE LA SEMANA, que es cuando el cliente entrena;
        # el nombre de la sesión va debajo y en la etiqueta.
        titulo = DIAS_SEMANA[wd] if wd is not None else nombre
        if ejercicios:
            sub = " \u00b7 ".join([x for x in [
                nombre if wd is not None else None,
                f"{len(ejercicios)} ejercicio" + ("s" if len(ejercicios) != 1 else ""),
                f"~{routine.time} min" if routine.time else None,
            ] if x])
        else:
            # Un día de descanso no tiene ejercicios ni dura 45 minutos.
            sub = "Sin entreno programado"

        etiqueta = Table([[Paragraph(_txt(nombre.upper()), e["dia_tag"])]], colWidths=[2.9 * cm])
        etiqueta.setStyle(TableStyle([
            ("BACKGROUND",    (0, 0), (-1, -1), INDIGO_PALE),
            ("TOPPADDING",    (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ]))
        cabecera = Table(
            [[[Paragraph(_txt(titulo), e["dia"]), Spacer(1, 2), Paragraph(_txt(sub), e["dia_sub"])],
              etiqueta]],
            colWidths=[doc.width * 0.7, doc.width * 0.3])
        cabecera.setStyle(TableStyle([
            ("VALIGN",       (0, 0), (-1, -1), "MIDDLE"),
            ("ALIGN",        (1, 0), (1, 0), "RIGHT"),
            ("LEFTPADDING",  (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ("LINEBELOW",    (0, 0), (-1, -1), 1.2, INDIGO),
        ]))

        if not ejercicios:
            # Un día de descanso se dice, no se deja en blanco: en blanco
            # parece que el PDF salió mal.
            vacio = Table([[Paragraph(
                _txt(day.description or "D\u00eda de descanso"), styles["body"])]],
                colWidths=[doc.width])
            vacio.setStyle(TableStyle([
                ("BACKGROUND",    (0, 0), (-1, -1), GRAY_BG),
                ("BOX",           (0, 0), (-1, -1), 0.7, GRAY_BORDER),
                ("TOPPADDING",    (0, 0), (-1, -1), 12),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
                ("LEFTPADDING",   (0, 0), (-1, -1), 14),
            ]))
            story.append(KeepTogether([cabecera, Spacer(1, 0.25 * cm), vacio, Spacer(1, 0.5 * cm)]))
            continue

        cab = ([Paragraph("", e["th"])] if hay_fotos else []) + [
            Paragraph("EJERCICIO", e["th_l"]),
            Paragraph("SERIES", e["th"]),
            Paragraph("REPS", e["th"]),
            Paragraph("INTENSIDAD", e["th"]),
            Paragraph("DESCANSO", e["th"]),
        ]
        filas = [cab]

        for d in ejercicios:
            tr = d.training
            nombre_ex = tr.name if tr else "\u2014"
            musculo = (d.muscle_group.name if d.muscle_group
                       else (tr.muscle_group.name if tr and tr.muscle_group else None))
            celda = [Paragraph(_txt(nombre_ex), e["ex"])]
            if musculo:
                celda.append(Paragraph(_txt(musculo), e["mg"]))
            video = tr.video_url if tr else None
            if video:
                celda.append(Spacer(1, 2))
                celda.append(Paragraph(
                    f'<a href="{_txt(video)}" color="#4F46E5"><font size="8"><u>Ver v\u00eddeo</u></font></a>',
                    styles["body"]))

            if d.intensity_value is not None:
                marca = ("RPE " + _num(d.intensity_value)) if (d.intensity_type or "").upper() == "RPE" \
                    else _num(d.intensity_value) + "%"
                inten = Paragraph(marca, e["inten"])
            else:
                inten = Paragraph("\u2014", e["celda_g"])

            filas.append(([_fetch_image(tr.image if tr else None) or ""] if hay_fotos else []) + [
                celda,
                Paragraph(str(d.series) if d.series else "\u2014", e["celda"]),
                Paragraph(_txt(d.repetitions) or "\u2014", e["celda"]),
                inten,
                Paragraph(_descanso(d.break_time), e["celda_g"]),
            ])

        tabla = Table(filas, colWidths=col_w, repeatRows=1)
        tabla.setStyle(TableStyle([
            ("BACKGROUND",    (0, 0), (-1, 0), INDIGO_MID),
            ("TOPPADDING",    (0, 0), (-1, 0), 8),
            ("BOTTOMPADDING", (0, 0), (-1, 0), 8),
            ("LINEBELOW",     (0, 1), (-1, -2), 0.5, HexColor("#F1F2F6")),
            ("BOX",           (0, 0), (-1, -1), 0.7, GRAY_BORDER),
            ("TOPPADDING",    (0, 1), (-1, -1), 9),
            ("BOTTOMPADDING", (0, 1), (-1, -1), 9),
            ("LEFTPADDING",   (0, 0), (-1, -1), 10),
            ("RIGHTPADDING",  (0, 0), (-1, -1), 10),
            ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
        ]))
        story.append(KeepTogether([cabecera, Spacer(1, 0.25 * cm), tabla, Spacer(1, 0.55 * cm)]))

    if not dias:
        story.append(Paragraph("Esta rutina no tiene d\u00edas configurados.", styles["body"]))

    story.append(Spacer(1, 0.3 * cm))
    story.append(HRFlowable(width="100%", thickness=0.5, color=GRAY_BORDER))
    story.append(Spacer(1, 0.2 * cm))
    story.append(Paragraph("Generado por Alzum.io", styles["footer"]))

    doc.build(story)
    return buffer.getvalue()
