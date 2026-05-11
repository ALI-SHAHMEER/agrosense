from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel


class VegetationIndexOut(BaseModel):
    id: UUID
    image_id: UUID
    ndvi: Optional[float]
    evi: Optional[float]
    ndwi: Optional[float]
    ndre: Optional[float]
    lai: Optional[float]
    calculated_at: datetime

    model_config = {"from_attributes": True}


class MLPredictionOut(BaseModel):
    id: UUID
    field_id: UUID
    model_type: str
    model_version: str
    result_data: Optional[Any]
    confidence: Optional[float]
    predicted_at: datetime

    model_config = {"from_attributes": True, "protected_namespaces": ()}


class IrrigationRecOut(BaseModel):
    id: UUID
    field_id: UUID
    soil_moisture_pct: Optional[float]
    recommendation: str
    water_amount_mm: Optional[float]
    notes: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}


class YieldPredictionOut(BaseModel):
    id: UUID
    field_id: UUID
    predicted_yield_tha: float
    yield_lower_bound: Optional[float]
    yield_upper_bound: Optional[float]
    estimated_harvest: Optional[datetime]
    harvest_readiness_pct: Optional[float]
    model_version: str
    predicted_at: datetime

    model_config = {"from_attributes": True, "protected_namespaces": ()}
