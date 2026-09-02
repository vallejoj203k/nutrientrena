"""El PDF de la rutina: el papel con el que el cliente entrena.

Rehecho para que se vea como el diseño, y con las mismas cosas que importan
más que el aspecto:

  · El título de cada día es el DÍA DE LA SEMANA en el que entrena, sacado del
    reparto. Antes salía el nombre de la sesión ("Empuje") y el cliente tenía
    que acordarse de cuándo tocaba.
  · El descanso se lee: 120 segundos son 2', no "120".
  · La intensidad aparece. Estaba guardada y no se imprimía, así que el RPE
    que el coach había puesto no llegaba a quien entrena.
  · Y un día de descanso lo dice, en vez de quedarse en blanco pareciendo que
    el PDF salió mal.

Las comprobaciones leen el texto DE DENTRO del PDF: mirar que empieza por
"%PDF" es compatible con una página en blanco.
"""
import base64
import re
import zlib

from app.pdf.routine_pdf import generate_routine_pdf


def _texto(pdf):
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
    return b"".join(partes).decode("latin-1")


class _O:
    def __init__(self, **k):
        self.__dict__.update(k)


def _ex(nombre, musculo=None, series=None, reps=None, descanso=None,
        inten=None, tipo="RPE", orden=0, video=None):
    return _O(training=_O(name=nombre, image=None, video_url=video,
                          muscle_group=_O(name=musculo) if musculo else None),
              muscle_group=None, series=series, repetitions=reps,
              break_time=descanso, intensity_type=tipo if inten else None,
              intensity_value=inten, notes=None, order_index=orden)


def _dia(nombre, weekday, ejercicios, descripcion=None):
    return _O(day_name=nombre, weekday=weekday, description=descripcion,
              details=[], blocks=[_O(exercises=ejercicios)])


def _rutina(**k):
    base = dict(name="Empuje A", training="Gimnasio", days=4, time=45,
                user=None, days_list=[])
    base.update(k)
    return _O(**base)


LUNES = _dia("Empuje", 0, [
    _ex("Press banca con barra", "Pecho", 4, "8-10", 120, 8, orden=0),
    _ex("Press militar mancuernas", "Hombro", 3, "10-12", 90, orden=1),
])


# ── Que salga ──────────────────────────────────────────────────────────────

def test_sale_un_pdf_de_verdad():
    pdf = generate_routine_pdf(_rutina(days_list=[LUNES]))
    assert pdf.startswith(b"%PDF"), pdf[:20]
    assert len(pdf) > 1500, len(pdf)


def test_la_cabecera_dice_lo_que_es():
    txt = _texto(generate_routine_pdf(_rutina(days_list=[LUNES])))
    assert "PLAN DE ENTRENAMIENTO" in txt, txt[:400]
    assert "Empuje A" in txt
    assert "Gimnasio" in txt
    # Los ejercicios se cuentan, no se copia el campo `days`.
    assert "2 ejercicios" in txt, txt[:600]
    for c in ("EJERCICIO", "SERIES", "REPS", "INTENSIDAD", "DESCANSO"):
        assert c in txt, f"falta la columna {c}"


# ── El reparto ─────────────────────────────────────────────────────────────

def test_EL_TITULO_DEL_DIA_ES_CUANDO_SE_ENTRENA():
    """El cliente necesita saber qué día le toca, no cómo se llama la sesión.
    El nombre sigue estando, debajo y en la etiqueta."""
    rut = _rutina(days_list=[
        _dia("Empuje", 0, [_ex("Press banca", "Pecho", 4, "8", 90)]),
        _dia("Pierna", 3, [_ex("Sentadilla", "Cuádriceps", 4, "8", 120)]),
    ])
    txt = _texto(generate_routine_pdf(rut))
    assert "Lunes" in txt and "Jueves" in txt, txt[:800]
    assert "Martes" not in txt, "ha repartido por orden en vez de por el dato"
    assert "Empuje" in txt and "Pierna" in txt, "se ha perdido el nombre de la sesión"


def test_sin_reparto_manda_el_orden_como_siempre():
    """Las rutinas de antes no tienen `weekday`. Nadie puede perder su reparto
    por desplegar esto."""
    rut = _rutina(days_list=[
        _dia("Empuje", None, [_ex("Press banca", "Pecho", 4, "8", 90)]),
        _dia("Tirón", None, [_ex("Remo", "Espalda", 4, "8", 90)]),
    ])
    txt = _texto(generate_routine_pdf(rut))
    assert "Lunes" in txt and "Martes" in txt, txt[:800]


# ── Lo que se imprime de cada ejercicio ────────────────────────────────────

def test_EL_DESCANSO_SE_LEE():
    """120 segundos son 2'. Un número suelto obliga a dividir en mitad de la
    serie, que es justo cuando no se puede."""
    txt = _texto(generate_routine_pdf(_rutina(days_list=[LUNES])))
    assert "2'" in txt, txt[:800]
    assert '90"' in txt


def test_LA_INTENSIDAD_SE_IMPRIME():
    """Estaba guardada y no salía: el RPE que el coach puso no llegaba a quien
    entrena."""
    txt = _texto(generate_routine_pdf(_rutina(days_list=[LUNES])))
    assert "RPE 8" in txt, txt[:800]


def test_el_porcentaje_se_marca_como_porcentaje():
    rut = _rutina(days_list=[_dia("Fuerza", 0, [
        _ex("Sentadilla", "Cuádriceps", 5, "3", 180, 80, tipo="pct1rm")])])
    txt = _texto(generate_routine_pdf(rut))
    assert "80%" in txt, txt[:800]


def test_el_grupo_muscular_acompaña_al_ejercicio():
    txt = _texto(generate_routine_pdf(_rutina(days_list=[LUNES])))
    assert "Pecho" in txt and "Hombro" in txt


def test_el_video_se_enlaza():
    rut = _rutina(days_list=[_dia("Empuje", 0, [
        _ex("Press banca", "Pecho", 4, "8", 90, video="https://youtu.be/abc")])])
    txt = _texto(generate_routine_pdf(rut))
    assert "Ver v" in txt, txt[:800]


# ── Lo que no puede tumbarlo ───────────────────────────────────────────────

def test_UN_DIA_DE_DESCANSO_LO_DICE():
    """En blanco parece que el PDF salió mal."""
    rut = _rutina(days_list=[LUNES, _dia("Libre", 2, [])])
    txt = _texto(generate_routine_pdf(rut))
    # Las tildes viajan como escapes octales dentro del PDF ("Mi\\351rcoles"),
    # asi que se busca el trozo sin tilde.
    assert "rcoles" in txt, txt[:900]
    assert "descanso" in txt.lower(), txt[:900]


def test_UN_NOMBRE_CON_SIGNOS_NO_DESAPARECE():
    """Reportlab lee `< >` como etiquetas suyas: sin escapar, el ejercicio no
    sale mal, DESAPARECE."""
    rut = _rutina(days_list=[_dia("Empuje", 0, [
        _ex("Press <cerrado> & fondos", "Tríceps", 3, "10", 60)])])
    txt = _texto(generate_routine_pdf(rut))
    assert "Press" in txt and "cerrado" in txt, "se ha perdido el ejercicio entero"


def test_una_rutina_sin_dias_no_revienta():
    pdf = generate_routine_pdf(_rutina(days_list=[]))
    assert pdf.startswith(b"%PDF")
    assert "no tiene d" in _texto(pdf)


def test_un_ejercicio_a_medias_no_para_el_pdf():
    rut = _rutina(days_list=[_dia("Empuje", 0, [
        _O(training=None, muscle_group=None, series=None, repetitions=None,
           break_time=None, intensity_type=None, intensity_value=None,
           notes=None, order_index=0),
        _ex("Press banca", None, 3, "10", None, orden=1),
    ])])
    pdf = generate_routine_pdf(rut)
    assert pdf.startswith(b"%PDF")
    assert "Press banca" in _texto(pdf)
