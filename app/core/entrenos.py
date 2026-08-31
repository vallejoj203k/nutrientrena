"""Las cuentas del historial de entrenos.

Aquí vive lo que la pantalla de Sesiones necesita saber y no está guardado tal
cual: el tonelaje, el estado de cada sesión y qué se programó frente a qué se
hizo. Se calcula en un solo sitio porque son cuentas con filo — cada una tiene
una forma obvia de hacerse mal.

Lo que se decidió con el cliente:

  · Lo PROGRAMADO sale de su calendario (tareas de tipo `rutina`). Es lo que el
    coach planificó de verdad; deducirlo de "días por semana × semanas" sería
    una estimación que no sabe de vacaciones ni de cambios de plan.
  · Una sesión SALTADA no existe en la base: es un día programado sin sesión
    registrada. Se construye al leer, no se guarda.
"""
import re
from datetime import date, timedelta

# Una serie de 40 segundos no son 40 repeticiones. Si se colara, el tonelaje de
# una plancha de 40s con 20 kg saldría como 800 kg de una sentada.
_TIEMPO = re.compile(r"\d\s*(s|seg|segs|segundos|min|m|'|\")\b", re.I)
_PRIMER_NUMERO = re.compile(r"\d+(?:[.,]\d+)?")


def repeticiones(texto):
    """Las repeticiones de una serie, del texto que escribió el cliente.

    Admite "8", "8-10", "10 reps". De un rango se coge el PRIMERO: es lo que
    de verdad marcó como hecho, y quedarse con el mayor infla el tonelaje.
    Devuelve None cuando no son repeticiones (una serie por tiempo).
    """
    t = str(texto or "").strip()
    if not t or _TIEMPO.search(t):
        return None
    m = _PRIMER_NUMERO.search(t)
    if not m:
        return None
    try:
        return float(m.group(0).replace(",", "."))
    except ValueError:
        return None


def tonelaje(sesion):
    """Kilos levantados: peso × repeticiones, sumando SOLO las series hechas.

    Contar las no marcadas diría que el cliente levantó lo que dejó a medias, y
    justo en las sesiones parciales —donde más importa— sería lo más falso.
    """
    total = 0.0
    for ex in (sesion.exercises or []):
        for st in (ex.sets or []):
            if not st.done or st.weight is None:
                continue
            reps = repeticiones(st.reps)
            if reps:
                total += float(st.weight) * reps
    return round(total, 1)


def series(sesion):
    """(hechas, registradas) de una sesión."""
    todas = [st for ex in (sesion.exercises or []) for st in (ex.sets or [])]
    return sum(1 for st in todas if st.done), len(todas)


def estado(hechas, previstas):
    """Completada, parcial o saltada.

    `previstas` es lo que el coach dejó puesto en la rutina de ese día; cuando
    no se sabe, se usan las registradas, y entonces "completada" significa que
    marcó todo lo que apuntó.
    """
    if not previstas:
        return "completada" if hechas else "saltada"
    if hechas <= 0:
        return "saltada"
    return "completada" if hechas >= previstas else "parcial"


def semana_del_programa(dia, inicio):
    """En qué semana del programa cae esa fecha. La primera es la 1."""
    if not dia or not inicio:
        return None
    dias = (dia - inicio).days
    if dias < 0:
        return None
    return dias // 7 + 1


def racha_semanas(fechas, hoy=None):
    """Semanas seguidas, hasta hoy, con al menos un entreno.

    Se cuenta hacia atrás desde la semana en curso. La semana actual no rompe
    la racha si aún no se ha entrenado: es miércoles, quedan días.
    """
    if not fechas:
        return 0
    hoy = hoy or date.today()
    lunes_actual = hoy - timedelta(days=hoy.weekday())
    con_entreno = {f - timedelta(days=f.weekday()) for f in fechas if f}

    racha = 0
    semana = lunes_actual
    if semana not in con_entreno:
        semana -= timedelta(days=7)      # la semana en curso aún puede llenarse
    while semana in con_entreno:
        racha += 1
        semana -= timedelta(days=7)
    return racha
