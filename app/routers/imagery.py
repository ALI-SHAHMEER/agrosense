from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.database import get_db
from app.models import Farm, Field, SatelliteImage, VegetationIndex
from app.models import User
from app.routers.auth import get_current_user
from app.services.gee_auth import init_gee
from app.services.pipeline import run_satellite_pipeline
from app.services.sentinel2 import get_collection_metadata

router = APIRouter(prefix="/imagery", tags=["Satellite Imagery"])


class AnalyzeRequest(BaseModel):
    field_id: UUID
    start_date: str
    end_date: str
    max_cloud_pct: float = 20.0


def _get_owned_field(field_id: UUID, user: User, db: Session) -> Field:
    field = (
        db.query(Field)
        .join(Farm)
        .filter(Field.id == field_id, Farm.user_id == user.id)
        .first()
    )
    if not field:
        raise HTTPException(status_code=404, detail="Field not found")
    return field


@router.post("/analyze")
def analyze_field(
    payload: AnalyzeRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _get_owned_field(payload.field_id, current_user, db)
    init_gee()
    try:
        result = run_satellite_pipeline(
            field_id=str(payload.field_id),
            db=db,
            start_date=payload.start_date,
            end_date=payload.end_date,
            max_cloud_pct=payload.max_cloud_pct,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"GEE pipeline error: {str(e)}")
    return result


@router.get("/field/{field_id}/history")
def get_index_history(
    field_id: UUID,
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _get_owned_field(field_id, current_user, db)
    records = (
        db.query(VegetationIndex)
        .join(SatelliteImage)
        .filter(SatelliteImage.field_id == field_id)
        .order_by(VegetationIndex.calculated_at.desc())
        .limit(limit)
        .all()
    )
    return [
        {
            "id": str(r.id),
            "ndvi": r.ndvi,
            "evi": r.evi,
            "ndwi": r.ndwi,
            "ndre": r.ndre,
            "lai": r.lai,
            "calculated_at": r.calculated_at,
        }
        for r in records
    ]


@router.get("/field/{field_id}/available")
def check_available_images(
    field_id: UUID,
    start_date: str = Query(...),
    end_date: str = Query(...),
    max_cloud_pct: float = Query(20.0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    field = _get_owned_field(field_id, current_user, db)
    if field.boundary_geom is None:
        raise HTTPException(status_code=400, detail="Field has no boundary geometry")
    from geoalchemy2.shape import to_shape
    shape = to_shape(field.boundary_geom)
    coords = [[x, y] for x, y in shape.exterior.coords]
    init_gee()
    images = get_collection_metadata(coords, start_date, end_date, max_cloud_pct)
    return {
        "field_id": str(field_id),
        "images_found": len(images),
        "images": images,
    }


@router.get("/field/{field_id}/bands/{band_type}")
def get_band_thumbnail(
    field_id: UUID,
    band_type: str,
    start_date: str = "2024-01-01",
    end_date: str = "2024-03-01",
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return a Sentinel-2 band composite thumbnail as PNG bytes."""
    from fastapi.responses import Response
    import ee

    field = (db.query(Field).join(Farm)
             .filter(Field.id == field_id, Farm.user_id == current_user.id)
             .first())
    if not field:
        raise HTTPException(status_code=404, detail="Field not found")

    try:
        from geoalchemy2.shape import to_shape
        from app.models import Farm as FarmModel
        
        # Get farm GPS for accurate location
        farm = db.query(FarmModel).filter(FarmModel.id == field.farm_id).first()
        
        # Try farm GPS first (most accurate)
        lat, lon = None, None
        if farm and farm.location_geom:
            try:
                farm_shape = to_shape(farm.location_geom)
                lon, lat = farm_shape.x, farm_shape.y
            except: pass
        
        # Fallback to field boundary centroid
        if not lat or not lon:
            shape    = to_shape(field.boundary_geom)
            centroid = shape.centroid
            lon, lat = centroid.x, centroid.y
        
        # Skip default Hyderabad location — use farm GPS instead
        DEFAULT_LON, DEFAULT_LAT = 68.374, 25.396
        if abs(lon - DEFAULT_LON) < 0.01 and abs(lat - DEFAULT_LAT) < 0.01:
            if farm and farm.location_geom:
                farm_shape = to_shape(farm.location_geom)
                lon, lat = farm_shape.x, farm_shape.y

        buf  = 0.04  # ~4km buffer
        geom = ee.Geometry.Rectangle([lon-buf, lat-buf, lon+buf, lat+buf])
        print(f"Band view for {field.name}: lat={lat:.3f}, lon={lon:.3f}")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Location error: {e}")

    BANDS_MAP = {
        "agriculture": (["B11","B8","B2"],  0, 3000),
        "vegetation":  (["B8A","B4","B3"],  0, 3000),
        "ndre":        (["B5","B4","B3"],   0, 3000),
        "truecolor":   (["B4","B3","B2"],   0, 3000),
        "falsecolor":  (["B8","B4","B3"],   0, 3000),
        "ndvi":        (["NDVI"],        -0.2, 0.8),
    }

    if band_type not in BANDS_MAP:
        raise HTTPException(status_code=400, detail=f"Unknown band type: {band_type}")

    bands, vmin, vmax = BANDS_MAP[band_type]

    col = (ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
           .filterBounds(geom)
           .filterDate(start_date, end_date)
           .filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", 30))
           .sort("CLOUDY_PIXEL_PERCENTAGE")
           .limit(10))

    image = col.median()

    if bands == ["NDVI"]:
        vis = image.normalizedDifference(["B8","B4"]).visualize(
            min=vmin, max=vmax,
            palette=["d73027","f46d43","fdae61","fee08b",
                     "d9ef8b","a6d96a","66bd63","1a9850"])
    else:
        vis = image.select(bands).visualize(min=vmin, max=vmax, gamma=1.4)

    import requests as req
    import google.auth.transport.requests

    thumb_id = vis.getThumbId({"region": geom, "dimensions": 600, "format": "png", "crs": "EPSG:4326"})

    # Refresh GEE credentials
    creds = ee.data._credentials
    creds.refresh(google.auth.transport.requests.Request())

    # Download thumbnail
    url = f"https://earthengine.googleapis.com/v1/{thumb_id['thumbid']}:getPixels"
    r   = req.get(url, headers={"Authorization": f"Bearer {creds.token}"}, timeout=90)

    if r.status_code != 200:
        raise HTTPException(status_code=500, detail=f"GEE thumbnail error: {r.status_code}")

    return Response(content=r.content, media_type="image/png")
