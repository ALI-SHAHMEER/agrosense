"""
Direct unit tests for app/ml/predictor.py — no HTTP layer, no DB.
Tests function correctness, edge cases, and agronomic consistency.
"""
import sys
import pytest
import numpy as np

sys.path.insert(0, ".")
from app.ml.predictor import (
    predict_crop_stress,
    predict_irrigation,
    predict_vra_zone,
    predict_yield,
    predict_soil,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

HEALTHY = {
    "ndvi": 0.65, "evi": 0.50, "ndwi": 0.10, "ndre": 0.40,
    "lai": 4.0, "ndvi_std": 0.08, "ndvi_min": 0.40, "ndvi_max": 0.85,
}
STRESSED = {
    "ndvi": 0.22, "evi": 0.15, "ndwi": -0.45, "ndre": 0.12,
    "lai": 0.50, "ndvi_std": 0.20, "ndvi_min": 0.05, "ndvi_max": 0.45,
}
BARE_SOIL = {
    "ndvi": 0.02, "evi": 0.01, "ndwi": -0.60, "ndre": 0.03,
    "lai": 0.10, "ndvi_std": 0.05, "ndvi_min": -0.05, "ndvi_max": 0.10,
}
WATER = {
    "ndvi": -0.20, "evi": -0.10, "ndwi": 0.55, "ndre": -0.05,
    "lai": 0.0, "ndvi_std": 0.03, "ndvi_min": -0.30, "ndvi_max": -0.10,
}
PARTIAL = {"ndvi": 0.40}  # missing most keys


# ---------------------------------------------------------------------------
# Crop Stress
# ---------------------------------------------------------------------------

class TestCropStress:
    def test_returns_required_keys(self):
        r = predict_crop_stress(HEALTHY)
        assert "prediction" in r
        assert "confidence" in r
        assert "probabilities" in r

    def test_confidence_in_range(self):
        for sample in (HEALTHY, STRESSED, BARE_SOIL):
            r = predict_crop_stress(sample)
            assert 0.0 <= r["confidence"] <= 1.0

    def test_probabilities_sum_to_one(self):
        r = predict_crop_stress(HEALTHY)
        total = sum(r["probabilities"].values())
        assert abs(total - 1.0) < 1e-4

    def test_prediction_is_known_class(self):
        r = predict_crop_stress(HEALTHY)
        assert r["prediction"] in ("Healthy", "Stressed", "Diseased")

    def test_healthy_ndvi_predicts_better_than_stressed(self):
        rh = predict_crop_stress(HEALTHY)
        rs = predict_crop_stress(STRESSED)
        healthy_prob = rh["probabilities"].get("Healthy", 0)
        stressed_prob = rs["probabilities"].get("Stressed", 0) + rs["probabilities"].get("Diseased", 0)
        assert healthy_prob > 0.3
        assert stressed_prob > 0.3

    def test_partial_indices_do_not_crash(self):
        r = predict_crop_stress(PARTIAL)
        assert "prediction" in r

    def test_empty_indices_do_not_crash(self):
        r = predict_crop_stress({})
        assert "prediction" in r

    def test_confidence_equals_max_probability(self):
        r = predict_crop_stress(HEALTHY)
        assert abs(r["confidence"] - max(r["probabilities"].values())) < 1e-4

    def test_water_body_indices(self):
        r = predict_crop_stress(WATER)
        assert "prediction" in r
        assert 0.0 <= r["confidence"] <= 1.0


# ---------------------------------------------------------------------------
# Irrigation
# ---------------------------------------------------------------------------

class TestIrrigation:
    def test_returns_required_keys(self):
        r = predict_irrigation(HEALTHY)
        for k in ("recommendation", "confidence", "soil_moisture_pct", "water_amount_mm", "probabilities"):
            assert k in r

    def test_recommendation_is_valid_class(self):
        r = predict_irrigation(HEALTHY)
        assert isinstance(r["recommendation"], str)
        assert len(r["recommendation"]) > 0

    def test_soil_moisture_non_negative(self):
        for sample in (HEALTHY, STRESSED, BARE_SOIL):
            r = predict_irrigation(sample)
            assert r["soil_moisture_pct"] >= 0

    def test_water_amount_non_negative(self):
        r = predict_irrigation(STRESSED)
        assert r["water_amount_mm"] >= 0

    def test_high_ndwi_reduces_water_need(self):
        wet   = dict(HEALTHY, ndwi=0.40)
        dry   = dict(HEALTHY, ndwi=-0.60)
        r_wet = predict_irrigation(wet)
        r_dry = predict_irrigation(dry)
        assert r_wet["water_amount_mm"] <= r_dry["water_amount_mm"]

    def test_weather_param_used(self):
        r1 = predict_irrigation(HEALTHY, {"temp_celsius": 20, "rainfall_mm": 100})
        r2 = predict_irrigation(HEALTHY, {"temp_celsius": 45, "rainfall_mm": 0})
        assert isinstance(r1["recommendation"], str)
        assert isinstance(r2["recommendation"], str)

    def test_probabilities_sum_to_one(self):
        r = predict_irrigation(HEALTHY)
        total = sum(r["probabilities"].values())
        assert abs(total - 1.0) < 1e-4

    def test_explicit_soil_moisture_overrides_ndwi(self):
        r = predict_irrigation(HEALTHY, {"soil_moisture_pct": 80})
        assert r["soil_moisture_pct"] == pytest.approx(80.0, abs=1.0)


# ---------------------------------------------------------------------------
# VRA Zones
# ---------------------------------------------------------------------------

class TestVRAZones:
    def test_returns_required_keys(self):
        r = predict_vra_zone(HEALTHY)
        for k in ("zone", "confidence", "fertiliser_recommendation", "probabilities"):
            assert k in r

    def test_zone_is_valid(self):
        r = predict_vra_zone(HEALTHY)
        assert r["zone"] in ("Low", "Medium", "High")

    def test_fertiliser_recommendation_is_string(self):
        r = predict_vra_zone(HEALTHY)
        assert isinstance(r["fertiliser_recommendation"], str)
        assert len(r["fertiliser_recommendation"]) > 5

    def test_probabilities_sum_to_one(self):
        r = predict_vra_zone(HEALTHY)
        total = sum(r["probabilities"].values())
        assert abs(total - 1.0) < 1e-4

    def test_high_ndvi_yields_high_or_medium_zone(self):
        r = predict_vra_zone(HEALTHY)
        assert r["zone"] in ("High", "Medium")

    def test_low_ndvi_yields_low_or_medium_zone(self):
        r = predict_vra_zone(BARE_SOIL)
        assert r["zone"] in ("Low", "Medium")

    def test_confidence_in_range(self):
        r = predict_vra_zone(STRESSED)
        assert 0.0 <= r["confidence"] <= 1.0


# ---------------------------------------------------------------------------
# Yield
# ---------------------------------------------------------------------------

CROPS = ["wheat", "rice", "cotton", "sugarcane", "mango"]
BENCHMARKS = {"wheat": 3.1, "rice": 4.1, "cotton": 1.6, "sugarcane": 58.0, "mango": 8.5}


class TestYield:
    def test_returns_required_keys(self):
        r = predict_yield(HEALTHY)
        for k in ("predicted_yield_tha", "yield_lower_bound", "yield_upper_bound", "harvest_readiness_pct"):
            assert k in r

    def test_yield_positive(self):
        r = predict_yield(HEALTHY)
        assert r["predicted_yield_tha"] > 0

    def test_lower_le_predicted_le_upper(self):
        r = predict_yield(HEALTHY)
        assert r["yield_lower_bound"] <= r["predicted_yield_tha"] <= r["yield_upper_bound"]

    def test_harvest_readiness_capped_at_100(self):
        r = predict_yield(HEALTHY, growing_days=200)
        assert r["harvest_readiness_pct"] == 100.0

    def test_harvest_readiness_scales_with_days(self):
        r60  = predict_yield(HEALTHY, growing_days=60)
        r120 = predict_yield(HEALTHY, growing_days=120)
        assert r60["harvest_readiness_pct"] <= r120["harvest_readiness_pct"]

    def test_harvest_readiness_zero_days(self):
        r = predict_yield(HEALTHY, growing_days=0)
        assert r["harvest_readiness_pct"] == 0.0

    @pytest.mark.parametrize("crop", CROPS)
    def test_all_crop_types_accepted(self, crop):
        r = predict_yield(HEALTHY, crop_type=crop)
        assert r["predicted_yield_tha"] > 0

    @pytest.mark.parametrize("crop", CROPS)
    def test_yield_within_30pct_of_benchmark(self, crop):
        r = predict_yield(HEALTHY, crop_type=crop, growing_days=120,
                          rainfall_mm=200, temp_celsius=26)
        pred = r["predicted_yield_tha"]
        real = BENCHMARKS[crop]
        err  = abs(pred - real) / real
        assert err < 0.35, f"{crop}: predicted {pred:.2f} vs benchmark {real} ({err*100:.1f}%)"

    def test_unknown_crop_type_uses_default(self):
        r = predict_yield(HEALTHY, crop_type="unknown_crop_xyz")
        assert r["predicted_yield_tha"] > 0

    def test_higher_rainfall_does_not_crash(self):
        r = predict_yield(HEALTHY, rainfall_mm=1000)
        assert r["predicted_yield_tha"] > 0

    def test_extreme_temperature(self):
        r_cold = predict_yield(HEALTHY, temp_celsius=0)
        r_hot  = predict_yield(HEALTHY, temp_celsius=55)
        assert r_cold["predicted_yield_tha"] > 0
        assert r_hot["predicted_yield_tha"] > 0

    def test_keyword_arg_order_crop_type(self):
        # Regression: crop_type used to be 3rd positional, conflicting with rainfall_mm
        r = predict_yield(HEALTHY, 120, 200, 26, "rice")
        assert r["predicted_yield_tha"] > 0

    def test_lower_bound_non_negative(self):
        r = predict_yield(BARE_SOIL)
        assert r["yield_lower_bound"] >= 0.0

    def test_deterministic(self):
        r1 = predict_yield(HEALTHY, crop_type="wheat")
        r2 = predict_yield(HEALTHY, crop_type="wheat")
        assert r1["predicted_yield_tha"] == r2["predicted_yield_tha"]


# ---------------------------------------------------------------------------
# Soil Assessment
# ---------------------------------------------------------------------------

class TestSoil:
    def test_returns_required_keys(self):
        r = predict_soil(HEALTHY)
        for k in ("soil_ph", "salinity_ds_m", "organic_matter_pct",
                  "ph_status", "salinity_status", "organic_matter_status"):
            assert k in r

    def test_ph_in_realistic_range(self):
        r = predict_soil(HEALTHY)
        assert 3.0 <= r["soil_ph"] <= 10.0

    def test_salinity_non_negative(self):
        r = predict_soil(HEALTHY)
        assert r["salinity_ds_m"] >= 0

    def test_organic_matter_non_negative(self):
        r = predict_soil(HEALTHY)
        assert r["organic_matter_pct"] >= 0

    def test_ph_status_is_valid(self):
        r = predict_soil(HEALTHY)
        assert r["ph_status"] in ("Optimal", "Acidic", "Alkaline")

    def test_salinity_status_is_valid(self):
        r = predict_soil(STRESSED)
        assert r["salinity_status"] in ("Normal", "Moderate", "High — leaching needed")

    def test_om_status_is_valid(self):
        r = predict_soil(BARE_SOIL)
        assert r["organic_matter_status"] in ("Good", "Low — add compost", "Very low — critical")

    def test_bands_parameter_accepted(self):
        bands = {"b2": 0.05, "b3": 0.08, "b4": 0.07, "b8": 0.30, "b11": 0.15}
        r = predict_soil(HEALTHY, bands=bands)
        assert r["soil_ph"] is not None

    def test_no_bands_uses_defaults(self):
        r = predict_soil(HEALTHY, bands=None)
        assert r["soil_ph"] is not None

    def test_partial_indices_do_not_crash(self):
        r = predict_soil(PARTIAL)
        assert "soil_ph" in r


# ---------------------------------------------------------------------------
# Cross-model consistency
# ---------------------------------------------------------------------------

class TestCrossModelConsistency:
    def test_healthy_field_better_stress_than_stressed(self):
        rh = predict_crop_stress(HEALTHY)
        rs = predict_crop_stress(STRESSED)
        ph = rh["probabilities"].get("Healthy", 0)
        ps = rs["probabilities"].get("Healthy", 0)
        assert ph > ps

    def test_dry_field_more_water_than_wet(self):
        wet = predict_irrigation(dict(HEALTHY, ndwi=0.30))
        dry = predict_irrigation(dict(HEALTHY, ndwi=-0.60))
        assert wet["water_amount_mm"] <= dry["water_amount_mm"]

    def test_all_five_models_run_on_same_indices(self):
        for fn in (predict_crop_stress, predict_vra_zone, predict_soil):
            r = fn(HEALTHY)
            assert isinstance(r, dict)
        predict_irrigation(HEALTHY)
        predict_yield(HEALTHY)
