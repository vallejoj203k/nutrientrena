"""Lo que comparten los PDF de la dieta y de la rutina.

Son dos documentos distintos con la misma cabecera: el nombre del cliente, su
coach y el sello de la plataforma. Escribirlo dos veces habría dejado dos
cabeceras que se parecen hasta que alguien toca una.
"""


def txt(v) -> str:
    """Texto para reportlab, que interpreta `< >` como etiquetas suyas.

    Sin esto, un ejercicio llamado "Press <banca>" no sale mal: DESAPARECE, y
    el documento se entrega con una línea menos sin que nada avise.
    """
    return (str(v or "")
            .replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def num(v) -> str:
    """80.0 se escribe 80, y 0.5 se queda en 0.5."""
    try:
        f = float(v)
    except (TypeError, ValueError):
        return "—"
    return str(int(f)) if f == int(f) else str(round(f, 2))


def descanso(seg) -> str:
    """120 segundos son 2'; el minuto justo se queda en 60".

    Por encima de dos minutos, los segundos obligan a dividir mentalmente en
    mitad de la serie. Es la misma regla que la pantalla, para que el papel y
    la app no digan el mismo descanso de dos formas.
    """
    try:
        n = int(seg)
    except (TypeError, ValueError):
        return "—"
    if n <= 0:
        return "—"
    if n >= 120 and n % 60 == 0:
        return f"{n // 60}'"
    return f'{n}"'


def quien_de(obj):
    """El cliente de un plan y su coach, para la cabecera.

    Va aquí y no en el router porque los PDF se generan desde varios sitios; si
    cada uno tuviera que pasarlos, el que se olvidara sacaría un plan sin
    nombre y nadie lo notaría hasta tenerlo impreso.

    Si algo falla se devuelven vacíos: un PDF sin nombre es peor que uno con
    nombre, pero un PDF que no se genera es todavía peor.
    """
    cliente = coach = ""
    try:
        u = getattr(obj, "user", None)
        if u is not None:
            cliente = (getattr(u, "name", "") or "").strip()
        from sqlalchemy.orm import object_session
        ses = object_session(obj)
        if ses is not None and u is not None:
            from app.models.user import UserDetail, UserParent
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
