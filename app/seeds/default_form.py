from sqlalchemy.orm import Session
from app.models.form import FormTemplate, FormTemplateField


DEFAULT_FIELDS = [
    {"label": "Peso actual (kg)",           "field_key": "weight",       "field_type": "number", "order": 1},
    {"label": "Altura (cm)",                "field_key": "height",       "field_type": "number", "order": 2},
    {"label": "Telefono",                   "field_key": "phone",        "field_type": "text",   "order": 3},
    {"label": "Ocupacion",                  "field_key": "occupation",   "field_type": "text",   "order": 4},
    {"label": "ID Genero",                  "field_key": "gender_id",    "field_type": "number", "order": 5},
    {"label": "ID Objetivo",                "field_key": "objective_id", "field_type": "number", "order": 6},
    {"label": "ID Nivel de actividad",      "field_key": "activity_id",  "field_type": "number", "order": 7},
    {"label": "Lesiones o restricciones",   "field_key": "injuries",     "field_type": "textarea","order": 8},
    {"label": "Experiencia previa",         "field_key": "experience",   "field_type": "textarea","order": 9},
    {"label": "Motivacion",                 "field_key": "motivation",   "field_type": "textarea","order": 10},
]


def seed_default_form(db: Session):
    from app.models.user import User
    admin = db.query(User).first()
    if not admin:
        return

    existing = db.query(FormTemplate).filter(FormTemplate.is_default.is_(True)).first()
    if existing:
        return

    template = FormTemplate(
        title="Formulario de Bienvenida",
        description="Formulario inicial para nuevos clientes",
        created_by=admin.id,
        is_default=True,
    )
    db.add(template)
    db.flush()

    for field_data in DEFAULT_FIELDS:
        db.add(FormTemplateField(
            form_template_id=template.id,
            label=field_data["label"],
            field_key=field_data["field_key"],
            field_type=field_data["field_type"],
            order=field_data["order"],
            required=field_data.get("required", True),
        ))

    db.commit()
    print("Default form template created.")
