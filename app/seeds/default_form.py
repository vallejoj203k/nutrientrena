import json
from sqlalchemy.orm import Session
from app.models.form import FormTemplate, FormTemplateField


# ── Complete default field list (Section 4 of MVP requirements) ───────────────
DEFAULT_FIELDS = [
    # ── Datos corporales ──────────────────────────────────────────────────────
    {
        "label": "Peso actual (kg)",
        "field_key": "weight",
        "field_type": "number",
        "placeholder": "Ej: 72.5",
        "order": 1,
        "required": True,
    },
    {
        "label": "Altura (cm)",
        "field_key": "height",
        "field_type": "number",
        "placeholder": "Ej: 175",
        "order": 2,
        "required": True,
    },
    {
        "label": "Género",
        "field_key": "gender_id",
        "field_type": "number",
        "placeholder": "ID del parámetro de género",
        "order": 3,
        "required": False,
    },
    # ── Datos personales ──────────────────────────────────────────────────────
    {
        "label": "Teléfono / WhatsApp",
        "field_key": "phone",
        "field_type": "text",
        "placeholder": "+34 600 000 000",
        "order": 4,
        "required": False,
    },
    {
        "label": "País",
        "field_key": "country_code",
        "field_type": "text",
        "placeholder": "Ej: ES, MX, CO…",
        "order": 5,
        "required": False,
    },
    {
        "label": "Ocupación",
        "field_key": "occupation",
        "field_type": "text",
        "placeholder": "¿A qué te dedicas?",
        "order": 6,
        "required": False,
    },
    # ── Objetivo y actividad ──────────────────────────────────────────────────
    {
        "label": "Objetivo principal",
        "field_key": "objective_id",
        "field_type": "number",
        "placeholder": "ID del parámetro de objetivo",
        "order": 7,
        "required": False,
    },
    {
        "label": "Nivel de actividad física",
        "field_key": "activity_id",
        "field_type": "number",
        "placeholder": "ID del parámetro de actividad",
        "order": 8,
        "required": False,
    },
    {
        "label": "Días disponibles para entrenar (por semana)",
        "field_key": "training_days",
        "field_type": "number",
        "placeholder": "Ej: 4",
        "order": 9,
        "required": False,
    },
    {
        "label": "Equipamiento disponible",
        "field_key": "equipment",
        "field_type": "select",
        "options": json.dumps([
            "Sin equipamiento (solo peso corporal)",
            "Mancuernas / pesas en casa",
            "Gimnasio completo",
            "Bandas elásticas",
            "Otro",
        ]),
        "order": 10,
        "required": False,
    },
    # ── Historial médico ──────────────────────────────────────────────────────
    {
        "label": "Patologías o condiciones médicas",
        "field_key": "pathologies",
        "field_type": "textarea",
        "placeholder": "Diabetes, hipertensión, hipotiroidismo… (escribe 'ninguna' si no tienes)",
        "order": 11,
        "required": False,
    },
    {
        "label": "Lesiones o restricciones físicas",
        "field_key": "injuries",
        "field_type": "textarea",
        "placeholder": "Describe cualquier lesión o zona a evitar",
        "order": 12,
        "required": False,
    },
    {
        "label": "Alergias e intolerancias alimentarias",
        "field_key": "food_allergies",
        "field_type": "textarea",
        "placeholder": "Gluten, lactosa, frutos secos… (escribe 'ninguna' si no tienes)",
        "order": 13,
        "required": False,
    },
    # ── Hábitos ───────────────────────────────────────────────────────────────
    {
        "label": "Hábitos alimentarios actuales",
        "field_key": "eating_habits",
        "field_type": "textarea",
        "placeholder": "Describe brevemente cómo comes actualmente (comidas al día, alimentos frecuentes…)",
        "order": 14,
        "required": False,
    },
    {
        "label": "Horas de sueño diarias (aprox.)",
        "field_key": "sleep_hours",
        "field_type": "number",
        "placeholder": "Ej: 7",
        "order": 15,
        "required": False,
    },
    {
        "label": "Nivel de estrés",
        "field_key": "stress_level",
        "field_type": "select",
        "options": json.dumps(["Bajo", "Medio", "Alto", "Muy alto"]),
        "order": 16,
        "required": False,
    },
    # ── Motivación ────────────────────────────────────────────────────────────
    {
        "label": "Experiencia previa con entrenamiento / nutrición",
        "field_key": "experience",
        "field_type": "textarea",
        "placeholder": "¿Has seguido algún plan antes? ¿Cuánto tiempo?",
        "order": 17,
        "required": False,
    },
    {
        "label": "Motivación y expectativas",
        "field_key": "motivation",
        "field_type": "textarea",
        "placeholder": "¿Por qué te apuntas ahora? ¿Qué esperas conseguir?",
        "order": 18,
        "required": False,
    },
]


def seed_default_form(db: Session):
    """Create the default intake form template if it does not exist yet."""
    from app.models.user import User

    admin = db.query(User).first()
    if not admin:
        return

    existing = db.query(FormTemplate).filter(FormTemplate.is_default.is_(True)).first()
    if existing:
        return

    _create_template(db, admin.id)
    print("Default form template created.")


def update_default_form(db: Session):
    """
    Idempotent update: ensure the default template contains all current
    DEFAULT_FIELDS.  Missing fields are appended; existing ones are left
    untouched so coach edits are preserved.
    Run once after deploying this update.
    """
    template = db.query(FormTemplate).filter(FormTemplate.is_default.is_(True)).first()
    if not template:
        from app.models.user import User

        admin = db.query(User).first()
        if admin:
            _create_template(db, admin.id)
            print("Default form template created (via update).")
        return

    existing_keys = {f.field_key for f in template.fields}
    added = 0
    for field_data in DEFAULT_FIELDS:
        if field_data["field_key"] not in existing_keys:
            db.add(FormTemplateField(
                form_template_id=template.id,
                label=field_data["label"],
                field_key=field_data["field_key"],
                field_type=field_data["field_type"],
                placeholder=field_data.get("placeholder"),
                options=field_data.get("options"),
                order=field_data["order"],
                required=field_data.get("required", False),
            ))
            added += 1

    if added:
        db.commit()
        print(f"Default form updated: {added} new field(s) added.")
    else:
        print("Default form is already up to date.")


# ── Internal helper ───────────────────────────────────────────────────────────

def _create_template(db: Session, creator_id: int):
    template = FormTemplate(
        title="Formulario de Bienvenida",
        description="Formulario inicial para nuevos clientes",
        created_by=creator_id,
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
            placeholder=field_data.get("placeholder"),
            options=field_data.get("options"),
            order=field_data["order"],
            required=field_data.get("required", False),
        ))

    db.commit()
