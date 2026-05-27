from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime, date


class UserCreateRequest(BaseModel):
    name: str
    last_name: Optional[str] = None
    email: EmailStr
    password: str
    phone: Optional[str] = None
    height: Optional[float] = None
    weight: Optional[float] = None
    occupation: Optional[str] = None
    country_code: Optional[str] = None
    gender_id: Optional[int] = None
    activity_id: Optional[int] = None
    status_id: Optional[int] = None
    objective_id: Optional[int] = None
    defecit: Optional[float] = None
    excedente: Optional[float] = None
    role_id: int
    instructor: Optional[str] = None  # UserDetail UUID of instructor

    # Business / CRM fields
    plan_comprado: Optional[str] = None
    precio: Optional[float] = None
    estado_pago: Optional[str] = None
    importe_pagado: Optional[float] = None
    importe_pendiente: Optional[float] = None
    metodo_pago: Optional[str] = None
    fecha_compra: Optional[date] = None
    fecha_limite_entrega: Optional[date] = None
    responsable_venta: Optional[str] = None
    crm_origen: Optional[str] = None
    whatsapp_link: Optional[str] = None
    consentimiento_evolucion: Optional[bool] = None


class UserUpdateRequest(BaseModel):
    name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[EmailStr] = None
    password: Optional[str] = None
    phone: Optional[str] = None
    height: Optional[float] = None
    weight: Optional[float] = None
    occupation: Optional[str] = None
    country_code: Optional[str] = None
    gender_id: Optional[int] = None
    activity_id: Optional[int] = None
    status_id: Optional[int] = None
    objective_id: Optional[int] = None
    defecit: Optional[float] = None
    excedente: Optional[float] = None
    role_id: Optional[int] = None

    # Business / CRM fields
    plan_comprado: Optional[str] = None
    precio: Optional[float] = None
    estado_pago: Optional[str] = None
    importe_pagado: Optional[float] = None
    importe_pendiente: Optional[float] = None
    metodo_pago: Optional[str] = None
    fecha_compra: Optional[date] = None
    fecha_limite_entrega: Optional[date] = None
    responsable_venta: Optional[str] = None
    crm_origen: Optional[str] = None
    whatsapp_link: Optional[str] = None
    consentimiento_evolucion: Optional[bool] = None


class UserStateRequest(BaseModel):
    status_id: int


class UserAssignRequest(BaseModel):
    user_id: str          # UserDetail UUID of client
    user_parent_id: str   # UserDetail UUID of instructor


class WeeksTrainingRequest(BaseModel):
    client_id: str   # UserDetail UUID
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None


class ParameterDetailOut(BaseModel):
    id: int
    description: str
    model_config = {"from_attributes": True}


class CountryOut(BaseModel):
    code: str
    country: str
    model_config = {"from_attributes": True}


class RoleOut(BaseModel):
    id: int
    name: str
    model_config = {"from_attributes": True}


class UserDetailOut(BaseModel):
    id: str
    user_id: int
    name: str
    last_name: Optional[str] = None
    phone: Optional[str] = None
    height: Optional[float] = None
    weight: Optional[float] = None
    occupation: Optional[str] = None
    country_code: Optional[str] = None
    gender_id: Optional[int] = None
    activity_id: Optional[int] = None
    status_id: Optional[int] = None
    objective_id: Optional[int] = None
    defecit: Optional[float] = None
    excedente: Optional[float] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    created_at: Optional[datetime] = None

    # Business / CRM fields
    plan_comprado: Optional[str] = None
    precio: Optional[float] = None
    estado_pago: Optional[str] = None
    importe_pagado: Optional[float] = None
    importe_pendiente: Optional[float] = None
    metodo_pago: Optional[str] = None
    fecha_compra: Optional[date] = None
    fecha_limite_entrega: Optional[date] = None
    responsable_venta: Optional[str] = None
    crm_origen: Optional[str] = None
    whatsapp_link: Optional[str] = None
    consentimiento_evolucion: Optional[bool] = None

    status: Optional[ParameterDetailOut] = None
    gender: Optional[ParameterDetailOut] = None
    activity: Optional[ParameterDetailOut] = None
    objective: Optional[ParameterDetailOut] = None
    country: Optional[CountryOut] = None

    model_config = {"from_attributes": True}
