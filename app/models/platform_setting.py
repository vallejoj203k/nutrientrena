"""Ajustes de la PLATAFORMA (Alzum), no de un centro.

Ya existía `app_settings`, pero es otra cosa: son los datos del negocio del
coach —su nombre comercial, su teléfono, su moneda— y los edita él desde su
propio panel. Meter aquí los ajustes de Alzum habría mezclado dos niveles de
la jerarquía en la misma fila, que es justo lo que llevamos toda la fase
separando.

Una sola fila, id=1. No es una tabla de clave/valor a propósito: con columnas
tipadas, un ajuste nuevo obliga a pasar por una migración y a decidir su tipo
y su valor por defecto, en vez de aparecer como una cadena suelta que nadie
sabe interpretar.
"""
from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Integer, String

from app.database import Base


class PlatformSetting(Base):
    __tablename__ = "platform_settings"

    id = Column(Integer, primary_key=True, default=1)
    platform_name = Column(String(120), nullable=False, default="Alzum.io",
                           server_default="Alzum.io")
    support_email = Column(String(255), nullable=True)
    default_currency = Column(String(10), nullable=False, default="EUR",
                              server_default="EUR")
    trial_days = Column(Integer, nullable=False, default=14, server_default="14")
    # Que un desconocido pueda crearse una cuenta desde la web. Hoy no existe
    # esa página; el ajuste se guarda apagado y la pantalla lo dice.
    open_registration = Column(Boolean, nullable=False, default=False,
                               server_default="0")
    # Con esto puesto, nadie que no sea del equipo de Alzum puede escribir:
    # las peticiones que modifican datos responden 503 y el coach ve un aviso.
    maintenance_mode = Column(Boolean, nullable=False, default=False,
                              server_default="0")
    updated_at = Column(DateTime, nullable=True, onupdate=datetime.utcnow)
