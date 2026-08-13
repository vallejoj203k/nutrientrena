"""Configuración de la plataforma.

Dos endpoints y una regla: un ajuste que no hace nada no se pone.

- `/admin/settings` lo lee y lo escribe el super-admin.
- `/platform/settings` lo lee CUALQUIER usuario con sesión, y devuelve solo lo
  que la aplicación necesita saber para comportarse: el nombre, el correo de
  soporte y si hay mantenimiento. Sin este segundo endpoint, el correo de
  soporte sería un campo bonito que nadie ve nunca.
"""
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user
from app.core.responses import send_error, send_response
from app.database import get_db
from app.models.platform_setting import PlatformSetting

router = APIRouter(prefix="/platform", tags=["Configuración de plataforma"])
router_admin = APIRouter(prefix="/admin", tags=["Configuración de plataforma"])

MONEDAS = ["EUR", "USD", "GBP", "MXN", "COP", "ARS", "CLP", "PEN"]


def obtener(db: Session) -> PlatformSetting:
    s = db.query(PlatformSetting).filter(PlatformSetting.id == 1).first()
    if not s:
        s = PlatformSetting(id=1)
        db.add(s)
        db.commit()
        db.refresh(s)
    return s


def _out(s: PlatformSetting) -> dict:
    return {
        "platform_name": s.platform_name or "Alzum.io",
        "support_email": s.support_email,
        "default_currency": s.default_currency or "EUR",
        "trial_days": s.trial_days if s.trial_days is not None else 14,
        "open_registration": bool(s.open_registration),
        "maintenance_mode": bool(s.maintenance_mode),
        "updated_at": s.updated_at.isoformat() if s.updated_at else None,
        "monedas": MONEDAS,
        # El interruptor de registro abierto se guarda, pero hoy no hay página
        # pública de alta: los entrenadores se meten a mano desde el panel. Se
        # dice aquí para que la pantalla lo advierta en vez de dar a entender
        # que ya está gobernando algo.
        "registro_publico_existe": False,
    }


class AjustesPlataforma(BaseModel):
    platform_name: Optional[str] = None
    support_email: Optional[str] = None
    default_currency: Optional[str] = None
    trial_days: Optional[int] = None
    open_registration: Optional[bool] = None
    maintenance_mode: Optional[bool] = None


@router_admin.get("/settings", summary="Ajustes de la plataforma")
def ver_ajustes(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    from app.routers.admin_panel import _exige_seccion
    motivo = _exige_seccion(current_user, db, "configuracion")
    if motivo:
        return send_error(motivo, code=403)
    return send_response(_out(obtener(db)), "OK")


@router_admin.put("/settings", summary="Guardar los ajustes de la plataforma")
def guardar_ajustes(
    data: AjustesPlataforma,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    from app.routers.admin_panel import _exige_seccion
    motivo = _exige_seccion(current_user, db, "configuracion")
    if motivo:
        return send_error(motivo, code=403)

    s = obtener(db)
    cambios = data.model_dump(exclude_unset=True)

    if "platform_name" in cambios:
        nombre = (cambios["platform_name"] or "").strip()
        if not nombre:
            return send_error("La plataforma necesita un nombre", code=400)
        s.platform_name = nombre[:120]

    if "support_email" in cambios:
        correo = (cambios["support_email"] or "").strip()
        # No se valida con una expresión regular exhaustiva —siempre se queda
        # corta— pero sí lo mínimo: si esto está mal, el coach escribe a un
        # buzón que no existe y nadie se entera.
        if correo and ("@" not in correo or "." not in correo.split("@")[-1]):
            return send_error("Ese correo de soporte no parece válido", code=400)
        s.support_email = correo or None

    if "default_currency" in cambios:
        moneda = (cambios["default_currency"] or "").upper()
        if moneda not in MONEDAS:
            return send_error(f"Moneda no admitida. Admitidas: {', '.join(MONEDAS)}", code=400)
        s.default_currency = moneda

    if "trial_days" in cambios:
        dias = cambios["trial_days"]
        if dias is None or dias < 0 or dias > 365:
            return send_error("Los días de prueba tienen que estar entre 0 y 365", code=400)
        s.trial_days = int(dias)

    if "open_registration" in cambios:
        s.open_registration = bool(cambios["open_registration"])
    if "maintenance_mode" in cambios:
        s.maintenance_mode = bool(cambios["maintenance_mode"])

    s.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(s)
    _invalidar_cache()
    return send_response(_out(s), "Ajustes guardados")


@router.get("/settings", summary="Lo que la aplicación necesita saber de la plataforma",
            description="Nombre, correo de soporte y si hay mantenimiento. Para cualquier usuario con sesión.")
def ajustes_publicos(
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
):
    s = obtener(db)
    return send_response({
        "platform_name": s.platform_name or "Alzum.io",
        "support_email": s.support_email,
        "default_currency": s.default_currency or "EUR",
        "maintenance_mode": bool(s.maintenance_mode),
    }, "OK")


# ── Modo mantenimiento ──────────────────────────────────────────────────────
#
# Se consulta en CADA petición que escribe, así que se guarda en memoria unos
# segundos. Sin esa caché, encender el mantenimiento añadiría una consulta a la
# base de datos por cada guardado de la aplicación entera.
_cache = {"valor": None, "hasta": 0.0}
_TTL = 15.0


def _invalidar_cache():
    _cache["valor"] = None
    _cache["hasta"] = 0.0


def hay_mantenimiento(db: Session) -> bool:
    import time
    ahora = time.monotonic()
    if _cache["valor"] is not None and ahora < _cache["hasta"]:
        return _cache["valor"]
    try:
        fila = db.query(PlatformSetting).filter(PlatformSetting.id == 1).first()
        valor = bool(fila.maintenance_mode) if fila else False
    except Exception:
        # Si la tabla todavía no existe (base sin migrar), no hay
        # mantenimiento. Nunca al revés: un fallo al leer el ajuste no puede
        # dejar la aplicación entera en solo lectura.
        valor = False
    _cache["valor"] = valor
    _cache["hasta"] = ahora + _TTL
    return valor
