import sys, os, unittest.mock as mock
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


def _analysis(pred="Healthy"):
    return {
        "crop_stress": {"prediction": pred, "confidence": 0.92, "probabilities": {}},
        "field_name":  "Test Field",
        "crop_type":   "wheat",
        "irrigation":  {"recommendation": "moderate", "soil_moisture_pct": 40.0,
                        "water_amount_mm": 20.0},
        "soil_assessment": {},
        "yield_prediction": {"predicted_yield_tha": 2.4, "harvest_readiness_pct": 70.0},
        "vegetation_indices": {"ndvi": 0.45, "ndre": 0.22},
    }


# ── check_and_alert ───────────────────────────────────────────────────────────

def test_check_and_alert_sends_for_healthy():
    """check_and_alert must call send_crop_alert even when crop is Healthy."""
    from desktop.utils.email_alerts import check_and_alert
    with mock.patch("desktop.utils.email_alerts.send_crop_alert") as m:
        m.return_value = {"success": True, "message": "sent"}
        check_and_alert(_analysis("Healthy"), {"email": "farmer@example.com"})
        m.assert_called_once()


def test_check_and_alert_sends_for_stressed():
    from desktop.utils.email_alerts import check_and_alert
    with mock.patch("desktop.utils.email_alerts.send_crop_alert") as m:
        m.return_value = {"success": True, "message": "sent"}
        check_and_alert(_analysis("Stressed"), {"email": "farmer@example.com"})
        m.assert_called_once()


def test_check_and_alert_sends_for_diseased():
    from desktop.utils.email_alerts import check_and_alert
    with mock.patch("desktop.utils.email_alerts.send_crop_alert") as m:
        m.return_value = {"success": True, "message": "sent"}
        check_and_alert(_analysis("Diseased"), {"email": "farmer@example.com"})
        m.assert_called_once()


# ── send_crop_alert ───────────────────────────────────────────────────────────

def _run_send(pred):
    """Helper: run send_crop_alert with mocked SMTP and env vars."""
    from desktop.utils.email_alerts import send_crop_alert
    with mock.patch.dict(os.environ, {"GMAIL_USER": "bot@gmail.com",
                                      "GMAIL_APP_PASSWORD": "testpass"}):
        with mock.patch("smtplib.SMTP_SSL") as mock_ssl:
            srv = mock.MagicMock()
            mock_ssl.return_value.__enter__.return_value = srv
            result = send_crop_alert(_analysis(pred), "farmer@example.com")
            return result, srv


def test_send_healthy_does_not_return_early():
    result, srv = _run_send("Healthy")
    assert result["success"] is True
    srv.sendmail.assert_called_once()


def test_send_healthy_subject_contains_healthy():
    from desktop.utils.email_alerts import send_crop_alert
    captured = {}
    def fake_sendmail(frm, to, msg_str):
        captured["msg"] = msg_str
    with mock.patch.dict(os.environ, {"GMAIL_USER": "bot@gmail.com",
                                      "GMAIL_APP_PASSWORD": "testpass"}):
        with mock.patch("smtplib.SMTP_SSL") as mock_ssl:
            srv = mock.MagicMock()
            srv.sendmail.side_effect = fake_sendmail
            mock_ssl.return_value.__enter__.return_value = srv
            send_crop_alert(_analysis("Healthy"), "farmer@example.com")
    assert "Healthy" in captured["msg"]
    assert "🚨" not in captured["msg"]


def test_send_diseased_subject_contains_alert_emoji():
    from desktop.utils.email_alerts import send_crop_alert
    captured = {}
    def fake_sendmail(frm, to, msg_str):
        captured["msg"] = msg_str
    with mock.patch.dict(os.environ, {"GMAIL_USER": "bot@gmail.com",
                                      "GMAIL_APP_PASSWORD": "testpass"}):
        with mock.patch("smtplib.SMTP_SSL") as mock_ssl:
            srv = mock.MagicMock()
            srv.sendmail.side_effect = fake_sendmail
            mock_ssl.return_value.__enter__.return_value = srv
            send_crop_alert(_analysis("Diseased"), "farmer@example.com")
    # Check for emoji in HTML body (Subject may be RFC 2047 encoded in MIME messages)
    assert "🚨" in captured["msg"] or "alert-banner" in captured["msg"]
