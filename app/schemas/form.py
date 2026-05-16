from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class FormFieldCreate(BaseModel):
    label: str
    field_type: str = "text"
    field_key: str
    placeholder: Optional[str] = None
    options: Optional[str] = None
    order: int = 0
    required: bool = True


class FormFieldOut(BaseModel):
    id: int
    label: str
    field_type: str
    field_key: str
    placeholder: Optional[str] = None
    options: Optional[str] = None
    order: int
    required: bool

    model_config = {"from_attributes": True}


class FormTemplateCreate(BaseModel):
    title: str
    description: Optional[str] = None
    is_default: bool = False
    fields: List[FormFieldCreate] = []


class FormTemplateUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    is_default: Optional[bool] = None
    fields: Optional[List[FormFieldCreate]] = None


class FormTemplateOut(BaseModel):
    id: int
    title: str
    description: Optional[str] = None
    is_default: bool
    created_at: Optional[datetime] = None
    fields: List[FormFieldOut] = []

    model_config = {"from_attributes": True}


class FormAssignRequest(BaseModel):
    form_template_id: int
    client_user_detail_id: str


class FormResponseItem(BaseModel):
    field_key: str
    value: Optional[str] = None


class FormSubmitRequest(BaseModel):
    responses: List[FormResponseItem]


class FormResponseOut(BaseModel):
    field_key: str
    value: Optional[str] = None

    model_config = {"from_attributes": True}


class FormAssignmentOut(BaseModel):
    id: str
    form_template_id: int
    client_user_detail_id: str
    status: str
    submitted_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    template: Optional[FormTemplateOut] = None
    responses: List[FormResponseOut] = []

    model_config = {"from_attributes": True}
