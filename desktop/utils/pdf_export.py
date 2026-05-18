"""AgroSense PDF Report — v3 (EN/UR bilingual)"""
from datetime import datetime
import io

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table,
    TableStyle, HRFlowable, Image, PageBreak
)
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase.pdfmetrics import registerFontFamily

C_GREEN  = colors.HexColor("#1a6b35")
C_DARK   = colors.HexColor("#0b1f10")
C_GOLD   = colors.HexColor("#d4a017")
C_BLUE   = colors.HexColor("#2563eb")
C_RED    = colors.HexColor("#dc2626")
C_PURPLE = colors.HexColor("#7c3aed")
C_MUTED  = colors.HexColor("#6b7280")
C_BORDER = colors.HexColor("#e2e8e4")
C_WHITE  = colors.white
C_LIGHT  = colors.HexColor("#f0fdf4")

_UR_FONTS_REGISTERED = False

def _register_urdu_fonts():
    global _UR_FONTS_REGISTERED
    if _UR_FONTS_REGISTERED:
        return
    pdfmetrics.registerFont(TTFont(
        'NastaliqUrdu',
        '/usr/share/fonts/truetype/noto/NotoNastaliqUrdu-Regular.ttf'))
    pdfmetrics.registerFont(TTFont(
        'NastaliqUrdu-Bold',
        '/usr/share/fonts/truetype/noto/NotoNastaliqUrdu-Bold.ttf'))
    registerFontFamily('NastaliqUrdu',
                       normal='NastaliqUrdu', bold='NastaliqUrdu-Bold',
                       italic='NastaliqUrdu', boldItalic='NastaliqUrdu-Bold')
    _UR_FONTS_REGISTERED = True


def _ur(text):
    """Reshape + bidi-reorder Urdu text for ReportLab."""
    import arabic_reshaper
    from bidi.algorithm import get_display
    return get_display(arabic_reshaper.reshape(str(text)))


# Urdu translations used in the PDF
_UR = {
    # header / title
    "tagline":          "سیٹلائٹ بنیاد فصل انٹیلیجنس نظام",
    "generated":        "تیار کردہ",
    "report_title":     "فیلڈ تجزیہ رپورٹ",
    # summary banner
    "health":           "صحت",
    "irrigation":       "آبپاشی",
    "est_yield":        "متوقع پیداوار",
    "vra_zone":         "VRA زون",
    # section headings
    "sec1": "سبزینہ اشاریے (سینٹینل-2)",
    "sec2": "فصل صحت تشخیص",
    "sec3": "آبپاشی سفارش",
    "sec4": "پیداوار کی پیش گوئی",
    "sec5": "مٹی کی صورتحال",
    "sec6": "متغیر شرح اطلاق (VRA)",
    "sec7": "سیٹلائٹ بینڈ کمپوزٹ (سینٹینل-2)",
    # table column headers
    "index":            "اشاریہ",
    "value":            "قدر",
    "threshold":        "حد",
    "visual_bar":       "بار",
    "status":           "حالت",
    "parameter":        "پیرامیٹر",
    "class":            "قسم",
    "probability":      "امکان",
    "conf_bar":         "اعتماد بار",
    # index status
    "good":             "اچھا ✓",
    "fair":             "معتدل ~",
    "low":              "کم ✗",
    # index definitions (kept concise)
    "ndvi_def":  "NDVI — فصل کی کثافت اور صحت کا اشاریہ۔ زیادہ = گھنی صحت مند فصل",
    "evi_def":   "EVI — فضائی اثرات اور مٹی کی پس منظر کی اصلاح کے ساتھ NDVI",
    "ndwi_def":  "NDWI — فصل اور مٹی میں پانی کی مقدار — کم منفی = بہتر نمی",
    "ndre_def":  "NDRE — ریڈ ایج بینڈ سے کلوروفل کا پتہ — NDVI سے پہلے دباؤ ظاہر کرتا ہے",
    "lai_def":   "LAI — فی یونٹ زمین پر کل پتوں کا رقبہ (m²/m²) — زیادہ = گھنی فصل",
    "status_def":"اچھا ✓: ہدف پورا | معتدل ~: نگرانی ضروری | کم ✗: فوری توجہ",
    # irrigation params
    "recommendation":   "سفارش",
    "soil_moisture":    "مٹی کی نمی",
    "water_needed":     "پانی کی ضرورت",
    "confidence":       "اعتماد",
    # yield params
    "pred_yield":       "متوقع پیداوار",
    "lower_bound":      "نچلی حد (95%)",
    "upper_bound":      "اوپری حد (95%)",
    "harvest":          "کٹائی کی تیاری",
    # soil params
    "soil_ph":          "مٹی pH",
    "salinity":         "نمکینیت",
    "organic":          "نامیاتی مادہ",
    # VRA params
    "fert_zone":        "زرخیزی زون",
    "fert_rec":         "کھاد کی سفارش",
    # crop health labels
    "prediction":       "پیشین گوئی",
    "Healthy":          "صحت مند",
    "Stressed":         "دباؤ میں",
    "Diseased":         "بیمار",
    # band section
    "band_note":        "گوگل ارتھ انجن سے حقیقی تصاویر · فیلڈ کے ارد گرد 4 کلومیٹر × 4 کلومیٹر",
    "no_bands":         "کوئی بینڈ تصاویر دستیاب نہیں۔",
    # footer
    "footer":           "AgroSense — SMIU فائنل ایئر پروجیکٹ 2025–2026 · سینٹینل-2 تصاویر گوگل ارتھ انجن · ML ماڈلز پاکستانی زرعی ڈیٹا · صرف رہنمائی کے لیے",
    # ndvi status
    "ndvi_good":        "اچھا 🟢",
    "ndvi_mod":         "معتدل 🟡",
    "ndvi_low":         "کم 🔴",
}


def S(n, **k): return ParagraphStyle(n, **k)


def _tbl(data, cols, extras=None, font="Helvetica", bold_font="Helvetica-Bold", align=TA_LEFT):
    t = Table(data, colWidths=cols)
    s = [
        ("BACKGROUND", (0, 0), (-1, 0), C_DARK),
        ("TEXTCOLOR", (0, 0), (-1, 0), C_WHITE),
        ("FONTNAME", (0, 0), (-1, 0), bold_font),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [C_LIGHT, C_WHITE]),
        ("GRID", (0, 0), (-1, -1), 0.5, C_BORDER),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("LEFTPADDING", (0, 0), (-1, -1), 12),
    ]
    if align == TA_RIGHT:
        s.append(("ALIGN", (0, 0), (-1, -1), "RIGHT"))
        s.append(("RIGHTPADDING", (0, 0), (-1, -1), 12))
    if extras:
        s += extras
    t.setStyle(TableStyle(s))
    return t


def _fetch_bands(fid, start, end, tok):
    try:
        import requests
        h = {"Authorization": f"Bearer {tok}"}
        out = {}
        for bt, lbl in [
            ("agriculture", "Agriculture Composite (B11+B8+B2)"),
            ("vegetation",  "Vegetation Analysis (B8A+B4+B3)"),
            ("ndre",        "NDRE Visualization (B5+B4+B3)"),
            ("truecolor",   "True Color RGB (B4+B3+B2)"),
            ("falsecolor",  "False Color NIR (B8+B4+B3)"),
            ("ndvi",        "NDVI Colormap"),
        ]:
            try:
                r = requests.get(
                    f"http://localhost:8000/imagery/field/{fid}/bands/{bt}",
                    params={"start_date": start, "end_date": end},
                    headers=h, timeout=90)
                if r.status_code == 200:
                    out[lbl] = r.content
            except:
                pass
        return out
    except:
        return {}


def generate_report(analysis_data, output_path, user=None, include_bands=True, language="en"):
    is_ur = (language == "ur")
    if is_ur:
        _register_urdu_fonts()

    fn      = "NastaliqUrdu"      if is_ur else "Helvetica"
    fn_bold = "NastaliqUrdu-Bold" if is_ur else "Helvetica-Bold"
    fn_mono = "NastaliqUrdu"      if is_ur else "Courier"
    fs_body = 11  if is_ur else 9
    fs_hdr  = 13  if is_ur else 12
    fs_ttl  = 24  if is_ur else 22
    fs_sub  = 13  if is_ur else 11
    fs_sm   = 9   if is_ur else 7
    align   = TA_RIGHT if is_ur else TA_LEFT

    def T(key):
        """Return Urdu or English label."""
        if is_ur:
            return _ur(_UR.get(key, key))
        en_map = {
            "tagline":       "Satellite-Based Crop Intelligence System",
            "generated":     "Generated",
            "report_title":  "Field Analysis Report",
            "health":        "Health",
            "irrigation":    "Irrigation",
            "est_yield":     "Est. Yield",
            "vra_zone":      "VRA Zone",
            "sec1":          "1. Vegetation Indices (Sentinel-2)",
            "sec2":          "2. Crop Health Assessment",
            "sec3":          "3. Irrigation Recommendation",
            "sec4":          "4. Yield Prediction",
            "sec5":          "5. Soil Condition Assessment",
            "sec6":          "6. Variable Rate Application (VRA)",
            "sec7":          "7. Satellite Band Composites (Sentinel-2)",
            "index":         "Index",
            "value":         "Value",
            "threshold":     "Threshold",
            "visual_bar":    "Visual Bar",
            "status":        "Status",
            "parameter":     "Parameter",
            "class":         "Class",
            "probability":   "Probability",
            "conf_bar":      "Confidence Bar",
            "good":          "✓ Good",
            "fair":          "~ Fair",
            "low":           "✗ Low",
            "ndvi_def":      "NDVI — Normalized Difference Vegetation Index — measures green vegetation density and overall crop health. Higher = denser, healthier canopy.",
            "evi_def":       "EVI — Enhanced Vegetation Index — like NDVI but corrects for atmospheric haze and soil background.",
            "ndwi_def":      "NDWI — Normalized Difference Water Index — measures water content in vegetation and soil.",
            "ndre_def":      "NDRE — Normalized Difference Red Edge — detects chlorophyll using Sentinel-2 red-edge band.",
            "lai_def":       "LAI — Leaf Area Index — total one-sided leaf area per unit ground area (m²/m²).",
            "status_def":    "✓ Good: meets healthy target  |  ~ Fair: above critical threshold  |  ✗ Low: below threshold",
            "recommendation":"Recommendation",
            "soil_moisture": "Soil Moisture",
            "water_needed":  "Water Needed",
            "confidence":    "Confidence",
            "pred_yield":    "Predicted Yield",
            "lower_bound":   "Lower Bound (95%)",
            "upper_bound":   "Upper Bound (95%)",
            "harvest":       "Harvest Readiness",
            "soil_ph":       "Soil pH",
            "salinity":      "Salinity",
            "organic":       "Organic Matter",
            "fert_zone":     "Fertility Zone",
            "fert_rec":      "Fertiliser Recommendation",
            "prediction":    "Prediction",
            "Healthy":       "Healthy",
            "Stressed":      "Stressed",
            "Diseased":      "Diseased",
            "band_note":     "Real imagery from Google Earth Engine · 4km × 4km area around field",
            "no_bands":      "No band images available.",
            "footer":        "Generated by AgroSense — SMIU Final Year Project 2025–2026 · Sentinel-2 imagery via Google Earth Engine · ML models trained on Pakistan agricultural data · Advisory use only.",
            "ndvi_good":     "🟢 Good",
            "ndvi_mod":      "🟡 Moderate",
            "ndvi_low":      "🔴 Low",
        }
        return en_map.get(key, key)

    def P(text, style): return Paragraph(text, style)

    def h2(txt):
        return P(txt, S("h2", fontSize=fs_hdr, textColor=C_GREEN,
                         fontName=fn_bold, spaceAfter=6, spaceBefore=10,
                         alignment=align))

    doc = SimpleDocTemplate(output_path, pagesize=A4,
                            leftMargin=1.8*cm, rightMargin=1.8*cm,
                            topMargin=1.5*cm, bottomMargin=1.5*cm)
    story = []
    W = A4[0] - 3.6*cm

    d     = analysis_data
    idx   = d.get("vegetation_indices", {})
    stress= d.get("crop_stress", {})
    irrig = d.get("irrigation", {})
    yld   = d.get("yield_prediction", {})
    soil  = d.get("soil_assessment", {})
    vra   = d.get("vra_zones", {})
    pred  = stress.get("prediction", "—")
    conf  = stress.get("confidence", 0)
    sc    = {"Healthy": C_GREEN, "Stressed": C_GOLD, "Diseased": C_RED}.get(pred, C_MUTED)
    now   = datetime.now().strftime("%d %B %Y  %H:%M")
    if is_ur:
        now_txt = _ur(f"{T('generated')}: {now}")
    else:
        now_txt = f"{T('generated')}: {now}"
    field = d.get("field_name") or "Field"
    crop  = (d.get("crop_type") or "").title()
    pred_label = T(pred) if pred in ("Healthy", "Stressed", "Diseased") else pred

    # ── HEADER ────────────────────────────────────────────────────────────────
    tagline_txt = _ur(T("tagline")) if is_ur else T("tagline")
    hdr = Table([[
        P(f"<font color='#ffffff' size='18'><b>🌿 AgroSense</b></font><br/>"
          f"<font color='#86efac' size='9'>{tagline_txt}</font>",
          S("hh", fontSize=18, textColor=C_WHITE, fontName=fn_bold, leading=28)),
        P(f"<font color='#86efac' size='9'><b>SMIU FYP 2025–2026</b></font><br/>"
          f"<font color='#86efac' size='8'>{now_txt}</font>",
          S("hr", fontSize=9, textColor=C_WHITE, fontName=fn,
            alignment=TA_RIGHT if not is_ur else TA_LEFT, leading=16)),
    ]], colWidths=[W*0.60, W*0.40])
    hdr.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), C_DARK),
        ("TOPPADDING", (0, 0), (-1, -1), 18), ("BOTTOMPADDING", (0, 0), (-1, -1), 18),
        ("LEFTPADDING", (0, 0), (0, -1), 20), ("RIGHTPADDING", (-1, 0), (-1, -1), 16),
    ]))
    story += [hdr, Spacer(1, 0.5*cm)]

    # Title
    ttl = _ur(T("report_title")) if is_ur else T("report_title")
    story.append(P(ttl, S("t", fontSize=fs_ttl, fontName=fn_bold,
                           textColor=C_DARK, spaceAfter=8, leading=32, alignment=align)))
    field_line = f"{field}  ·  {crop}  ·  {now}"
    if is_ur:
        field_line = _ur(field_line)
    story.append(P(field_line,
                   S("s", fontSize=fs_sub, fontName=fn, textColor=C_MUTED,
                     spaceAfter=4, alignment=align)))
    story.append(HRFlowable(width="100%", thickness=3, color=C_GREEN, spaceAfter=14))

    # ── SUMMARY BANNER ────────────────────────────────────────────────────────
    ndvi_v = idx.get("ndvi") or 0
    ndvi_status = T("ndvi_good") if ndvi_v > 0.25 else T("ndvi_mod") if ndvi_v > 0.15 else T("ndvi_low")
    if is_ur:
        ndvi_status = _ur(ndvi_status)
    irr_txt = irrig.get("recommendation", "—").replace("_", " ").title()

    def banner_cell(label_key, main_val, color_hex):
        lbl_txt = _ur(T(label_key)) if is_ur else T(label_key)
        val_txt = _ur(str(main_val)) if is_ur else str(main_val)
        return P(
            f"<b>{lbl_txt}</b><br/>"
            f"<font size='{'13' if is_ur else '14'}' color='{color_hex}'>{val_txt}</font>",
            S("bc", fontSize=fs_body, textColor=C_WHITE, fontName=fn,
              leading=22, alignment=TA_CENTER))

    banner_items = [
        banner_cell("health", pred_label, "#1a6b35" if pred == "Healthy" else "#dc2626" if pred == "Diseased" else "#d4a017"),
        banner_cell("ndvi_good" if ndvi_v > 0.25 else "ndvi_mod" if ndvi_v > 0.15 else "ndvi_low",
                    f"{ndvi_v:.3f}", "#86efac"),
        banner_cell("irrigation", irr_txt, "#93c5fd"),
        banner_cell("est_yield", f"{yld.get('predicted_yield_tha', 0):.2f} t/ha", "#c4b5fd"),
        banner_cell("vra_zone", vra.get("zone", "—"), "#86efac"),
    ]
    banner = Table([banner_items], colWidths=[W/5]*5)
    banner.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), C_DARK),
        ("TOPPADDING", (0, 0), (-1, -1), 12), ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
        ("LINEAFTER", (0, 0), (3, -1), 0.5, colors.HexColor("#1a3a24")),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    story += [banner, Spacer(1, 0.5*cm)]

    # ── 1. VEGETATION INDICES ─────────────────────────────────────────────────
    story.append(h2(T("sec1")))

    def idx_status(v, good, warn):
        if v >= good: return T("good")
        if v >= warn: return T("fair")
        return T("low")

    hdr_row = [T("index"), T("value"), T("threshold"), T("visual_bar"), T("status")]
    if is_ur:
        hdr_row = [_ur(c) for c in hdr_row]
    rows = [hdr_row]
    for name, key, good, warn in [
        ("NDVI", "ndvi", 0.25, 0.15), ("EVI", "evi", 0.18, 0.10),
        ("NDWI", "ndwi", -0.20, -0.28), ("NDRE", "ndre", 0.15, 0.08),
        ("LAI",  "lai",  0.45,  0.25),
    ]:
        v = idx.get(key) or 0
        pct = min(1.0, max(0, (v - (-0.5)) / (1.0 - (-0.5))))
        filled = int(pct * 25)
        bar = "█" * filled + "-" * (25 - filled)
        st = idx_status(v, good, warn)
        if is_ur:
            st = _ur(st)
        rows.append([name, f"{v:.4f}", f">{warn:.2f}", bar, st])
    it = Table(rows, colWidths=[W*0.10, W*0.12, W*0.13, W*0.48, W*0.17])
    it.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), C_DARK), ("TEXTCOLOR", (0, 0), (-1, 0), C_WHITE),
        ("FONTNAME", (0, 0), (-1, 0), fn_bold), ("FONTSIZE", (0, 0), (-1, -1), fs_body),
        ("FONTNAME", (3, 1), (3, -1), fn_mono), ("FONTSIZE", (3, 1), (3, -1), 7),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [C_LIGHT, C_WHITE]),
        ("GRID", (0, 0), (-1, -1), 0.5, C_BORDER),
        ("TOPPADDING", (0, 0), (-1, -1), 7), ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        *([("ALIGN", (0, 0), (-1, -1), "RIGHT"), ("RIGHTPADDING", (0, 0), (-1, -1), 8)]
          if is_ur else []),
    ]))
    story += [it, Spacer(1, 0.25*cm)]

    # Index definitions
    defs_data = [
        ("NDVI", "ndvi_def"), ("EVI", "evi_def"), ("NDWI", "ndwi_def"),
        ("NDRE", "ndre_def"), ("LAI",  "lai_def"),
        (T("status") if not is_ur else _ur(T("status")), "status_def"),
    ]
    defs = []
    for abbr, def_key in defs_data:
        def_txt = _ur(T(def_key)) if is_ur else T(def_key)
        defs.append([abbr, def_txt])
    dt = Table(defs, colWidths=[W*0.10, W*0.90])
    dt.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (0, -1), fn_bold),
        ("FONTSIZE", (0, 0), (-1, -1), fs_sm),
        ("FONTNAME", (1, 0), (1, -1), fn),
        ("TEXTCOLOR", (0, 0), (0, -2), C_GREEN),
        ("TEXTCOLOR", (0, -1), (0, -1), C_MUTED), ("TEXTCOLOR", (1, -1), (1, -1), C_MUTED),
        ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("LINEBELOW", (0, -1), (-1, -1), 0.5, C_BORDER),
        ("BACKGROUND", (0, -1), (-1, -1), C_LIGHT),
        *([("ALIGN", (0, 0), (-1, -1), "RIGHT"), ("RIGHTPADDING", (0, 0), (-1, -1), 8)]
          if is_ur else []),
    ]))
    story += [dt, Spacer(1, 0.4*cm)]

    # ── 2. CROP HEALTH ────────────────────────────────────────────────────────
    story.append(h2(T("sec2")))
    probs = stress.get("probabilities", {})
    ch_hdr = [T("class"), T("probability"), T("conf_bar")]
    if is_ur:
        ch_hdr = [_ur(c) for c in ch_hdr]
    hrows = [ch_hdr]
    for cls, p in probs.items():
        filled = int(p * 35)
        bar = "█" * filled + "-" * (35 - filled)
        cls_lbl = T(cls) if cls in ("Healthy", "Stressed", "Diseased") else cls
        if is_ur:
            cls_lbl = _ur(cls_lbl)
        hrows.append([cls_lbl, f"{p*100:.1f}%", bar])
    ht = Table(hrows, colWidths=[W*0.25, W*0.15, W*0.60])
    ht.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), C_DARK), ("TEXTCOLOR", (0, 0), (-1, 0), C_WHITE),
        ("FONTNAME", (0, 0), (-1, 0), fn_bold), ("FONTSIZE", (0, 0), (-1, -1), fs_body),
        ("FONTNAME", (2, 1), (2, -1), fn_mono), ("FONTSIZE", (2, 1), (2, -1), 8),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [C_LIGHT, C_WHITE, C_LIGHT]),
        ("GRID", (0, 0), (-1, -1), 0.5, C_BORDER),
        ("TOPPADDING", (0, 0), (-1, -1), 7), ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("TEXTCOLOR", (0, 1), (0, 1), sc), ("FONTNAME", (0, 1), (0, 1), fn_bold),
        *([("ALIGN", (0, 0), (-1, -1), "RIGHT"), ("RIGHTPADDING", (0, 0), (-1, -1), 10)]
          if is_ur else []),
    ]))
    pred_txt = _ur(f"{T('prediction')}: {pred_label}  ({T('confidence')}: {conf*100:.1f}%)") \
               if is_ur else \
               f"<b>{T('prediction')}: {pred_label}</b>  ({T('confidence')}: {conf*100:.1f}%)"
    story.append(P(pred_txt,
                   S("cp", fontSize=fs_body, textColor=sc, fontName=fn_bold,
                     spaceAfter=4, alignment=align)))
    story += [ht, Spacer(1, 0.4*cm)]

    # ── 3. IRRIGATION ─────────────────────────────────────────────────────────
    story.append(h2(T("sec3")))

    def make_kv(pairs, col_widths, extras=None):
        rows = [[T("parameter"), T("value")]]
        if is_ur:
            rows = [[_ur(T("parameter")), _ur(T("value"))]]
        for k, v in pairs:
            k_txt = _ur(k) if is_ur else k
            v_txt = _ur(str(v)) if is_ur else str(v)
            rows.append([k_txt, v_txt])
        return _tbl(rows, col_widths, extras,
                    font=fn, bold_font=fn_bold, align=align)

    story.append(make_kv([
        (T("recommendation"), irrig.get("recommendation", "—").replace("_", " ").title()),
        (T("soil_moisture"),  f"{irrig.get('soil_moisture_pct', 0):.1f}%"),
        (T("water_needed"),   f"{irrig.get('water_amount_mm', 0):.1f} mm"),
        (T("confidence"),     f"{irrig.get('confidence', 0)*100:.0f}%"),
    ], [W*0.40, W*0.60],
        [("TEXTCOLOR", (1, 1), (1, 1), C_BLUE), ("FONTNAME", (1, 1), (1, 1), fn_bold)]))
    story.append(Spacer(1, 0.4*cm))

    # ── 4. YIELD ──────────────────────────────────────────────────────────────
    story.append(h2(T("sec4")))
    story.append(make_kv([
        (T("pred_yield"),  f"{yld.get('predicted_yield_tha', 0):.3f} t/ha"),
        (T("lower_bound"), f"{yld.get('yield_lower_bound', 0):.3f} t/ha"),
        (T("upper_bound"), f"{yld.get('yield_upper_bound', 0):.3f} t/ha"),
        (T("harvest"),     f"{yld.get('harvest_readiness_pct', 0):.1f}%"),
    ], [W*0.40, W*0.60],
        [("TEXTCOLOR", (1, 1), (1, 1), C_PURPLE), ("FONTNAME", (1, 1), (1, 1), fn_bold)]))
    story.append(Spacer(1, 0.4*cm))

    # ── 5. SOIL ───────────────────────────────────────────────────────────────
    story.append(h2(T("sec5")))
    soil_hdr = [T("parameter"), T("value"), T("status")]
    if is_ur:
        soil_hdr = [_ur(c) for c in soil_hdr]
    soil_rows = [soil_hdr,
        [T("soil_ph") if not is_ur else _ur(T("soil_ph")),
         f"{soil.get('soil_ph', 0):.2f}",
         soil.get("ph_status", "—")],
        [T("salinity") if not is_ur else _ur(T("salinity")),
         f"{soil.get('salinity_ds_m', 0):.3f} dS/m",
         soil.get("salinity_status", "—")],
        [T("organic") if not is_ur else _ur(T("organic")),
         f"{soil.get('organic_matter_pct', 0):.3f}%",
         soil.get("organic_matter_status", "—")],
    ]
    story.append(_tbl(soil_rows, [W*0.35, W*0.30, W*0.35],
                      font=fn, bold_font=fn_bold, align=align))
    story.append(Spacer(1, 0.4*cm))

    # ── 6. VRA ────────────────────────────────────────────────────────────────
    story.append(h2(T("sec6")))
    story.append(make_kv([
        (T("fert_zone"), vra.get("zone", "—")),
        (T("fert_rec"),  vra.get("fertiliser_recommendation", "—")),
        (T("confidence"), f"{vra.get('confidence', 0)*100:.0f}%"),
    ], [W*0.40, W*0.60],
        [("TEXTCOLOR", (1, 1), (1, 1), C_GREEN), ("FONTNAME", (1, 1), (1, 1), fn_bold)]))

    # ── 7. BAND COMPOSITES ────────────────────────────────────────────────────
    fid   = d.get("field_id")
    tok   = d.get("_token")
    start = d.get("_start_date", "2024-01-01")
    end   = d.get("_end_date",   "2024-03-01")

    if fid and tok and include_bands:
        story.append(PageBreak())
        story.append(h2(T("sec7")))
        note_txt = _ur(T("band_note")) if is_ur else T("band_note")
        story.append(P(note_txt,
                       S("d", fontSize=fs_sm, fontName=fn,
                         textColor=C_MUTED, spaceAfter=10, alignment=align)))
        descs = {
            "Agriculture Composite (B11+B8+B2)": "SWIR+NIR+Blue — crops=bright green, soil=brown",
            "Vegetation Analysis (B8A+B4+B3)":   "Narrow NIR — canopy density and plant health",
            "NDRE Visualization (B5+B4+B3)":     "Red Edge — late season, avoids NDVI saturation",
            "True Color RGB (B4+B3+B2)":         "Natural color as seen by the human eye",
            "False Color NIR (B8+B4+B3)":        "NIR composite — healthy vegetation=bright red",
            "NDVI Colormap":                     "Green=healthy · Orange/Red=stressed · Grey=bare soil",
        }
        bands = _fetch_bands(fid, start, end, tok)
        if bands:
            iw = (W - 0.6*cm) / 2
            ih = iw * 0.72
            items = list(bands.items())
            for i in range(0, len(items), 2):
                row = []
                for j in range(2):
                    if i + j < len(items):
                        band_lbl, png = items[i + j]
                        img = Image(io.BytesIO(png), width=iw, height=ih)
                        desc_txt = descs.get(band_lbl, "")
                        c = Table([
                            [P(f"<b>{band_lbl}</b>",
                               S("bl", fontSize=8, fontName=fn_bold,
                                 textColor=C_GREEN))],
                            [img],
                            [P(desc_txt,
                               S("bd", fontSize=7, fontName=fn,
                                 textColor=C_MUTED, leading=10))],
                        ], colWidths=[iw])
                        c.setStyle(TableStyle([
                            ("BACKGROUND", (0, 0), (-1, 0), C_LIGHT),
                            ("TOPPADDING", (0, 0), (-1, -1), 5),
                            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                            ("LEFTPADDING", (0, 0), (-1, -1), 6),
                            ("GRID", (0, 0), (-1, -1), 0.5, C_BORDER),
                        ]))
                        row.append(c)
                    else:
                        row.append(Spacer(iw, ih))
                rt = Table([row], colWidths=[iw + 0.3*cm, iw + 0.3*cm])
                rt.setStyle(TableStyle([
                    ("LEFTPADDING", (0, 0), (-1, -1), 0),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                    ("TOPPADDING", (0, 0), (-1, -1), 0),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ]))
                story.append(rt)
        else:
            no_bands_txt = _ur(T("no_bands")) if is_ur else T("no_bands")
            story.append(P(no_bands_txt,
                           S("na", fontSize=fs_body, fontName=fn, textColor=C_MUTED)))

    # ── FOOTER ────────────────────────────────────────────────────────────────
    story += [Spacer(1, 0.6*cm),
              HRFlowable(width="100%", thickness=1, color=C_BORDER),
              Spacer(1, 0.2*cm)]
    footer_txt = _ur(T("footer")) if is_ur else T("footer")
    story.append(P(footer_txt,
                   S("ft", fontSize=7.5, fontName=fn,
                     textColor=C_MUTED, alignment=TA_CENTER, leading=11)))

    doc.build(story)
    return output_path
