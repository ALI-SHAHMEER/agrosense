"""
Vegetation Index Computation Service
Computes NDVI, EVI, NDWI, NDRE, LAI from a Sentinel-2 image
and returns both spatial statistics and per-pixel data.
"""
import ee


# ── Index formulas ────────────────────────────────────────────────────────────

def compute_ndvi(image: ee.Image) -> ee.Image:
    """
    NDVI = (NIR - Red) / (NIR + Red)
    Sentinel-2: NIR=B8, Red=B4
    Range: -1 to 1. Healthy vegetation > 0.4
    """
    return image.normalizedDifference(["B8", "B4"]).rename("NDVI")


def compute_evi(image: ee.Image) -> ee.Image:
    """
    EVI = 2.5 * (NIR - Red) / (NIR + 6*Red - 7.5*Blue + 1)
    Sentinel-2: NIR=B8, Red=B4, Blue=B2
    Less susceptible to atmospheric noise than NDVI.
    """
    return image.expression(
        "2.5 * ((NIR - RED) / (NIR + 6 * RED - 7.5 * BLUE + 1))",
        {
            "NIR":  image.select("B8"),
            "RED":  image.select("B4"),
            "BLUE": image.select("B2"),
        },
    ).rename("EVI")


def compute_ndwi(image: ee.Image) -> ee.Image:
    """
    NDWI = (Green - NIR) / (Green + NIR)
    Sentinel-2: Green=B3, NIR=B8
    Positive values indicate water/high moisture.
    """
    return image.normalizedDifference(["B3", "B8"]).rename("NDWI")


def compute_ndre(image: ee.Image) -> ee.Image:
    """
    NDRE = (NIR - RedEdge) / (NIR + RedEdge)
    Sentinel-2: NIR=B8, RedEdge=B5
    Better than NDVI for detecting early stress in dense canopies.
    """
    return image.normalizedDifference(["B8", "B5"]).rename("NDRE")


def compute_lai(image: ee.Image) -> ee.Image:
    """
    LAI approximation from NDVI:
    LAI = 3.618 * NDVI - 0.118
    Leaf Area Index: canopy density estimate.
    """
    ndvi = compute_ndvi(image)
    return ndvi.multiply(3.618).subtract(0.118).rename("LAI")


# ── Compute all indices and extract field stats ───────────────────────────────

def compute_all_indices(image: ee.Image) -> ee.Image:
    """Stack all indices into a single multi-band image."""
    return ee.Image([
        compute_ndvi(image),
        compute_evi(image),
        compute_ndwi(image),
        compute_ndre(image),
        compute_lai(image),
    ])


def extract_field_statistics(
    image: ee.Image,
    boundary_coords: list[list[float]],
    scale: int = 10,
) -> dict:
    """
    Compute mean, min, max, std dev for each index over the field polygon.

    Args:
        image           : Sentinel-2 median composite (already cloud-masked)
        boundary_coords : list of [lon, lat] pairs
        scale           : spatial resolution in metres (10m for S2)

    Returns:
        dict with keys: ndvi, evi, ndwi, ndre, lai,
                        ndvi_min, ndvi_max, ndvi_std
    """
    aoi = ee.Geometry.Polygon(boundary_coords)
    indices = compute_all_indices(image)

    # Mean reducer over the field
    means = indices.reduceRegion(
        reducer=ee.Reducer.mean(),
        geometry=aoi,
        scale=scale,
        maxPixels=1e9,
    ).getInfo()

    # Extra stats for NDVI
    ndvi_band  = compute_ndvi(image)
    ndvi_stats = ndvi_band.reduceRegion(
        reducer=ee.Reducer.minMax().combine(
            ee.Reducer.stdDev(), sharedInputs=True
        ),
        geometry=aoi,
        scale=scale,
        maxPixels=1e9,
    ).getInfo()

    return {
        "ndvi":     round(means.get("NDVI")  or 0, 4),
        "evi":      round(means.get("EVI")   or 0, 4),
        "ndwi":     round(means.get("NDWI")  or 0, 4),
        "ndre":     round(means.get("NDRE")  or 0, 4),
        "lai":      round(means.get("LAI")   or 0, 4),
        "ndvi_min": round(ndvi_stats.get("NDVI_min") or 0, 4),
        "ndvi_max": round(ndvi_stats.get("NDVI_max") or 0, 4),
        "ndvi_std": round(ndvi_stats.get("NDVI_stdDev") or 0, 4),
    }


def interpret_indices(stats: dict) -> dict:
    """
    Generate human-readable interpretation of index values.
    Used for dashboard alerts and recommendations.
    """
    ndvi = stats.get("ndvi", 0)
    ndwi = stats.get("ndwi", 0)

    # Crop health status
    if ndvi > 0.6:
        health = "Excellent"
    elif ndvi > 0.4:
        health = "Good"
    elif ndvi > 0.2:
        health = "Moderate — monitor closely"
    elif ndvi > 0.1:
        health = "Stressed — intervention recommended"
    else:
        health = "Severely stressed or bare soil"

    # Moisture status
    if ndwi > 0.3:
        moisture = "High — potential waterlogging"
    elif ndwi > 0.0:
        moisture = "Adequate"
    elif ndwi > -0.3:
        moisture = "Low — consider irrigation"
    else:
        moisture = "Very dry — irrigate immediately"

    return {
        "crop_health_status": health,
        "moisture_status": moisture,
        "ndvi_value": ndvi,
        "ndwi_value": ndwi,
    }
