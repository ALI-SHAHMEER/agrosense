"""
ML Models API Router
POST /ml/field/{field_id}/crop-stress
POST /ml/field/{field_id}/irrigation
POST /ml/field/{field_id}/vra-zones
POST /ml/field/{field_id}/yield
POST /ml/field/{field_id}/soil
POST /ml/field/{field_id}/full-analysis  ← runs all 5 at once
"""
from uuid import UUID
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import Optional

from app.database import get_db
from app.models import Farm, Field, MLPrediction, IrrigationRec, YieldPrediction, User
from app.routers.auth import get_current_user
from app.ml.predictor import (
    predict_crop_stress,
    predict_irrigation,
    predict_vra_zone,
    predict_yield,
    predict_soil,
)

router = APIRouter(prefix="/ml", tags=["ML Models"])


# ── Request schemas ───────────────────────────────────────────────────────────

class WeatherInput(BaseModel):
    temp_celsius: float = 28.0
    rainfall_mm: float = 10.0
    soil_moisture_pct: Optional[float] = None


class YieldInput(BaseModel):
    growing_days: int = 120
    rainfall_mm: float = 200.0
    temp_celsius: float = 26.0


# ── Helper ────────────────────────────────────────────────────────────────────

def _get_field_with_indices(field_id: UUID, user: User, db: Session):
    """Load field + most recent vegetation indices."""
    from app.models import SatelliteImage, VegetationIndex

    field = (
        db.query(Field)
        .join(Farm)
        .filter(Field.id == field_id, Farm.user_id == user.id)
        .first()
    )
    if not field:
        raise HTTPException(status_code=404, detail="Field not found")

    # Get most recent vegetation index record
    latest = (
        db.query(VegetationIndex)
        .join(SatelliteImage)
        .filter(SatelliteImage.field_id == field_id)
        .order_by(VegetationIndex.calculated_at.desc())
        .first()
    )
    if not latest:
        raise HTTPException(
            status_code=400,
            detail="No vegetation indices found for this field. "
                   "Run POST /imagery/analyze first."
        )

    indices = {
        "ndvi":     latest.ndvi,
        "evi":      latest.evi,
        "ndwi":     latest.ndwi,
        "ndre":     latest.ndre,
        "lai":      latest.lai,
        "ndvi_std": latest.ndvi_std,
        "ndvi_min": latest.ndvi_min,
        "ndvi_max": latest.ndvi_max,
    }
    return field, indices


def _save_ml_prediction(db, field_id, model_type, result, confidence):
    pred = MLPrediction(
        field_id=field_id,
        model_type=model_type,
        result_data=result,
        confidence=confidence,
    )
    db.add(pred)
    db.commit()
    return pred


# ── Routes ────────────────────────────────────────────────────────────────────

@router.post("/field/{field_id}/crop-stress")
def run_crop_stress(
    field_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Detect crop health: Healthy / Stressed / Diseased"""
    field, indices = _get_field_with_indices(field_id, current_user, db)
    try:
        result = predict_crop_stress(indices)
    except FileNotFoundError as e:
        raise HTTPException(status_code=503, detail=str(e))

    _save_ml_prediction(db, field_id, "crop_stress", result, result["confidence"])
    return {"field_id": str(field_id), "field_name": field.name, **result}


@router.post("/field/{field_id}/irrigation")
def run_irrigation(
    field_id: UUID,
    weather: WeatherInput = WeatherInput(),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Predict irrigation need and water amount."""
    field, indices = _get_field_with_indices(field_id, current_user, db)
    try:
        result = predict_irrigation(indices, weather.model_dump())
    except FileNotFoundError as e:
        raise HTTPException(status_code=503, detail=str(e))

    # Save irrigation recommendation
    rec = IrrigationRec(
        field_id=field_id,
        soil_moisture_pct=result["soil_moisture_pct"],
        recommendation=result["recommendation"],
        water_amount_mm=result["water_amount_mm"],
    )
    db.add(rec)
    db.commit()
    return {"field_id": str(field_id), "field_name": field.name, **result}


@router.post("/field/{field_id}/vra-zones")
def run_vra_zones(
    field_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Predict fertility zone for variable rate fertiliser application."""
    field, indices = _get_field_with_indices(field_id, current_user, db)
    try:
        result = predict_vra_zone(indices)
    except FileNotFoundError as e:
        raise HTTPException(status_code=503, detail=str(e))

    _save_ml_prediction(db, field_id, "vra_zones", result, result["confidence"])
    return {"field_id": str(field_id), "field_name": field.name, **result}


@router.post("/field/{field_id}/yield")
def run_yield(
    field_id: UUID,
    params: YieldInput = YieldInput(),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Predict crop yield in tons per hectare."""
    field, indices = _get_field_with_indices(field_id, current_user, db)
    try:
        result = predict_yield(
            indices,
            growing_days=params.growing_days,
            rainfall_mm=params.rainfall_mm,
            temp_celsius=params.temp_celsius,
        )
    except FileNotFoundError as e:
        raise HTTPException(status_code=503, detail=str(e))

    # Save yield prediction
    yp = YieldPrediction(
        field_id=field_id,
        predicted_yield_tha=result["predicted_yield_tha"],
        yield_lower_bound=result["yield_lower_bound"],
        yield_upper_bound=result["yield_upper_bound"],
        harvest_readiness_pct=result["harvest_readiness_pct"],
    )
    db.add(yp)
    db.commit()
    return {"field_id": str(field_id), "field_name": field.name, **result}


@router.post("/field/{field_id}/soil")
def run_soil(
    field_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Assess soil pH, salinity, and organic matter."""
    field, indices = _get_field_with_indices(field_id, current_user, db)
    try:
        result = predict_soil(indices)
    except FileNotFoundError as e:
        raise HTTPException(status_code=503, detail=str(e))

    _save_ml_prediction(db, field_id, "soil_assessment", result, 0.85)
    return {"field_id": str(field_id), "field_name": field.name, **result}


@router.post("/field/{field_id}/full-analysis")
def run_full_analysis(
    field_id: UUID,
    weather: WeatherInput = WeatherInput(),
    yield_params: YieldInput = YieldInput(),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Run all 5 models at once and return a complete field report.
    This is the main endpoint for the dashboard.
    """
    field, indices = _get_field_with_indices(field_id, current_user, db)

    try:
        stress   = predict_crop_stress(indices)
        irrig    = predict_irrigation(indices, weather.model_dump())
        vra      = predict_vra_zone(indices)
        yld      = predict_yield(indices, yield_params.growing_days,
                                 yield_params.rainfall_mm, yield_params.temp_celsius)
        soil     = predict_soil(indices)
    except FileNotFoundError as e:
        raise HTTPException(status_code=503, detail=str(e))

    return {
        "field_id":           str(field_id),
        "field_name":         field.name,
        "crop_type":          field.crop_type,
        "analysed_at":        datetime.now(timezone.utc).isoformat(),
        "vegetation_indices": indices,
        "crop_stress":        stress,
        "irrigation":         irrig,
        "vra_zones":          vra,
        "yield_prediction":   yld,
        "soil_assessment":    soil,
    }
