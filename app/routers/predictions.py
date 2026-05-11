from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Farm, Field, IrrigationRec, MLPrediction, YieldPrediction
from app.models import User
from app.routers.auth import get_current_user
from app.schemas.predictions import IrrigationRecOut, MLPredictionOut, YieldPredictionOut

router = APIRouter(prefix="/predictions", tags=["Predictions"])


def _owned_field(field_id: UUID, user: User, db: Session) -> Field:
    field = (
        db.query(Field)
        .join(Farm)
        .filter(Field.id == field_id, Farm.user_id == user.id)
        .first()
    )
    if not field:
        raise HTTPException(status_code=404, detail="Field not found")
    return field


@router.get("/field/{field_id}/ml", response_model=List[MLPredictionOut])
def get_ml_predictions(
    field_id: UUID,
    model_type: str = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _owned_field(field_id, current_user, db)
    q = db.query(MLPrediction).filter(MLPrediction.field_id == field_id)
    if model_type:
        q = q.filter(MLPrediction.model_type == model_type)
    return q.order_by(MLPrediction.predicted_at.desc()).all()


@router.get("/field/{field_id}/irrigation", response_model=List[IrrigationRecOut])
def get_irrigation_recs(
    field_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _owned_field(field_id, current_user, db)
    return (
        db.query(IrrigationRec)
        .filter(IrrigationRec.field_id == field_id)
        .order_by(IrrigationRec.created_at.desc())
        .all()
    )


@router.get("/field/{field_id}/yield", response_model=List[YieldPredictionOut])
def get_yield_predictions(
    field_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _owned_field(field_id, current_user, db)
    return (
        db.query(YieldPrediction)
        .filter(YieldPrediction.field_id == field_id)
        .order_by(YieldPrediction.predicted_at.desc())
        .all()
    )
