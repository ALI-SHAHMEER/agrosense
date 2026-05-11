"""
AgroSense — SQLAlchemy ORM Models
All tables mirror the ERD from the project proposal.
"""
import uuid
from datetime import datetime, timezone

from geoalchemy2 import Geometry
from sqlalchemy import (
    Boolean, Column, DateTime, Enum, Float, ForeignKey,
    JSON, String, Text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.database import Base

# ── helpers ───────────────────────────────────────────────────────────────────

def _uuid():
    return str(uuid.uuid4())

def _now():
    return datetime.now(timezone.utc)


# ── User ──────────────────────────────────────────────────────────────────────

class User(Base):
    __tablename__ = "users"

    id         = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name       = Column(String(120), nullable=False)
    email      = Column(String(255), unique=True, nullable=False, index=True)
    password   = Column(String(255), nullable=False)
    role       = Column(Enum("admin", "farmer", "analyst", name="user_role"),
                        nullable=False, default="farmer")
    is_active  = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=_now)
    updated_at = Column(DateTime(timezone=True), default=_now, onupdate=_now)

    farms = relationship("Farm", back_populates="owner", cascade="all, delete-orphan")


# ── Farm ──────────────────────────────────────────────────────────────────────

class Farm(Base):
    __tablename__ = "farms"

    id           = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id      = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"),
                          nullable=False, index=True)
    name         = Column(String(200), nullable=False)
    location_geom = Column(Geometry("POINT", srid=4326))   # farm centroid
    area_ha      = Column(Float)
    district     = Column(String(100))
    province     = Column(String(100))
    created_at   = Column(DateTime(timezone=True), default=_now)

    owner  = relationship("User", back_populates="farms")
    fields = relationship("Field", back_populates="farm", cascade="all, delete-orphan")

    @property
    def latitude(self):
        if self.location_geom is None:
            return None
        from geoalchemy2.shape import to_shape
        return to_shape(self.location_geom).y

    @property
    def longitude(self):
        if self.location_geom is None:
            return None
        from geoalchemy2.shape import to_shape
        return to_shape(self.location_geom).x


# ── Field ─────────────────────────────────────────────────────────────────────

class Field(Base):
    __tablename__ = "fields"

    id              = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    farm_id         = Column(UUID(as_uuid=True), ForeignKey("farms.id", ondelete="CASCADE"),
                             nullable=False, index=True)
    name            = Column(String(200))
    crop_type       = Column(String(100))
    planting_date   = Column(DateTime(timezone=True))
    boundary_geom   = Column(Geometry("POLYGON", srid=4326))  # field boundary polygon
    area_ha         = Column(Float)
    created_at      = Column(DateTime(timezone=True), default=_now)

    farm              = relationship("Farm", back_populates="fields")
    satellite_images  = relationship("SatelliteImage",  back_populates="field", cascade="all, delete-orphan")
    ml_predictions    = relationship("MLPrediction",    back_populates="field", cascade="all, delete-orphan")
    irrigation_recs   = relationship("IrrigationRec",   back_populates="field", cascade="all, delete-orphan")
    yield_predictions = relationship("YieldPrediction", back_populates="field", cascade="all, delete-orphan")


# ── SatelliteImage ────────────────────────────────────────────────────────────

class SatelliteImage(Base):
    __tablename__ = "satellite_images"

    id               = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    field_id         = Column(UUID(as_uuid=True), ForeignKey("fields.id", ondelete="CASCADE"),
                              nullable=False, index=True)
    source           = Column(Enum("sentinel2", "landsat8", name="satellite_source"), nullable=False)
    acquisition_date = Column(DateTime(timezone=True), nullable=False)
    cloud_cover_pct  = Column(Float, default=0.0)
    gee_asset_id     = Column(String(500))          # Earth Engine image ID
    bands_available  = Column(JSON)                  # list of band names stored
    created_at       = Column(DateTime(timezone=True), default=_now)

    field              = relationship("Field", back_populates="satellite_images")
    vegetation_indices = relationship("VegetationIndex", back_populates="image",
                                      cascade="all, delete-orphan")


# ── VegetationIndex ───────────────────────────────────────────────────────────

class VegetationIndex(Base):
    __tablename__ = "vegetation_indices"

    id           = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    image_id     = Column(UUID(as_uuid=True), ForeignKey("satellite_images.id", ondelete="CASCADE"),
                          nullable=False, index=True)
    ndvi         = Column(Float)    # Normalized Difference Vegetation Index
    evi          = Column(Float)    # Enhanced Vegetation Index
    ndwi         = Column(Float)    # Normalized Difference Water Index
    ndre         = Column(Float)    # Normalized Difference Red Edge
    lai          = Column(Float)    # Leaf Area Index
    ndvi_min     = Column(Float)    # spatial stats for the field
    ndvi_max     = Column(Float)
    ndvi_std     = Column(Float)
    calculated_at = Column(DateTime(timezone=True), default=_now)

    image = relationship("SatelliteImage", back_populates="vegetation_indices")


# ── MLPrediction ──────────────────────────────────────────────────────────────

class MLPrediction(Base):
    __tablename__ = "ml_predictions"

    id           = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    field_id     = Column(UUID(as_uuid=True), ForeignKey("fields.id", ondelete="CASCADE"),
                          nullable=False, index=True)
    model_type   = Column(
        Enum("crop_stress", "irrigation", "vra_zones", "soil_assessment", name="model_type_enum"),
        nullable=False,
    )
    model_version = Column(String(50), default="1.0.0")
    result_data  = Column(JSON)        # full prediction output (class probs, zone map, etc.)
    confidence   = Column(Float)       # overall confidence score 0–1
    predicted_at = Column(DateTime(timezone=True), default=_now)

    field = relationship("Field", back_populates="ml_predictions")


# ── IrrigationRec ─────────────────────────────────────────────────────────────

class IrrigationRec(Base):
    __tablename__ = "irrigation_recs"

    id                = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    field_id          = Column(UUID(as_uuid=True), ForeignKey("fields.id", ondelete="CASCADE"),
                               nullable=False, index=True)
    soil_moisture_pct = Column(Float)
    recommendation    = Column(
        Enum("irrigate_now", "irrigate_soon", "adequate", "overwatered",
             name="irrigation_status"),
        nullable=False,
    )
    water_amount_mm   = Column(Float)    # recommended water amount
    notes             = Column(Text)
    created_at        = Column(DateTime(timezone=True), default=_now)

    field = relationship("Field", back_populates="irrigation_recs")


# ── YieldPrediction ───────────────────────────────────────────────────────────

class YieldPrediction(Base):
    __tablename__ = "yield_predictions"

    id                   = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    field_id             = Column(UUID(as_uuid=True), ForeignKey("fields.id", ondelete="CASCADE"),
                                  nullable=False, index=True)
    predicted_yield_tha  = Column(Float, nullable=False)  # tons per hectare
    yield_lower_bound    = Column(Float)   # 95% confidence interval
    yield_upper_bound    = Column(Float)
    estimated_harvest    = Column(DateTime(timezone=True))
    harvest_readiness_pct = Column(Float)  # 0–100%
    model_version        = Column(String(50), default="1.0.0")
    predicted_at         = Column(DateTime(timezone=True), default=_now)

    field = relationship("Field", back_populates="yield_predictions")
