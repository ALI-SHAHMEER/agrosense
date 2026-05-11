from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from geoalchemy2.shape import from_shape
from shapely.geometry import Point
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Farm
from app.routers.auth import get_current_user
from app.schemas.farm import FarmCreate, FarmOut, FarmUpdate
from app.models import User

router = APIRouter(prefix="/farms", tags=["Farms"])


@router.post("/", response_model=FarmOut, status_code=status.HTTP_201_CREATED)
def create_farm(
    payload: FarmCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    geom = None
    if payload.latitude is not None and payload.longitude is not None:
        geom = from_shape(Point(payload.longitude, payload.latitude), srid=4326)

    farm = Farm(
        user_id=current_user.id,
        name=payload.name,
        area_ha=payload.area_ha,
        district=payload.district,
        province=payload.province,
        location_geom=geom,
    )
    db.add(farm)
    db.commit()
    db.refresh(farm)
    return farm


@router.get("/", response_model=List[FarmOut])
def list_farms(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return db.query(Farm).filter(Farm.user_id == current_user.id).all()


@router.get("/{farm_id}", response_model=FarmOut)
def get_farm(
    farm_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    farm = db.query(Farm).filter(Farm.id == farm_id,
                                  Farm.user_id == current_user.id).first()
    if not farm:
        raise HTTPException(status_code=404, detail="Farm not found")
    return farm


@router.patch("/{farm_id}", response_model=FarmOut)
def update_farm(
    farm_id: UUID,
    payload: FarmUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    farm = db.query(Farm).filter(Farm.id == farm_id,
                                  Farm.user_id == current_user.id).first()
    if not farm:
        raise HTTPException(status_code=404, detail="Farm not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(farm, field, value)
    db.commit()
    db.refresh(farm)
    return farm


@router.delete("/{farm_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_farm(
    farm_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    farm = db.query(Farm).filter(Farm.id == farm_id,
                                  Farm.user_id == current_user.id).first()
    if not farm:
        raise HTTPException(status_code=404, detail="Farm not found")
    db.delete(farm)
    db.commit()
