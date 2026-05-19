"""
AgroSense Email Alert System
Sends crop stress alerts via Gmail SMTP when diseased/stressed crops are detected.
"""
import smtplib
import os
from email.mime.text import MIMEText
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()


def send_crop_alert(
    analysis_data: dict,
    user_email: str,
    admin_email: str = None,
) -> dict:
    """
    Send a crop stress alert email.

    Args:
        analysis_data : full_analysis API response dict
        user_email    : farmer's email address
        admin_email   : optional admin email (also receives alert)

    Returns:
        dict with "success" bool and "message" str
    """
    smtp_user = os.getenv("GMAIL_USER", "")
    smtp_pass = os.getenv("GMAIL_APP_PASSWORD", "")

    if not smtp_user or not smtp_pass:
        return {
            "success": False,
            "message": "Gmail credentials not configured in .env file"
        }

    stress    = analysis_data.get("crop_stress", {})
    pred      = stress.get("prediction", "Unknown")
    conf      = stress.get("confidence", 0)
    field     = analysis_data.get("field_name", "Unknown Field")
    crop      = analysis_data.get("crop_type", "Unknown")
    irrig     = analysis_data.get("irrigation", {})
    soil      = analysis_data.get("soil_assessment", {})
    yld       = analysis_data.get("yield_prediction", {})
    indices   = analysis_data.get("vegetation_indices", {})

    color_map = {"Healthy": "#1a6b35", "Stressed": "#d4a017", "Diseased": "#dc2626"}
    alert_color = color_map.get(pred, "#6b7280")

    if pred == "Healthy":
        subject      = f"✅ AgroSense Report: {field} crop is Healthy"
        banner_text  = "CROP STATUS: HEALTHY — No immediate action required"
    else:
        subject      = f"🚨 AgroSense Alert: {pred} crop detected in {field}"
        banner_text  = f"⚠  {pred.upper()} CROP DETECTED — Immediate attention required"

    html_body = f"""
<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <style>
    body {{ font-family: 'Segoe UI', Arial, sans-serif; background: #f4f6f4; margin: 0; padding: 20px; }}
    .container {{ max-width: 600px; margin: 0 auto; background: white; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 20px rgba(0,0,0,0.1); }}
    .header {{ background: #0b1f10; color: white; padding: 28px 32px; }}
    .header h1 {{ margin: 0; font-size: 22px; }}
    .header p {{ margin: 6px 0 0; color: #7aaa8a; font-size: 13px; }}
    .alert-banner {{ background: {alert_color}; color: white; padding: 16px 32px; font-size: 15px; font-weight: 600; }}
    .body {{ padding: 28px 32px; }}
    .section {{ margin-bottom: 24px; }}
    .section h3 {{ color: #0b1f10; font-size: 14px; margin: 0 0 12px; border-bottom: 1px solid #e5e7eb; padding-bottom: 6px; }}
    .kv {{ display: flex; justify-content: space-between; padding: 7px 0; font-size: 13px; border-bottom: 1px solid #f3f4f6; }}
    .kv .key {{ color: #6b7280; }}
    .kv .val {{ font-weight: 600; color: #111827; }}
    .badge {{ display: inline-block; background: {alert_color}20; color: {alert_color}; border-radius: 6px; padding: 3px 10px; font-size: 12px; font-weight: 700; }}
    .actions {{ background: #f0fdf4; border: 1px solid #bbf7d0; border-radius: 8px; padding: 16px; margin-top: 20px; }}
    .actions h4 {{ color: #1a6b35; margin: 0 0 8px; font-size: 13px; }}
    .actions ul {{ margin: 0; padding-left: 18px; font-size: 13px; color: #374151; line-height: 1.8; }}
    .footer {{ background: #f9fafb; padding: 16px 32px; font-size: 11px; color: #9ca3af; text-align: center; }}
  </style>
</head>
<body>
<div class="container">
  <div class="header">
    <h1>🌿 AgroSense Alert</h1>
    <p>Satellite-Based Crop Intelligence System</p>
  </div>
  <div class="alert-banner">
    {banner_text}
  </div>
  <div class="body">
    <div class="section">
      <h3>Field Information</h3>
      <div class="kv"><span class="key">Field Name</span><span class="val">{field}</span></div>
      <div class="kv"><span class="key">Crop Type</span><span class="val">{crop.title()}</span></div>
      <div class="kv"><span class="key">Alert Time</span><span class="val">{datetime.now().strftime('%d %B %Y at %H:%M')}</span></div>
    </div>

    <div class="section">
      <h3>🌿 Crop Health Status</h3>
      <div class="kv">
        <span class="key">Status</span>
        <span class="val"><span class="badge">{pred}</span></span>
      </div>
      <div class="kv"><span class="key">Confidence</span><span class="val">{conf*100:.1f}%</span></div>
      <div class="kv"><span class="key">NDVI</span><span class="val">{indices.get('ndvi',0):.3f}</span></div>
      <div class="kv"><span class="key">NDRE</span><span class="val">{indices.get('ndre',0):.3f}</span></div>
    </div>

    <div class="section">
      <h3>💧 Irrigation Status</h3>
      <div class="kv"><span class="key">Recommendation</span><span class="val">{irrig.get('recommendation','—').replace('_',' ').title()}</span></div>
      <div class="kv"><span class="key">Soil Moisture</span><span class="val">{irrig.get('soil_moisture_pct',0):.1f}%</span></div>
      <div class="kv"><span class="key">Water Needed</span><span class="val">{irrig.get('water_amount_mm',0):.1f} mm</span></div>
    </div>

    <div class="section">
      <h3>📈 Yield Forecast</h3>
      <div class="kv"><span class="key">Predicted Yield</span><span class="val">{yld.get('predicted_yield_tha',0):.2f} t/ha</span></div>
      <div class="kv"><span class="key">Harvest Readiness</span><span class="val">{yld.get('harvest_readiness_pct',0):.1f}%</span></div>
    </div>

    <div class="actions">
      <h4>✅ Recommended Actions</h4>
      <ul>
        {"<li>Inspect the field immediately for visible disease symptoms</li>" if pred == "Diseased" else ""}
        {"<li>Apply appropriate fungicide/pesticide treatment</li>" if pred == "Diseased" else "<li>Investigate water or nutrient stress factors</li>"}
        <li>{'Irrigate immediately — soil moisture is critically low' if 'now' in irrig.get('recommendation','') else 'Monitor soil moisture levels closely'}</li>
        <li>Re-run AgroSense analysis in 7 days to track recovery</li>
        <li>Consult an agricultural extension officer if condition worsens</li>
      </ul>
    </div>
  </div>
  <div class="footer">
    This alert was generated automatically by AgroSense · SMIU FYP 2025–2026<br>
    Do not reply to this email · Open AgroSense desktop app for full analysis
  </div>
</div>
</body>
</html>
"""

    recipients = [user_email]
    if admin_email and admin_email != user_email:
        recipients.append(admin_email)

    try:
        from email.message import EmailMessage
        msg = EmailMessage()
        msg["Subject"] = subject
        msg["From"]    = f"AgroSense Alerts <{smtp_user}>"
        msg["To"]      = ", ".join(recipients)
        msg.set_content(html_body, subtype="html")

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(smtp_user, smtp_pass)
            server.sendmail(smtp_user, recipients, msg.as_bytes().decode("utf-8", errors="replace"))

        return {
            "success": True,
            "message": f"Alert sent to {', '.join(recipients)}"
        }
    except Exception as e:
        return {"success": False, "message": str(e)}


def check_and_alert(analysis_data: dict, user: dict, admin_email: str = None) -> dict:
    """Send an email report for any crop status (Healthy, Stressed, or Diseased)."""
    return send_crop_alert(
        analysis_data=analysis_data,
        user_email=user.get("email", ""),
        admin_email=admin_email,
    )
