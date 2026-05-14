from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.core.dependencies import get_current_user
from app.core.responses import send_response, send_error
from app.models.nutrition.diet import Diet, DietDetail
from app.schemas.nutrition.diet import DietCreate, DietUpdate, DietOut, DietAssignRequest

router = APIRouter(prefix="/diets", tags=["Nutrition - Diets"])


def _get_or_404(db: Session, diet_id: int):
    return db.query(Diet).filter(Diet.id == diet_id).first()


@router.get("/findAll")
def find_all(db: Session = Depends(get_db), _=Depends(get_current_user)):
    items = db.query(Diet).filter(Diet.state == 1).all()
    return send_response([DietOut.model_validate(i).model_dump() for i in items], "OK")


@router.get("/client/{client_id}")
def client_diets(client_id: int, db: Session = Depends(get_db), _=Depends(get_current_user)):
    items = db.query(Diet).filter(Diet.client_id == client_id, Diet.state == 1).all()
    return send_response([DietOut.model_validate(i).model_dump() for i in items], "OK")


@router.get("/{id}/pdf")
def pdf(id: int, db: Session = Depends(get_db), _=Depends(get_current_user)):
    if not _get_or_404(db, id):
        return send_error("Dieta no encontrada")
    return send_response({"diet_id": id}, "PDF generado")


@router.post("/{client_id}/assigned")
def assigned(client_id: int, data: DietAssignRequest, db: Session = Depends(get_db), _=Depends(get_current_user)):
    diet = _get_or_404(db, data.client_id)
    if not diet:
        return send_error("Dieta no encontrada")
    diet.client_id = client_id
    db.commit()
    return send_response(None, "Dieta asignada")


@router.get("/{id}/edit")
def edit(id: int, db: Session = Depends(get_db), _=Depends(get_current_user)):
    diet = _get_or_404(db, id)
    if not diet:
        return send_error("Dieta no encontrada")
    return send_response(DietOut.model_validate(diet).model_dump(), "OK")


@router.post("")
def create(data: DietCreate, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    diet_data = data.model_dump(exclude={"details"})
    diet_data["instructor_id"] = current_user.id
    diet = Diet(**diet_data)
    db.add(diet)
    db.flush()
    for detail in (data.details or []):
        db.add(DietDetail(diet_id=diet.id, **detail.model_dump()))
    db.commit()
    db.refresh(diet)
    return send_response(DietOut.model_validate(diet).model_dump(), "Dieta creada")


@router.put("/{id}/update")
def updated(id: int, data: DietUpdate, db: Session = Depends(get_db), _=Depends(get_current_user)):
    diet = _get_or_404(db, id)
    if not diet:
        return send_error("Dieta no encontrada")
    for f, v in data.model_dump(exclude_unset=True, exclude={"details"}).items():
        setattr(diet, f, v)
    if data.details is not None:
        db.query(DietDetail).filter(DietDetail.diet_id == diet.id).delete()
        for detail in data.details:
            db.add(DietDetail(diet_id=diet.id, **detail.model_dump()))
    db.commit()
    db.refresh(diet)
    return send_response(DietOut.model_validate(diet).model_dump(), "Dieta actualizada")
