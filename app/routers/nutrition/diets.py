from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional

from app.database import get_db
from app.core.dependencies import get_current_user
from app.models.nutrition.diet import Diet, DietDetail
from app.schemas.nutrition.diet import DietCreate, DietUpdate, DietOut, DietAssignRequest

router = APIRouter(prefix="/diets", tags=["Nutrition - Diets"])


def _get_or_404(db: Session, diet_id: int) -> Diet:
    obj = db.query(Diet).filter(Diet.id == diet_id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Dieta no encontrada")
    return obj


@router.get("/findAll")
def find_all(db: Session = Depends(get_db), _=Depends(get_current_user)):
    return [DietOut.model_validate(i) for i in db.query(Diet).filter(Diet.state == 1).all()]


@router.get("/client/{client_id}")
def client_diets(client_id: int, db: Session = Depends(get_db), _=Depends(get_current_user)):
    items = db.query(Diet).filter(Diet.client_id == client_id, Diet.state == 1).all()
    return [DietOut.model_validate(i) for i in items]


@router.get("/{id}/pdf")
def pdf(id: int, db: Session = Depends(get_db), _=Depends(get_current_user)):
    _get_or_404(db, id)
    return {"message": "PDF generado", "diet_id": id}


@router.post("/{client_id}/assigned")
def assigned(client_id: int, data: DietAssignRequest, db: Session = Depends(get_db), _=Depends(get_current_user)):
    diet = _get_or_404(db, data.client_id)
    diet.client_id = client_id
    db.commit()
    return {"message": "Dieta asignada"}


@router.get("/{id}/edit")
def edit(id: int, db: Session = Depends(get_db), _=Depends(get_current_user)):
    return DietOut.model_validate(_get_or_404(db, id))


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
    return DietOut.model_validate(diet)


@router.put("/{id}/update")
def updated(id: int, data: DietUpdate, db: Session = Depends(get_db), _=Depends(get_current_user)):
    diet = _get_or_404(db, id)
    update_data = data.model_dump(exclude_unset=True, exclude={"details"})
    for f, v in update_data.items():
        setattr(diet, f, v)
    if data.details is not None:
        db.query(DietDetail).filter(DietDetail.diet_id == diet.id).delete()
        for detail in data.details:
            db.add(DietDetail(diet_id=diet.id, **detail.model_dump()))
    db.commit()
    db.refresh(diet)
    return DietOut.model_validate(diet)
