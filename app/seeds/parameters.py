from sqlalchemy.orm import Session
from app.models.parameter import Parameter, ParameterDetail


PARAMETERS = [
    {
        "description": "Estado del Cliente",
        "details": [
            {"description": "Pago pendiente"},
            {"description": "Reserva recibida"},
            {"description": "Pago recibido"},
            {"description": "Formulario pendiente"},
            {"description": "Formulario recibido"},
            {"description": "Cliente contactado"},
            {"description": "Videollamada pendiente"},
            {"description": "Videollamada realizada"},
            {"description": "Plan en creacion"},
            {"description": "Plan entregado"},
            {"description": "En seguimiento"},
            {"description": "Cliente en riesgo"},
            {"description": "Finalizado"},
            {"description": "Renovado"},
            {"description": "Cancelado / Reembolsado"},
        ],
    },
    {
        "description": "Estado de Cuenta",
        "details": [
            {"description": "Activo"},
            {"description": "Inactivo"},
        ],
    },
    {
        "description": "Genero",
        "details": [
            {"description": "Masculino"},
            {"description": "Femenino"},
            {"description": "Otro"},
        ],
    },
    {
        "description": "Actividad Fisica",
        "details": [
            {"description": "Sedentario"},
            {"description": "Moderadamente activo"},
            {"description": "Activo"},
            {"description": "Muy activo"},
        ],
    },
    {
        "description": "Nivel de entrenamiento",
        "details": [
            {"description": "Principiante"},
            {"description": "Intermedio"},
            {"description": "Avanzado"},
        ],
    },
    {
        "description": "Cantidad",
        "details": [
            {"description": "gr"},
            {"description": "ml"},
            {"description": "oz"},
            {"description": "ud"},
        ],
    },
    {
        "description": "Nivel de actividad",
        "details": [
            {"description": "Sedentario",    "value_1": "1.2",   "value_1_description": "VALOR"},
            {"description": "Ligera",         "value_1": "1.375", "value_1_description": "VALOR"},
            {"description": "Moderada",       "value_1": "1.55",  "value_1_description": "VALOR"},
            {"description": "Intensa",        "value_1": "1.65",  "value_1_description": "VALOR"},
            {"description": "Muy Activa",     "value_1": "1.725", "value_1_description": "VALOR"},
            {"description": "Extra Fuerte",   "value_1": "1.9",   "value_1_description": "VALOR"},
        ],
    },
    {
        "description": "Objetivo",
        "details": [
            {"description": "Mantenimiento"},
            {"description": "Perder Grasa"},
            {"description": "Ganar Musculatura"},
        ],
    },
    {
        "description": "Categoria de Comida",
        "details": [
            {"description": "Mediterranea"},
            {"description": "Keto"},
            {"description": "Low carb"},
            {"description": "Vegetariana"},
            {"description": "Vegana"},
            {"description": "Ovolactovegetariana"},
            {"description": "Lactovegetariana"},
            {"description": "Ayuno Intermitente"},
            {"description": "Fodmap"},
        ],
    },
    {
        "description": "Tipo de Comida",
        "details": [
            {"description": "Desayuno"},
            {"description": "Almuerzo"},
            {"description": "Cena"},
            {"description": "Merienda"},
        ],
    },
    {
        "description": "Objetivo Usuario",
        "details": [
            {"description": "Perder Grasa"},
            {"description": "Aumentar masa muscular"},
            {"description": "Mejorar rendimiento deportivo"},
            {"description": "Tonificar"},
            {"description": "Mejorar habitos"},
            {"description": "Adelgazar"},
        ],
    },
]


def seed_parameters(db: Session):
    if db.query(Parameter).count() > 0:
        return
    for param_data in PARAMETERS:
        param = Parameter(description=param_data["description"])
        db.add(param)
        db.flush()
        for detail_data in param_data["details"]:
            db.add(ParameterDetail(parameter_id=param.id, **detail_data))
    db.commit()
