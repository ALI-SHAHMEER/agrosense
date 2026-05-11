"""
Satellite Pipeline Orchestrator
Ties together: GEE fetch → index computation → DB save
Called by the /imagery router.
"""
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models import Field, Farm, SatelliteImage, VegetationIndex
from app.services.sentinel2 import (
    get_best_sentinel2_image,
    get_collection_metadata,
)
from app.services.indices import extract_field_statistics, interpret_indices


def _get_boundary_coords(field: Field) -> list[list[float]] | None:
    """Extract coordinates from PostGIS geometry."""
    if field.boundary_geom is None:
        return None
    from geoalchemy2.shape import to_shape
    shape = to_shape(field.boundary_geom)
    coords = [[x, y] for x, y in shape.exterior.coords]
    return coords


def run_satellite_pipeline(
    field_id: str,
    db: Session,
    start_date: str,
    end_date: str,
    max_cloud_pct: float = 20.0,
) -> dict:
    """
    Full pipeline for one field:
    1. Get field boundary from DB
    2. Fetch best Sentinel-2 composite from GEE
    3. Compute NDVI, EVI, NDWI, NDRE, LAI
    4. Save SatelliteImage + VegetationIndex records to DB
    5. Return stats + interpretation

    Returns a result dict ready to send as API response.
    """
    # ── 1. Load field ──────────────────────────────────────────────────────
    field = db.query(Field).filter(Field.id == field_id).first()
    if not field:
        raise ValueError(f"Field {field_id} not found")

    coords = _get_boundary_coords(field)
    if not coords:
        raise ValueError("Field has no boundary geometry. Add boundary_coords first.")

    # ── 2. Check available images ──────────────────────────────────────────
    available = get_collection_metadata(coords, start_date, end_date, max_cloud_pct)
    if not available:
        return {
            "status": "no_images",
            "message": f"No Sentinel-2 images found for this field between "
                       f"{start_date} and {end_date} with cloud cover < {max_cloud_pct}%.",
            "suggestion": "Try a wider date range or increase max_cloud_pct.",
        }

    # ── 3. Get median composite ────────────────────────────────────────────
    image = get_best_sentinel2_image(coords, start_date, end_date, max_cloud_pct)

    # ── 4. Compute indices ─────────────────────────────────────────────────
    stats = extract_field_statistics(image, coords, scale=10)
    interpretation = interpret_indices(stats)

    # ── 5. Save SatelliteImage record ──────────────────────────────────────
    sat_image = SatelliteImage(
        field_id=field_id,
        source="sentinel2",
        acquisition_date=datetime.strptime(start_date, "%Y-%m-%d").replace(
            tzinfo=timezone.utc
        ),
        cloud_cover_pct=available[0].get("cloud_pct", 0) if available else 0,
        gee_asset_id=f"S2_COMPOSITE_{start_date}_{end_date}",
        bands_available=["B2", "B3", "B4", "B5", "B8", "QA60"],
    )
    db.add(sat_image)
    db.flush()   # get the ID without committing yet

    # ── 6. Save VegetationIndex record ─────────────────────────────────────
    veg_index = VegetationIndex(
        image_id=sat_image.id,
        ndvi=stats["ndvi"],
        evi=stats["evi"],
        ndwi=stats["ndwi"],
        ndre=stats["ndre"],
        lai=stats["lai"],
        ndvi_min=stats["ndvi_min"],
        ndvi_max=stats["ndvi_max"],
        ndvi_std=stats["ndvi_std"],
    )
    db.add(veg_index)
    db.commit()

    return {
        "status": "success",
        "field_id": str(field_id),
        "field_name": field.name,
        "crop_type": field.crop_type,
        "date_range": {"start": start_date, "end": end_date},
        "images_found": len(available),
        "satellite_image_id": str(sat_image.id),
        "vegetation_index_id": str(veg_index.id),
        "indices": stats,
        "interpretation": interpretation,
    }
