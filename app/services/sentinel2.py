"""
Sentinel-2 Surface Reflectance Image Service
Fetches cloud-masked imagery for a given field boundary and date range.
"""
import ee


def get_sentinel2_collection(
    boundary_coords: list[list[float]],
    start_date: str,
    end_date: str,
    max_cloud_pct: float = 20.0,
) -> ee.ImageCollection:
    """
    Fetch a cloud-masked Sentinel-2 SR collection for a field boundary.

    Args:
        boundary_coords : list of [lon, lat] pairs forming the field polygon
        start_date      : 'YYYY-MM-DD'
        end_date        : 'YYYY-MM-DD'
        max_cloud_pct   : maximum cloud cover percentage to allow

    Returns:
        ee.ImageCollection filtered and cloud-masked
    """
    aoi = ee.Geometry.Polygon(boundary_coords)

    def mask_s2_clouds(image: ee.Image) -> ee.Image:
        """Use the Sentinel-2 QA60 band to mask clouds and cirrus."""
        qa = image.select("QA60")
        cloud_bit_mask  = 1 << 10   # opaque clouds
        cirrus_bit_mask = 1 << 11   # cirrus clouds
        mask = (
            qa.bitwiseAnd(cloud_bit_mask).eq(0)
            .And(qa.bitwiseAnd(cirrus_bit_mask).eq(0))
        )
        # Scale reflectance values from 0–10000 → 0–1
        return (
            image.updateMask(mask)
            .divide(10000)
            .copyProperties(image, ["system:time_start", "system:index"])
        )

    collection = (
        ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
        .filterBounds(aoi)
        .filterDate(start_date, end_date)
        .filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", max_cloud_pct))
        .sort("CLOUDY_PIXEL_PERCENTAGE")
        .limit(20)
        .map(mask_s2_clouds)
    )

    return collection


def get_best_sentinel2_image(
    boundary_coords: list[list[float]],
    start_date: str,
    end_date: str,
    max_cloud_pct: float = 20.0,
) -> ee.Image | None:
    """
    Return the median composite image (best single representative image)
    from a Sentinel-2 collection over the date range.
    Returns None if no images are available.
    """
    collection = get_sentinel2_collection(
        boundary_coords, start_date, end_date, max_cloud_pct
    )
    count = collection.size().getInfo()
    if count == 0:
        return None
    # Median composite reduces cloud/shadow artifacts
    return collection.median().set("image_count", count)


def get_collection_metadata(
    boundary_coords: list[list[float]],
    start_date: str,
    end_date: str,
    max_cloud_pct: float = 20.0,
) -> list[dict]:
    """
    Return metadata (date, cloud %) for each image in the collection.
    Useful for showing the user which images are available.
    """
    collection = get_sentinel2_collection(
        boundary_coords, start_date, end_date, max_cloud_pct
    )
    images = collection.toList(50)
    count = collection.size().getInfo()
    results = []
    for i in range(min(count, 50)):
        img = ee.Image(images.get(i))
        props = img.getInfo().get("properties", {})
        results.append({
            "date": props.get("system:index", "")[:8],
            "cloud_pct": props.get("CLOUDY_PIXEL_PERCENTAGE", 0),
            "gee_id": props.get("system:index", ""),
        })
    return results
