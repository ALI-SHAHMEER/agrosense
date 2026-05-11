from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from geoalchemy2.shape import from_shape
from shapely.geometry import Polygon, box
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Farm, Field
from app.models import User
from app.routers.auth import get_current_user
from app.schemas.farm import FieldCreate, FieldOut, FieldUpdate

router = APIRouter(prefix="/fields", tags=["Fields"])


def _owned_farm(farm_id: UUID, user: User, db: Session) -> Farm:
    farm = db.query(Farm).filter(Farm.id == farm_id,
                                  Farm.user_id == user.id).first()
    if not farm:
        raise HTTPException(status_code=404, detail="Farm not found")
    return farm


def _auto_boundary(farm: Farm, area_ha: float = 10.0):
    """Generate a default boundary box from farm GPS or Pakistan center."""
    import math
    # Use farm GPS or default to Hyderabad, Sindh
    try:
        from geoalchemy2.shape import to_shape
        shape = to_shape(farm.location_geom)
        lat = shape.y
        lon = shape.x
    except:
        lat = 25.396
        lon = 68.374

    # Convert area to degrees (approx)
    area_m2  = float(area_ha or 10) * 10000
    side_m   = math.sqrt(area_m2)
    d_lat    = side_m / 111000.0
    d_lon    = side_m / (111000.0 * math.cos(math.radians(lat)))

    boundary = box(lon - d_lon, lat - d_lat,
                   lon + d_lon, lat + d_lat)
    return from_shape(boundary, srid=4326)


@router.post("/", response_model=FieldOut, status_code=status.HTTP_201_CREATED)
def create_field(
    payload: FieldCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    farm = _owned_farm(payload.farm_id, current_user, db)
    geom = None

    if payload.boundary_coords and len(payload.boundary_coords) >= 3:
        # Use provided boundary
        coords = [(c[0], c[1]) for c in payload.boundary_coords]
        if coords[0] != coords[-1]:
            coords.append(coords[0])
        geom = from_shape(Polygon(coords), srid=4326)
    else:
        # Auto-generate boundary from farm GPS
        geom = _auto_boundary(farm, payload.area_ha)

    field = Field(
        farm_id=payload.farm_id,
        name=payload.name,
        crop_type=payload.crop_type,
        planting_date=payload.planting_date,
        area_ha=payload.area_ha,
        boundary_geom=geom,
    )
    db.add(field)
    db.commit()
    db.refresh(field)
    return field


@router.get("/farm/{farm_id}", response_model=List[FieldOut])
def list_fields(
    farm_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _owned_farm(farm_id, current_user, db)
    return db.query(Field).filter(Field.farm_id == farm_id).all()


@router.get("/{field_id}", response_model=FieldOut)
def get_field(
    field_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    field = (
        db.query(Field)
        .join(Farm)
        .filter(Field.id == field_id, Farm.user_id == current_user.id)
        .first()
    )
    if not field:
        raise HTTPException(status_code=404, detail="Field not found")
    return field


@router.patch("/{field_id}", response_model=FieldOut)
def update_field(
    field_id: UUID,
    payload: FieldUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    field = (
        db.query(Field)
        .join(Farm)
        .filter(Field.id == field_id, Farm.user_id == current_user.id)
        .first()
    )
    if not field:
        raise HTTPException(status_code=404, detail="Field not found")
    for key, val in payload.model_dump(exclude_unset=True).items():
        setattr(field, key, val)
    db.commit()
    db.refresh(field)
    return field


@router.delete("/{field_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_field(
    field_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    field = (
        db.query(Field)
        .join(Farm)
        .filter(Field.id == field_id, Farm.user_id == current_user.id)
        .first()
    )
    if not field:
        raise HTTPException(status_code=404, detail="Field not found")
    db.delete(field)
    db.commit()
