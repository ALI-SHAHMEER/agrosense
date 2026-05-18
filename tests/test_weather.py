import pytest
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# We import only the pure functions — no DB, no HTTP needed
from app.routers.weather import _wmo_to_condition, _apply_rules, _planting_recommendation


def _day(temp_max=25, temp_min=15, temp_avg=20, rain_mm=0,
         rain_probability=10, humidity=60, wind_kmh=15,
         date="2026-05-18", day_name="Monday", condition="clear"):
    return dict(temp_max=temp_max, temp_min=temp_min, temp_avg=temp_avg,
                rain_mm=rain_mm, rain_probability=rain_probability,
                humidity=humidity, wind_kmh=wind_kmh, date=date,
                day_name=day_name, condition=condition)


# ── WMO condition map ─────────────────────────────────────────────────────────

def test_wmo_clear():
    assert _wmo_to_condition(0) == "clear"

def test_wmo_partly_cloudy():
    for code in (1, 2, 3):
        assert _wmo_to_condition(code) == "partly_cloudy"

def test_wmo_foggy():
    assert _wmo_to_condition(45) == "foggy"
    assert _wmo_to_condition(48) == "foggy"

def test_wmo_drizzle():
    for code in (51, 55, 61, 65, 67):
        assert _wmo_to_condition(code) == "drizzle"

def test_wmo_snow():
    assert _wmo_to_condition(71) == "snow"
    assert _wmo_to_condition(77) == "snow"

def test_wmo_rain_showers():
    for code in (80, 81, 82):
        assert _wmo_to_condition(code) == "rain_showers"

def test_wmo_thunderstorm():
    for code in (95, 96, 99):
        assert _wmo_to_condition(code) == "thunderstorm"

def test_wmo_unknown_returns_partly_cloudy():
    assert _wmo_to_condition(999) == "partly_cloudy"


# ── Rule engine — heatwave ────────────────────────────────────────────────────

def test_heatwave_triggered_on_two_consecutive_hot_days():
    forecast = [_day(temp_max=39)] * 7
    alerts = _apply_rules(forecast)
    types = [a["type"] for a in alerts]
    assert "heatwave" in types

def test_heatwave_not_triggered_on_single_hot_day():
    forecast = [_day(temp_max=39)] + [_day()] * 6
    alerts = _apply_rules(forecast)
    assert not any(a["type"] == "heatwave" for a in alerts)

def test_heatwave_not_triggered_below_threshold():
    forecast = [_day(temp_max=37)] * 7
    alerts = _apply_rules(forecast)
    assert not any(a["type"] == "heatwave" for a in alerts)


# ── Rule engine — heavy rain ──────────────────────────────────────────────────

def test_heavy_rain_triggered():
    forecast = [_day(rain_mm=30)] + [_day()] * 6
    alerts = _apply_rules(forecast)
    assert any(a["type"] == "heavy_rain" for a in alerts)

def test_heavy_rain_not_triggered_below_25():
    forecast = [_day(rain_mm=24)] * 7
    alerts = _apply_rules(forecast)
    assert not any(a["type"] == "heavy_rain" for a in alerts)


# ── Rule engine — frost ───────────────────────────────────────────────────────

def test_frost_triggered():
    forecast = [_day(temp_min=2)] + [_day()] * 6
    alerts = _apply_rules(forecast)
    assert any(a["type"] == "frost" for a in alerts)

def test_frost_not_triggered_above_4():
    forecast = [_day(temp_min=5)] * 7
    alerts = _apply_rules(forecast)
    assert not any(a["type"] == "frost" for a in alerts)


# ── Rule engine — drought ─────────────────────────────────────────────────────

def test_drought_triggered():
    forecast = [_day(rain_mm=0, temp_avg=32)] * 7
    alerts = _apply_rules(forecast)
    assert any(a["type"] == "drought" for a in alerts)

def test_drought_not_triggered_enough_rain():
    forecast = [_day(rain_mm=2, temp_avg=32)] * 7  # total = 14mm
    alerts = _apply_rules(forecast)
    assert not any(a["type"] == "drought" for a in alerts)

def test_drought_not_triggered_cool_weather():
    forecast = [_day(rain_mm=0, temp_avg=28)] * 7
    alerts = _apply_rules(forecast)
    assert not any(a["type"] == "drought" for a in alerts)


# ── Rule engine — strong wind ─────────────────────────────────────────────────

def test_strong_wind_triggered():
    forecast = [_day(wind_kmh=50)] + [_day()] * 6
    alerts = _apply_rules(forecast)
    assert any(a["type"] == "strong_wind" for a in alerts)

def test_strong_wind_not_triggered():
    forecast = [_day(wind_kmh=39)] * 7
    alerts = _apply_rules(forecast)
    assert not any(a["type"] == "strong_wind" for a in alerts)


# ── Rule engine — spray delay ─────────────────────────────────────────────────

def test_spray_delay_triggered_day0():
    forecast = [_day(rain_probability=65)] + [_day()] * 6
    alerts = _apply_rules(forecast)
    assert any(a["type"] == "spray_delay" for a in alerts)

def test_spray_delay_triggered_day1():
    forecast = [_day()] + [_day(rain_probability=70)] + [_day()] * 5
    alerts = _apply_rules(forecast)
    assert any(a["type"] == "spray_delay" for a in alerts)

def test_spray_delay_not_triggered_after_day1():
    forecast = [_day()] * 2 + [_day(rain_probability=80)] + [_day()] * 4
    alerts = _apply_rules(forecast)
    assert not any(a["type"] == "spray_delay" for a in alerts)


# ── Rule engine — fungal risk ─────────────────────────────────────────────────

def test_fungal_risk_triggered_three_consecutive_humid_days():
    forecast = [_day(humidity=90)] * 7
    alerts = _apply_rules(forecast)
    assert any(a["type"] == "fungal_risk" for a in alerts)

def test_fungal_risk_not_triggered_two_days():
    forecast = [_day(humidity=90), _day(humidity=90)] + [_day()] * 5
    alerts = _apply_rules(forecast)
    assert not any(a["type"] == "fungal_risk" for a in alerts)


# ── No duplicate alerts ───────────────────────────────────────────────────────

def test_no_duplicate_heatwave_alerts():
    forecast = [_day(temp_max=40)] * 7
    alerts = _apply_rules(forecast)
    assert sum(1 for a in alerts if a["type"] == "heatwave") == 1

def test_no_duplicate_fungal_risk_alerts():
    forecast = [_day(humidity=95)] * 7
    alerts = _apply_rules(forecast)
    assert sum(1 for a in alerts if a["type"] == "fungal_risk") == 1


# ── Planting recommendation ───────────────────────────────────────────────────

def test_suitability_ideal_conditions():
    forecast = [_day(temp_avg=25, rain_mm=3)] * 7
    irrig = {"confidence": 0.8, "water_amount_mm": 20.0}
    rec = _planting_recommendation(forecast, [], irrig)
    assert rec["suitability_score"] > 0.7
    assert rec["risk_level"] == "low"

def test_suitability_low_when_high_alerts():
    forecast = [_day(temp_avg=25)] * 7
    alerts = [{"type": "heatwave", "severity": "high"}]
    rec = _planting_recommendation(forecast, alerts, None)
    assert rec["risk_level"] == "high"
    assert rec["suitability_score"] < 0.85

def test_ideal_date_set_when_suitability_exceeds_threshold():
    forecast = [_day(temp_avg=25, rain_mm=2, date=f"2026-05-{18+i:02d}") for i in range(7)]
    rec = _planting_recommendation(forecast, [], {"confidence": 0.9, "water_amount_mm": 15.0})
    assert rec["ideal_date"] is not None

def test_ideal_date_none_when_all_days_unsuitable():
    forecast = [_day(temp_avg=50, date=f"2026-05-{18+i:02d}") for i in range(7)]
    alerts = [{"type": "heatwave", "severity": "high"}, {"type": "drought", "severity": "medium"}]
    rec = _planting_recommendation(forecast, alerts, None)
    assert rec["ideal_date"] is None

def test_water_requirement_from_irrig_model():
    forecast = [_day()] * 7
    irrig = {"confidence": 0.7, "water_amount_mm": 35.0}
    rec = _planting_recommendation(forecast, [], irrig)
    assert rec["water_requirement_mm"] == 35.0

def test_reasons_list_max_three():
    forecast = [_day()] * 7
    rec = _planting_recommendation(forecast, [], None)
    assert len(rec["reasons"]) <= 3
