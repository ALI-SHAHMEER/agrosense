from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel


# ── Farm ──────────────────────────────────────────────────────────────────────

class FarmCreate(BaseModel):
    name: str
    area_ha: Optional[float] = None
    district: Optional[str] = None
    province: Optional[str] = None
    latitude: Optional[float] = None    # for storing the centroid point
    longitude: Optional[float] = None


class FarmUpdate(BaseModel):
    name: Optional[str] = None
    area_ha: Optional[float] = None
    district: Optional[str] = None
    province: Optional[str] = None


class FarmOut(BaseModel):
    id: UUID
    name: str
    area_ha: Optional[float]
    district: Optional[str]
    province: Optional[str]
    latitude: Optional[float]
    longitude: Optional[float]
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Field ─────────────────────────────────────────────────────────────────────

class FieldCreate(BaseModel):
    farm_id: UUID
    name: Optional[str] = None
    crop_type: Optional[str] = None
    planting_date: Optional[datetime] = None
    area_ha: Optional[float] = None
    # GeoJSON polygon coordinates accepted as a list of [lon, lat] pairs
    boundary_coords: Optional[list[list[float]]] = None


class FieldUpdate(BaseModel):
    name: Optional[str] = None
    crop_type: Optional[str] = None
    planting_date: Optional[datetime] = None
    area_ha: Optional[float] = None


class FieldOut(BaseModel):
    id: UUID
    farm_id: UUID
    name: Optional[str]
    crop_type: Optional[str]
    planting_date: Optional[datetime]
    area_ha: Optional[float]
    created_at: datetime

    model_config = {"from_attributes": True}
