"""AgroSense PDF Report - Professional Version v2"""
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
from reportlab.lib.enums import TA_CENTER, TA_RIGHT

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

def S(n,**k): return ParagraphStyle(n,**k)

def _tbl(data,cols,extras=None):
    t=Table(data,colWidths=cols)
    s=[("BACKGROUND",(0,0),(-1,0),C_DARK),("TEXTCOLOR",(0,0),(-1,0),C_WHITE),
       ("FONTNAME",(0,0),(-1,0),"Helvetica-Bold"),("FONTSIZE",(0,0),(-1,-1),9),
       ("ROWBACKGROUNDS",(0,1),(-1,-1),[C_LIGHT,C_WHITE]),
       ("GRID",(0,0),(-1,-1),0.5,C_BORDER),
       ("TOPPADDING",(0,0),(-1,-1),8),("BOTTOMPADDING",(0,0),(-1,-1),8),
       ("LEFTPADDING",(0,0),(-1,-1),12)]
    if extras: s+=extras
    t.setStyle(TableStyle(s)); return t

def _h2(txt): return Paragraph(txt,S("h2",fontSize=12,textColor=C_GREEN,
    fontName="Helvetica-Bold",spaceAfter=6,spaceBefore=10))

def _fetch_bands(fid,start,end,tok):
    try:
        import requests
        h={"Authorization":f"Bearer {tok}"}
        out={}
        for bt,lbl in [("agriculture","Agriculture Composite (B11+B8+B2)"),
                        ("vegetation","Vegetation Analysis (B8A+B4+B3)"),
                        ("ndre","NDRE Visualization (B5+B4+B3)"),
                        ("truecolor","True Color RGB (B4+B3+B2)"),
                        ("falsecolor","False Color NIR (B8+B4+B3)"),
                        ("ndvi","NDVI Colormap")]:
            try:
                r=requests.get(f"http://localhost:8000/imagery/field/{fid}/bands/{bt}",
                    params={"start_date":start,"end_date":end},headers=h,timeout=90)
                if r.status_code==200: out[lbl]=r.content
            except: pass
        return out
    except: return {}

def generate_report(analysis_data, output_path, user=None, include_bands=True):
    doc=SimpleDocTemplate(output_path,pagesize=A4,
        leftMargin=1.8*cm,rightMargin=1.8*cm,topMargin=1.5*cm,bottomMargin=1.5*cm)
    story=[]; W=A4[0]-3.6*cm

    d=analysis_data
    idx=d.get("vegetation_indices",{})
    stress=d.get("crop_stress",{})
    irrig=d.get("irrigation",{})
    yld=d.get("yield_prediction",{})
    soil=d.get("soil_assessment",{})
    vra=d.get("vra_zones",{})
    pred=stress.get("prediction","—")
    conf=stress.get("confidence",0)
    sc={"Healthy":C_GREEN,"Stressed":C_GOLD,"Diseased":C_RED}.get(pred,C_MUTED)
    now=datetime.now().strftime("%d %B %Y  %H:%M")
    field=d.get("field_name") or "Field"
    crop=(d.get("crop_type") or "").title()

    # ── HEADER ────────────────────────────────────────────────────────────────
    hdr=Table([[
        Paragraph("<font color='#ffffff' size='18'><b>🌿 AgroSense</b></font><br/>"
            "<font color='#86efac' size='9'>Satellite-Based Crop Intelligence System</font>",
            S("hh",fontSize=18,textColor=C_WHITE,fontName="Helvetica-Bold",leading=26)),
        Paragraph(f"<font color='#86efac' size='9'><b>SMIU FYP 2025–2026</b></font><br/>"
            f"<font color='#86efac' size='8'>Generated: {now}</font>",
            S("hr",fontSize=9,textColor=C_WHITE,alignment=TA_RIGHT,leading=16)),
    ]],colWidths=[W*0.60,W*0.40])
    hdr.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,-1),C_DARK),
        ("TOPPADDING",(0,0),(-1,-1),18),("BOTTOMPADDING",(0,0),(-1,-1),18),
        ("LEFTPADDING",(0,0),(0,-1),20),("RIGHTPADDING",(-1,0),(-1,-1),16)]))
    story+=[hdr,Spacer(1,0.5*cm)]

    # Title
    story.append(Paragraph("Field Analysis Report",
        S("t",fontSize=22,fontName="Helvetica-Bold",textColor=C_DARK,spaceAfter=8,leading=28)))
    story.append(Paragraph(f"<b>{field}</b>  ·  {crop}  ·  {now}",
        S("s",fontSize=11,textColor=C_MUTED,spaceAfter=4)))
    story.append(HRFlowable(width="100%",thickness=3,color=C_GREEN,spaceAfter=14))

    # ── SUMMARY BANNER ────────────────────────────────────────────────────────
    ndvi_v=idx.get('ndvi') or 0
    ndvi_status="🟢 Good" if ndvi_v>0.25 else "🟡 Moderate" if ndvi_v>0.15 else "🔴 Low"
    irr_txt=irrig.get("recommendation","—").replace("_"," ").title()
    banner=Table([[
        Paragraph(f"<b>Health</b><br/><font size='14' color='{'#1a6b35' if pred=='Healthy' else '#dc2626' if pred=='Diseased' else '#d4a017'}'>{pred}</font>",
            S("b1",fontSize=9,textColor=C_WHITE,leading=20,alignment=TA_CENTER)),
        Paragraph(f"<b>NDVI</b><br/><font size='14' color='#86efac'>{ndvi_v:.3f}</font><br/><font size='8'>{ndvi_status}</font>",
            S("b2",fontSize=9,textColor=C_WHITE,leading=18,alignment=TA_CENTER)),
        Paragraph(f"<b>Irrigation</b><br/><font size='11' color='#93c5fd'>{irr_txt}</font>",
            S("b3",fontSize=9,textColor=C_WHITE,leading=18,alignment=TA_CENTER)),
        Paragraph(f"<b>Est. Yield</b><br/><font size='14' color='#c4b5fd'>{yld.get('predicted_yield_tha',0):.2f} t/ha</font>",
            S("b4",fontSize=9,textColor=C_WHITE,leading=18,alignment=TA_CENTER)),
        Paragraph(f"<b>VRA Zone</b><br/><font size='14' color='#86efac'>{vra.get('zone','—')}</font>",
            S("b5",fontSize=9,textColor=C_WHITE,leading=18,alignment=TA_CENTER)),
    ]],colWidths=[W/5]*5)
    banner.setStyle(TableStyle([
        ("BACKGROUND",(0,0),(-1,-1),C_DARK),
        ("TOPPADDING",(0,0),(-1,-1),12),("BOTTOMPADDING",(0,0),(-1,-1),12),
        ("LINEAFTER",(0,0),(3,-1),0.5,colors.HexColor("#1a3a24")),
        ("ALIGN",(0,0),(-1,-1),"CENTER"),("VALIGN",(0,0),(-1,-1),"MIDDLE"),
    ]))
    story+=[banner,Spacer(1,0.5*cm)]

    # ── 1. VEGETATION INDICES ─────────────────────────────────────────────────
    story.append(_h2("1. Vegetation Indices (Sentinel-2)"))
    rows=[["Index","Value","Threshold","Visual Bar","Status"]]
    for name,key,good,warn in [("NDVI","ndvi",0.25,0.15),("EVI","evi",0.18,0.10),
        ("NDWI","ndwi",-0.20,-0.28),("NDRE","ndre",0.15,0.08),("LAI","lai",0.45,0.25)]:
        v=idx.get(key) or 0
        pct=min(1.0,max(0,(v-(-0.5))/(1.0-(-0.5))))
        filled=int(pct*25); bar="█"*filled+"-"*(25-filled)
        st="✓ Good" if v>=good else "~ Fair" if v>=warn else "✗ Low"
        rows.append([name,f"{v:.4f}",f">{warn:.2f}",bar,st])
    it=Table(rows,colWidths=[W*0.10,W*0.12,W*0.13,W*0.48,W*0.17])
    it.setStyle(TableStyle([
        ("BACKGROUND",(0,0),(-1,0),C_DARK),("TEXTCOLOR",(0,0),(-1,0),C_WHITE),
        ("FONTNAME",(0,0),(-1,0),"Helvetica-Bold"),("FONTSIZE",(0,0),(-1,-1),8),
        ("FONTNAME",(3,1),(3,-1),"Courier"),("FONTSIZE",(3,1),(3,-1),7),
        ("ROWBACKGROUNDS",(0,1),(-1,-1),[C_LIGHT,C_WHITE]),
        ("GRID",(0,0),(-1,-1),0.5,C_BORDER),
        ("TOPPADDING",(0,0),(-1,-1),7),("BOTTOMPADDING",(0,0),(-1,-1),7),
        ("LEFTPADDING",(0,0),(-1,-1),8),
    ]))
    story+=[it,Spacer(1,0.25*cm)]

    # Index definitions
    defs=[
        ["NDVI","Normalized Difference Vegetation Index — measures green vegetation density and overall crop health. Higher = denser, healthier canopy."],
        ["EVI", "Enhanced Vegetation Index — like NDVI but corrects for atmospheric haze and soil background. More reliable in dense or high-biomass crops."],
        ["NDWI","Normalized Difference Water Index — measures water content in vegetation and soil. Less negative = better moisture; below −0.28 signals irrigation need."],
        ["NDRE","Normalized Difference Red Edge — detects chlorophyll using Sentinel-2 red-edge band. Catches early nutrient stress before NDVI responds."],
        ["LAI", "Leaf Area Index — total one-sided leaf area per unit ground area (m²/m²). Higher values mean a fuller, denser crop canopy."],
        ["Status","✓ Good: index meets healthy target  |  ~ Fair: above critical threshold but worth watching  |  ✗ Low: below critical threshold, action may be needed"],
    ]
    dt=Table(defs,colWidths=[W*0.10,W*0.90])
    dt.setStyle(TableStyle([
        ("FONTNAME",(0,0),(0,-1),"Helvetica-Bold"),("FONTSIZE",(0,0),(-1,-1),7),
        ("FONTNAME",(1,0),(1,-1),"Helvetica"),
        ("TEXTCOLOR",(0,0),(0,-2),C_GREEN),
        ("TEXTCOLOR",(0,-1),(0,-1),C_MUTED),("TEXTCOLOR",(1,-1),(1,-1),C_MUTED),
        ("TOPPADDING",(0,0),(-1,-1),3),("BOTTOMPADDING",(0,0),(-1,-1),3),
        ("LEFTPADDING",(0,0),(-1,-1),4),
        ("LINEBELOW",(0,-1),(-1,-1),0.5,C_BORDER),
        ("BACKGROUND",(0,-1),(-1,-1),C_LIGHT),
    ]))
    story+=[dt,Spacer(1,0.4*cm)]

    # ── 2. CROP HEALTH ────────────────────────────────────────────────────────
    story.append(_h2("2. Crop Health Assessment"))
    probs=stress.get("probabilities",{})
    hrows=[["Class","Probability","Confidence Bar"]]
    for cls,p in probs.items():
        filled=int(p*35); bar="█"*filled+"-"*(35-filled)
        hrows.append([cls,f"{p*100:.1f}%",bar])
    ht=Table(hrows,colWidths=[W*0.25,W*0.15,W*0.60])
    ht.setStyle(TableStyle([
        ("BACKGROUND",(0,0),(-1,0),C_DARK),("TEXTCOLOR",(0,0),(-1,0),C_WHITE),
        ("FONTNAME",(0,0),(-1,0),"Helvetica-Bold"),("FONTSIZE",(0,0),(-1,-1),9),
        ("FONTNAME",(2,1),(2,-1),"Courier"),("FONTSIZE",(2,1),(2,-1),8),
        ("ROWBACKGROUNDS",(0,1),(-1,-1),[C_LIGHT,C_WHITE,C_LIGHT]),
        ("GRID",(0,0),(-1,-1),0.5,C_BORDER),
        ("TOPPADDING",(0,0),(-1,-1),7),("BOTTOMPADDING",(0,0),(-1,-1),7),
        ("LEFTPADDING",(0,0),(-1,-1),10),
        ("TEXTCOLOR",(0,1),(0,1),sc),("FONTNAME",(0,1),(0,1),"Helvetica-Bold"),
    ]))
    story.append(Paragraph(f"<b>Prediction: {pred}</b>  (Confidence: {conf*100:.1f}%)",
        S("cp",fontSize=10,textColor=sc,fontName="Helvetica-Bold",spaceAfter=4)))
    story+=[ht,Spacer(1,0.4*cm)]

    # ── 3-6. OTHER SECTIONS ───────────────────────────────────────────────────
    story.append(_h2("3. Irrigation Recommendation"))
    story.append(_tbl([["Parameter","Value"],
        ["Recommendation",irrig.get("recommendation","—").replace("_"," ").title()],
        ["Soil Moisture",f"{irrig.get('soil_moisture_pct',0):.1f}%"],
        ["Water Needed",f"{irrig.get('water_amount_mm',0):.1f} mm"],
        ["Confidence",f"{irrig.get('confidence',0)*100:.0f}%"],
    ],[W*0.40,W*0.60],[("TEXTCOLOR",(1,1),(1,1),C_BLUE),("FONTNAME",(1,1),(1,1),"Helvetica-Bold")]))
    story.append(Spacer(1,0.4*cm))

    story.append(_h2("4. Yield Prediction"))
    story.append(_tbl([["Parameter","Value"],
        ["Predicted Yield",f"{yld.get('predicted_yield_tha',0):.3f} tons/hectare"],
        ["Lower Bound (95%)",f"{yld.get('yield_lower_bound',0):.3f} t/ha"],
        ["Upper Bound (95%)",f"{yld.get('yield_upper_bound',0):.3f} t/ha"],
        ["Harvest Readiness",f"{yld.get('harvest_readiness_pct',0):.1f}%"],
    ],[W*0.40,W*0.60],[("TEXTCOLOR",(1,1),(1,1),C_PURPLE),("FONTNAME",(1,1),(1,1),"Helvetica-Bold")]))
    story.append(Spacer(1,0.4*cm))

    story.append(_h2("5. Soil Condition Assessment"))
    story.append(_tbl([["Parameter","Value","Status"],
        ["Soil pH",f"{soil.get('soil_ph',0):.2f}",soil.get("ph_status","—")],
        ["Salinity",f"{soil.get('salinity_ds_m',0):.3f} dS/m",soil.get("salinity_status","—")],
        ["Organic Matter",f"{soil.get('organic_matter_pct',0):.3f}%",soil.get("organic_matter_status","—")],
    ],[W*0.35,W*0.30,W*0.35]))
    story.append(Spacer(1,0.4*cm))

    story.append(_h2("6. Variable Rate Application (VRA)"))
    story.append(_tbl([["Parameter","Value"],
        ["Fertility Zone",vra.get("zone","—")],
        ["Fertiliser Recommendation",vra.get("fertiliser_recommendation","—")],
        ["Confidence",f"{vra.get('confidence',0)*100:.0f}%"],
    ],[W*0.38,W*0.62],[("TEXTCOLOR",(1,1),(1,1),C_GREEN),("FONTNAME",(1,1),(1,1),"Helvetica-Bold")]))

    # ── 7. BAND COMPOSITES ────────────────────────────────────────────────────
    fid=d.get("field_id"); tok=d.get("_token")
    start=d.get("_start_date","2024-01-01"); end=d.get("_end_date","2024-03-01")

    if fid and tok and include_bands:
        story.append(PageBreak())
        story.append(_h2("7. Satellite Band Composites (Sentinel-2)"))
        story.append(Paragraph(
            "Real imagery from Google Earth Engine · 4km × 4km area around field",
            S("d",fontSize=9,textColor=C_MUTED,spaceAfter=10)))
        descs={
            "Agriculture Composite (B11+B8+B2)":"SWIR+NIR+Blue — crops=bright green, soil=brown",
            "Vegetation Analysis (B8A+B4+B3)":"Narrow NIR — canopy density and plant health",
            "NDRE Visualization (B5+B4+B3)":"Red Edge — late season, avoids NDVI saturation",
            "True Color RGB (B4+B3+B2)":"Natural color as seen by the human eye",
            "False Color NIR (B8+B4+B3)":"NIR composite — healthy vegetation=bright red",
            "NDVI Colormap":"Green=healthy · Orange/Red=stressed · Grey=bare soil",
        }
        bands=_fetch_bands(fid,start,end,tok)
        if bands:
            iw=(W-0.6*cm)/2; ih=iw*0.72
            items=list(bands.items())
            for i in range(0,len(items),2):
                row=[]
                for j in range(2):
                    if i+j<len(items):
                        lbl,png=items[i+j]
                        img=Image(io.BytesIO(png),width=iw,height=ih)
                        c=Table([[Paragraph(f"<b>{lbl}</b>",
                              S("bl",fontSize=8,textColor=C_GREEN,fontName="Helvetica-Bold"))],
                            [img],
                            [Paragraph(descs.get(lbl,""),
                              S("bd",fontSize=7,textColor=C_MUTED,leading=10))]],
                            colWidths=[iw])
                        c.setStyle(TableStyle([
                            ("BACKGROUND",(0,0),(-1,0),C_LIGHT),
                            ("TOPPADDING",(0,0),(-1,-1),5),("BOTTOMPADDING",(0,0),(-1,-1),5),
                            ("LEFTPADDING",(0,0),(-1,-1),6),("GRID",(0,0),(-1,-1),0.5,C_BORDER)]))
                        row.append(c)
                    else: row.append(Spacer(iw,ih))
                rt=Table([row],colWidths=[iw+0.3*cm,iw+0.3*cm])
                rt.setStyle(TableStyle([("LEFTPADDING",(0,0),(-1,-1),0),
                    ("RIGHTPADDING",(0,0),(-1,-1),0),("TOPPADDING",(0,0),(-1,-1),0),
                    ("BOTTOMPADDING",(0,0),(-1,-1),10),("VALIGN",(0,0),(-1,-1),"TOP")]))
                story.append(rt)
        else:
            story.append(Paragraph("No band images available.",
                S("na",fontSize=9,textColor=C_MUTED)))

    # ── FOOTER ────────────────────────────────────────────────────────────────
    story+=[Spacer(1,0.6*cm),HRFlowable(width="100%",thickness=1,color=C_BORDER),Spacer(1,0.2*cm)]
    story.append(Paragraph(
        "Generated by <b>AgroSense</b> — SMIU Final Year Project 2025–2026 · "
        "Sentinel-2 imagery via Google Earth Engine · ML models trained on Pakistan agricultural data · Advisory use only.",
        S("ft",fontSize=7.5,textColor=C_MUTED,alignment=TA_CENTER,leading=11)))

    doc.build(story)
    return output_path
