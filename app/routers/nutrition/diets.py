from fastapi import APIRouter, Depends
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.database import get_db
from sqlalchemy import or_
from app.core.dependencies import (
    require_role_ids, get_org_context, OrgContext,
    verify_client_access, SUPERADMIN, ADMIN, COACH,
)
from app.core.responses import send_response, send_error
from app.models.nutrition.diet import Diet, DietDetail, DietFood, DietFoodAliment, Pathology, diet_pathologies_table
from app.models.nutrition.aliment import Aliment
from app.schemas.nutrition.diet import DietCreate, DietUpdate, DietOut, DietFoodCreate, DietFoodAlimentCreate
from app.pdf.diet_pdf import generate_diet_pdf

router = APIRouter(prefix="/diets", tags=["Nutrition - Diets"])


def _get_or_404(db: Session, diet_id: str):
    return db.query(Diet).filter(Diet.id == diet_id).first()


def _serialize(diet: Diet) -> dict:
    return DietOut.model_validate(diet).model_dump()


def _clone_aliment(db: Session, source: Aliment) -> Aliment:
    clone = Aliment(
        group_food_id=source.group_food_id,
        brand=source.brand,
        name=source.name,
        quantity=source.quantity,
        quantity_type_id=source.quantity_type_id,
        proteins=source.proteins,
        carbohydrates=source.carbohydrates,
        fats=source.fats,
        calories=source.calories,
        comments=source.comments,
        parent_id=source.id,
        created_user_id=source.created_user_id,
    )
    db.add(clone)
    db.flush()
    return clone


def _save_pathologies(db: Session, diet_id: str, pathology_ids: list):
    db.execute(
        diet_pathologies_table.delete().where(diet_pathologies_table.c.diet_id == diet_id)
    )
    for pid in (pathology_ids or []):
        db.execute(diet_pathologies_table.insert().values(diet_id=diet_id, pathology_id=pid))


def _save_foods(db: Session, diet_id: str, foods_data: list, current_user_id: int):
    for food_data in foods_data:
        if food_data.delete and food_data.id:
            food = db.query(DietFood).filter(
                DietFood.id == food_data.id, DietFood.diet_id == diet_id
            ).first()
            if food:
                db.delete(food)
            continue

        if food_data.id:
            food = db.query(DietFood).filter(
                DietFood.id == food_data.id, DietFood.diet_id == diet_id
            ).first()
            if not food:
                continue
            food.name = food_data.name
        else:
            food = DietFood(diet_id=diet_id, name=food_data.name)
            db.add(food)
            db.flush()

        kept_ids = set()

        for aliment_data in (food_data.detail or []):
            if aliment_data.delete and aliment_data.id:
                dfa = db.query(DietFoodAliment).filter(
                    DietFoodAliment.id == aliment_data.id
                ).first()
                if dfa:
                    db.delete(dfa)
                continue

            source_aliment = db.query(Aliment).filter(
                Aliment.id == aliment_data.aliment_id
            ).first()
            if not source_aliment:
                continue

            if aliment_data.id:
                dfa = db.query(DietFoodAliment).filter(
                    DietFoodAliment.id == aliment_data.id
                ).first()
                if dfa:
                    dfa.quantity = aliment_data.quantity_calc
                    dfa.order = aliment_data.order or 0
                    kept_ids.add(dfa.id)
                    continue

            cloned = _clone_aliment(db, source_aliment)
            cloned.created_user_id = current_user_id

            dfa = DietFoodAliment(
                diet_id=diet_id,
                diet_food_id=food.id,
                aliment_id=cloned.id,
                quantity=aliment_data.quantity_calc,
                order=aliment_data.order or 0,
            )
            db.add(dfa)
            db.flush()
            kept_ids.add(dfa.id)


@router.get("/findAll", summary="Listar dietas", description="Retorna todas las dietas del coach autenticado.")
def find_all(
    db: Session = Depends(get_db),
    current_user=Depends(require_role_ids(SUPERADMIN, ADMIN, COACH)),
    org: OrgContext = Depends(get_org_context),
):
    q = db.query(Diet).filter(Diet.user_id == current_user.id)
    if org.org_id:
        q = q.filter(or_(Diet.organization_id.is_(None), Diet.organization_id == org.org_id))
    return send_response([_serialize(i) for i in q.all()], "OK")


@router.get("/client/{client_id}", summary="Dietas del cliente", description="Retorna las dietas de un cliente agrupadas por tipo de alimentación.")
def client_diets(client_id: str, db: Session = Depends(get_db), current_user=Depends(require_role_ids(SUPERADMIN, ADMIN, COACH))):
    verify_client_access(client_id, current_user, db)
    from app.models.user import UserDetail
    from app.models.nutrition.type_food import TypeFood

    client_detail = db.query(UserDetail).filter(UserDetail.id == client_id).first()
    if not client_detail:
        return send_error("Cliente no encontrado")

    diets = db.query(Diet).filter(Diet.user_id == client_detail.user_id).all()

    type_foods = db.query(TypeFood).all()
    grouped = []
    for tf in type_foods:
        matching = [_serialize(d) for d in diets if d.type_id == tf.id]
        if matching:
            grouped.append({"type": {"id": tf.id, "name": tf.name}, "diets": matching})

    untyped = [_serialize(d) for d in diets if d.type_id is None]
    if untyped:
        grouped.append({"type": None, "diets": untyped})

    return send_response(grouped, "OK")


@router.get("/{id}/pdf", summary="Exportar dieta a PDF", description="Genera y descarga la dieta en formato PDF.")
def pdf(id: str, db: Session = Depends(get_db), _=Depends(require_role_ids(SUPERADMIN, ADMIN, COACH))):
    diet = _get_or_404(db, id)
    if not diet:
        return send_error("Dieta no encontrada")
    try:
        pdf_bytes = generate_diet_pdf(diet)
    except Exception as e:
        return send_error(f"Error generando PDF: {str(e)}", code=500)
    safe_name = (diet.title or "dieta").replace(" ", "_").lower()
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{safe_name}.pdf"'},
    )


@router.post("/{client_id}/assigned", summary="Asignar dieta a cliente", description="Crea y asigna una dieta directamente a un cliente.")
def assigned(
    client_id: str,
    data: DietCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_role_ids(SUPERADMIN, ADMIN, COACH)),
):
    from app.models.user import UserDetail
    client_detail = db.query(UserDetail).filter(UserDetail.id == client_id).first()
    if not client_detail:
        return send_error("Cliente no encontrado")

    diet = Diet(
        title=data.title,
        calories=data.calories,
        quantity=data.quantity,
        type_id=data.type_id,
        notes=data.notes,
        user_id=client_detail.user_id,
        created_user_id=current_user.id,
    )
    db.add(diet)
    db.flush()

    _save_detail(db, diet.id, data)
    _save_foods(db, diet.id, data.foods or [], current_user.id)
    _save_pathologies(db, diet.id, data.pathology_ids or [])
    db.commit()
    db.refresh(diet)
    return send_response(_serialize(diet), "Dieta asignada")


@router.get("/{id}/edit", summary="Ver dieta", description="Retorna el detalle completo de una dieta con alimentos y macros.")
def edit(id: str, db: Session = Depends(get_db), _=Depends(require_role_ids(SUPERADMIN, ADMIN, COACH))):
    diet = _get_or_404(db, id)
    if not diet:
        return send_error("Dieta no encontrada")
    return send_response(_serialize(diet), "OK")


def _save_detail(db: Session, diet_id: str, data: DietCreate):
    detail = db.query(DietDetail).filter(DietDetail.diet_id == diet_id).first()
    detail_fields = {
        "height": data.height,
        "weight": data.weight,
        "body_fat": data.body_fat,
        "level_activity_id": data.level_activity_id,
        "objective_id": data.objective_id,
        "proteins": data.proteins,
        "carbs": data.carbs,
        "fats": data.fats,
        "deficit": data.deficit,
        "surplus": data.surplus,
    }
    if detail:
        for f, v in detail_fields.items():
            setattr(detail, f, v)
    else:
        db.add(DietDetail(diet_id=diet_id, **detail_fields))


@router.post("", summary="Crear dieta", description="Crea una nueva dieta con sus comidas, alimentos y distribución de macros.")
def create(
    data: DietCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_role_ids(SUPERADMIN, ADMIN, COACH)),
    org: OrgContext = Depends(get_org_context),
):
    diet = Diet(
        title=data.title,
        calories=data.calories,
        quantity=data.quantity,
        type_id=data.type_id,
        notes=data.notes,
        user_id=current_user.id,
        created_user_id=current_user.id,
        organization_id=org.org_id,
    )
    db.add(diet)
    db.flush()

    _save_detail(db, diet.id, data)
    _save_foods(db, diet.id, data.foods or [], current_user.id)
    _save_pathologies(db, diet.id, data.pathology_ids or [])
    db.commit()
    db.refresh(diet)
    return send_response(_serialize(diet), "Dieta creada")


@router.put("/{id}/update", summary="Actualizar dieta", description="Modifica una dieta existente, incluyendo sus comidas y alimentos.")
def updated(id: str, data: DietUpdate, db: Session = Depends(get_db), current_user=Depends(require_role_ids(SUPERADMIN, ADMIN, COACH))):
    diet = _get_or_404(db, id)
    if not diet:
        return send_error("Dieta no encontrada")

    if data.title is not None:
        diet.title = data.title
    if data.calories is not None:
        diet.calories = data.calories
    if data.quantity is not None:
        diet.quantity = data.quantity
    if data.type_id is not None:
        diet.type_id = data.type_id
    if data.notes is not None:
        diet.notes = data.notes
    diet.updated_user_id = current_user.id

    _save_detail(db, diet.id, data)
    _save_foods(db, diet.id, data.foods or [], current_user.id)
    _save_pathologies(db, diet.id, data.pathology_ids or [])
    db.commit()
    db.refresh(diet)
    return send_response(_serialize(diet), "Dieta actualizada")


@router.delete("/{id}", summary="Eliminar dieta", description="Elimina una dieta y todas sus comidas y alimentos asociados.")
def delete(id: str, db: Session = Depends(get_db), _=Depends(require_role_ids(SUPERADMIN, ADMIN, COACH))):
    diet = _get_or_404(db, id)
    if not diet:
        return send_error("Dieta no encontrada")
    db.delete(diet)
    db.commit()
    return send_response(None, "Dieta eliminada")


class _AssignBody(DietCreate):
    client_id: str
    title: str = ""


@router.post("/{id}/assign", summary="Asignar dieta existente a cliente", description="Copia una dieta del catálogo del coach al cliente especificado.")
def assign_to_client(
    id: str,
    body: _AssignBody,
    db: Session = Depends(get_db),
    current_user=Depends(require_role_ids(SUPERADMIN, ADMIN, COACH)),
):
    from app.models.user import UserDetail
    source = _get_or_404(db, id)
    if not source:
        return send_error("Dieta no encontrada")
    client_detail = db.query(UserDetail).filter(UserDetail.id == body.client_id).first()
    if not client_detail:
        return send_error("Cliente no encontrado")

    new_diet = Diet(
        title=source.title,
        calories=source.calories,
        quantity=source.quantity,
        type_id=source.type_id,
        user_id=client_detail.user_id,
        created_user_id=current_user.id,
    )
    db.add(new_diet)
    db.flush()

    if source.detail:
        d = source.detail
        db.add(DietDetail(
            diet_id=new_diet.id,
            proteins=d.proteins, carbs=d.carbs, fats=d.fats,
            deficit=d.deficit, surplus=d.surplus,
            height=d.height, weight=d.weight, body_fat=d.body_fat,
            level_activity_id=d.level_activity_id, objective_id=d.objective_id,
        ))

    foods_data = [
        DietFoodCreate(
            name=food.name,
            detail=[
                DietFoodAlimentCreate(
                    aliment_id=dfa.aliment_id,
                    quantity_calc=dfa.quantity,
                    order=dfa.order,
                )
                for dfa in food.detail
            ],
        )
        for food in source.foods
    ]
    _save_foods(db, new_diet.id, foods_data, current_user.id)
    db.commit()
    db.refresh(new_diet)
    return send_response(_serialize(new_diet), "Dieta asignada al cliente")
