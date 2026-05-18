from PyQt6.QtCore import QObject, pyqtSignal, Qt
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QFont

STRINGS = {
    # ── App / MainWindow ──────────────────────────────────────────────────────
    "app_name":               {"en": "AgroSense",                             "ur": "ایگرو سینس"},
    "main_menu":              {"en": "MAIN MENU",                             "ur": "مرکزی مینو"},
    "nav_dashboard":          {"en": "🏠  Dashboard",                         "ur": "🏠  ڈیش بورڈ"},
    "nav_farms":              {"en": "🗺  Farms & Fields",                    "ur": "🗺  کھیت اور زمین"},
    "nav_imagery":            {"en": "🛰  Satellite Imagery",                 "ur": "🛰  سیٹلائٹ تصاویر"},
    "nav_analytics":          {"en": "📊  Analytics",                         "ur": "📊  تجزیات"},
    "nav_map":                {"en": "🗺  Map View",                          "ur": "🗺  نقشہ"},
    "nav_bands":              {"en": "🛰  Band View",                         "ur": "🛰  بینڈ ویو"},
    "connected":              {"en": "● Connected",                           "ur": "● متصل"},
    "sign_out":               {"en": "⎋  Sign out",                           "ur": "⎋  باہر نکلیں"},
    "lang_toggle":            {"en": "🌐 اردو",                               "ur": "🌐 EN"},
    "topbar_title_dashboard": {"en": "Dashboard",                             "ur": "ڈیش بورڈ"},
    "topbar_title_farms":     {"en": "Farms & Fields",                        "ur": "کھیت اور زمین"},
    "topbar_title_imagery":   {"en": "Satellite Imagery",                     "ur": "سیٹلائٹ تصاویر"},
    "topbar_title_analytics": {"en": "Analytics",                             "ur": "تجزیات"},
    "topbar_title_map":       {"en": "Map View",                              "ur": "نقشہ"},
    "topbar_title_bands":     {"en": "Band View",                             "ur": "بینڈ ویو"},
    "topbar_sub_dashboard":   {"en": "Crop intelligence overview",            "ur": "فصل انٹیلیجنس کا جائزہ"},
    "topbar_sub_farms":       {"en": "Manage farms and fields",               "ur": "کھیت اور زمین کا انتظام"},
    "topbar_sub_imagery":     {"en": "Fetch and analyse Sentinel-2 data",     "ur": "سینٹینل-2 ڈیٹا کا تجزیہ"},
    "topbar_sub_analytics":   {"en": "Index trends over time",                "ur": "وقت کے ساتھ انڈیکس رجحانات"},
    "topbar_sub_map":         {"en": "Farm locations on satellite map",        "ur": "سیٹلائٹ نقشے پر کھیتوں کا مقام"},
    "topbar_sub_bands":       {"en": "Sentinel-2 band composites per field",  "ur": "فی فیلڈ سینٹینل-2 بینڈ"},
    # ── Smart Farming ─────────────────────────────────────────────────────────
    "nav_smart":          {"en": "🌱  Smart Farming",              "ur": "🌱  ذہین زراعت"},
    "topbar_sub_smart":   {"en": "Weather & Recommendations",       "ur": "موسم اور سفارشات"},
    "smart_title":        {"en": "Smart Farming Recommendations",   "ur": "ذہین زراعت سفارشات"},
    "select_farm_first":  {"en": "Select a farm to continue",       "ur": "جاری رکھنے کے لیے فارم منتخب کریں"},
    "loading_smart":      {"en": "Fetching weather data…",          "ur": "موسمی ڈیٹا حاصل ہو رہا ہے…"},
    "alerts_title":       {"en": "⚠  Crop Protection Alerts",      "ur": "⚠  فصل حفاظت الرٹس"},
    "no_alerts":          {"en": "✅  No weather risks detected this week", "ur": "✅  اس ہفتے کوئی موسمی خطرہ نہیں"},
    "forecast_title":     {"en": "📅  7-Day Weather Forecast",      "ur": "📅  7 روزہ موسمی پیش گوئی"},
    "planting_rec_title": {"en": "🌾  Planting Recommendation",     "ur": "🌾  بوائی کی سفارش"},
    "ml_summary_title":   {"en": "🤖  ML Analysis Summary",        "ur": "🤖  ML تجزیہ خلاصہ"},
    "weekly_summary":     {"en": "📊  Weekly Summary",             "ur": "📊  ہفتہ وار خلاصہ"},
    "ideal_date":         {"en": "Ideal Planting Date",             "ur": "بہترین بوائی تاریخ"},
    "not_favorable":      {"en": "Not favorable this week",         "ur": "اس ہفتے موزوں نہیں"},
    "risk_level":         {"en": "Risk Level",                      "ur": "خطرے کی سطح"},
    "water_req":          {"en": "Water Requirement",               "ur": "پانی کی ضرورت"},
    "suitability":        {"en": "Suitability Score",               "ur": "موزونیت اسکور"},
    "avg_temp":           {"en": "Avg Temp",                        "ur": "اوسط درجہ حرارت"},
    "total_rain":         {"en": "Total Rain",                      "ur": "کل بارش"},
    "avg_humidity":       {"en": "Avg Humidity",                    "ur": "اوسط نمی"},
    "avg_wind":           {"en": "Avg Wind",                        "ur": "اوسط ہوا"},
    "alert_heatwave":     {"en": "🔥 Heatwave Warning",            "ur": "🔥 گرمی کی لہر"},
    "alert_heavy_rain":   {"en": "🌧 Heavy Rain Alert",            "ur": "🌧 شدید بارش الرٹ"},
    "alert_frost":        {"en": "❄ Frost Warning",                "ur": "❄ پالہ انتباہ"},
    "alert_drought":      {"en": "☀ Drought Risk",                 "ur": "☀ خشک سالی خطرہ"},
    "alert_strong_wind":  {"en": "💨 Strong Wind Alert",           "ur": "💨 تیز ہوا الرٹ"},
    "alert_spray_delay":  {"en": "🚫 Delay Pesticide Spraying",    "ur": "🚫 کیڑے مار دوا دیر سے چھڑکیں"},
    "alert_fungal_risk":  {"en": "🍄 Fungal Disease Risk",         "ur": "🍄 پھپھوندی بیماری خطرہ"},
    "ml_unavailable":     {"en": "ML analysis unavailable (run field analysis first)", "ur": "ML تجزیہ دستیاب نہیں (پہلے فیلڈ تجزیہ چلائیں)"},
    "crop_health_lbl":    {"en": "Crop Health",                    "ur": "فصل کی صحت"},
    "irrigation_lbl":     {"en": "Irrigation",                     "ur": "آبپاشی"},
    "yield_lbl":          {"en": "Predicted Yield",                "ur": "متوقع پیداوار"},
    # ── Dashboard ─────────────────────────────────────────────────────────────
    "stat_farms":             {"en": "Total Farms",                           "ur": "کل فارم"},
    "stat_fields":            {"en": "Total Fields",                          "ur": "کل فیلڈز"},
    "stat_health":            {"en": "Crop Health",                           "ur": "فصل کی صحت"},
    "stat_yield":             {"en": "Est. Yield",                            "ur": "متوقع پیداوار"},
    "analysis_title":         {"en": "🔬  Full Field Analysis",               "ur": "🔬  مکمل فیلڈ تجزیہ"},
    "run_analysis":           {"en": "▶  Run Analysis",                       "ur": "▶  تجزیہ چلائیں"},
    "analysing":              {"en": "Analysing...",                          "ur": "تجزیہ ہو رہا ہے..."},
    "export_pdf":             {"en": "📄  Export PDF (with satellite images)", "ur": "📄  پی ڈی ایف برآمد کریں"},
    "send_alert":             {"en": "📧  Send Alert",                        "ur": "📧  الرٹ بھیجیں"},
    "fetching_pdf":           {"en": "⏳  Fetching bands & generating PDF...", "ur": "⏳  بینڈ حاصل ہو رہے ہیں..."},
    "pdf_ready_title":        {"en": "PDF Ready",                             "ur": "پی ڈی ایف تیار ہے"},
    "pdf_error_title":        {"en": "PDF Error",                             "ur": "پی ڈی ایف میں خرابی"},
    "no_data_title":          {"en": "No Data",                               "ur": "کوئی ڈیٹا نہیں"},
    "run_analysis_first":     {"en": "Please run analysis first.",            "ur": "پہلے تجزیہ چلائیں۔"},
    "alert_title":            {"en": "Alert",                                 "ur": "الرٹ"},
    "alert_error_title":      {"en": "Alert Error",                           "ur": "الرٹ میں خرابی"},
    # ── Farms ─────────────────────────────────────────────────────────────────
    "add_farm_btn":           {"en": "+ Add Farm",                            "ur": "+ فارم شامل کریں"},
    "del_farm_btn":           {"en": "🗑  Delete Farm",                       "ur": "🗑  فارم حذف کریں"},
    "no_farm_selected":       {"en": "No farm selected — click a row below",  "ur": "کوئی فارم منتخب نہیں — نیچے کلک کریں"},
    "fields_section":         {"en": "Fields",                                "ur": "فیلڈز"},
    "add_field_btn":          {"en": "+ Add Field",                           "ur": "+ فیلڈ شامل کریں"},
    "farm_tbl_name":          {"en": "Farm Name",                             "ur": "فارم کا نام"},
    "farm_tbl_district":      {"en": "District",                              "ur": "ضلع"},
    "farm_tbl_province":      {"en": "Province",                              "ur": "صوبہ"},
    "farm_tbl_area":          {"en": "Area (ha)",                             "ur": "رقبہ (ہیکٹر)"},
    "field_tbl_name":         {"en": "Field Name",                            "ur": "فیلڈ کا نام"},
    "field_tbl_crop":         {"en": "Crop Type",                             "ur": "فصل کی قسم"},
    "field_tbl_area":         {"en": "Area (ha)",                             "ur": "رقبہ (ہیکٹر)"},
    "field_tbl_id":           {"en": "ID",                                    "ur": "شناخت"},
    "del_farm_confirm":       {"en": "Delete this farm and all its fields?",  "ur": "یہ فارم اور تمام فیلڈز حذف کریں؟"},
    "del_farm_dialog":        {"en": "Delete Farm",                           "ur": "فارم حذف کریں"},
    "add_farm_dialog_title":  {"en": "Add New Farm",                          "ur": "نیا فارم شامل کریں"},
    "form_farm_name":         {"en": "Farm Name *",                           "ur": "فارم کا نام *"},
    "form_district":          {"en": "District",                              "ur": "ضلع"},
    "form_province":          {"en": "Province",                              "ur": "صوبہ"},
    "form_area_ha":           {"en": "Area (ha)",                             "ur": "رقبہ (ہیکٹر)"},
    "form_latitude":          {"en": "Latitude",                              "ur": "عرض البلد"},
    "form_longitude":         {"en": "Longitude",                             "ur": "طول البلد"},
    "add_farm_save_btn":      {"en": "Add Farm",                              "ur": "فارم شامل کریں"},
    "cancel_btn":             {"en": "Cancel",                                "ur": "منسوخ"},
    "saving_btn":             {"en": "Saving...",                             "ur": "محفوظ ہو رہا ہے..."},
    "add_field_dialog_title": {"en": "Add Field",                             "ur": "فیلڈ شامل کریں"},
    "form_field_name":        {"en": "Field Name",                            "ur": "فیلڈ کا نام"},
    "form_crop_type":         {"en": "Crop Type",                             "ur": "فصل کی قسم"},
    "add_field_save_btn":     {"en": "Add Field",                             "ur": "فیلڈ شامل کریں"},
    "no_farm_sel_title":      {"en": "No Farm Selected",                      "ur": "فارم منتخب نہیں"},
    "no_farm_sel_msg":        {"en": "Please click on a farm row to select it first.", "ur": "پہلے فارم قطار پر کلک کریں۔"},
    "error_title":            {"en": "Error",                                 "ur": "خرابی"},
    # ── Imagery ───────────────────────────────────────────────────────────────
    "imagery_config":         {"en": "📡  Configure Satellite Analysis",      "ur": "📡  سیٹلائٹ تجزیہ ترتیب دیں"},
    "farm_label":             {"en": "Farm:",                                 "ur": "فارم:"},
    "field_label":            {"en": "Field:",                                "ur": "فیلڈ:"},
    "start_label":            {"en": "Start:",                                "ur": "شروع:"},
    "end_label":              {"en": "End:",                                   "ur": "اختتام:"},
    "max_cloud_label":        {"en": "Max Cloud:",                            "ur": "زیادہ بادل:"},
    "fetch_analyse":          {"en": "🛰  Fetch & Analyse",                   "ur": "🛰  حاصل کریں اور تجزیہ کریں"},
    "fetching_gee_btn":       {"en": "⏳  Fetching from GEE...",              "ur": "⏳  جی ای ای سے حاصل ہو رہا ہے..."},
    "gee_contact":            {"en": "Contacting Google Earth Engine...",     "ur": "گوگل ارتھ انجن سے رابطہ..."},
    "imagery_results_title":  {"en": "📊  Latest Results",                    "ur": "📊  تازہ ترین نتائج"},
    "index_history_title":    {"en": "📅  Index History",                     "ur": "📅  انڈیکس تاریخ"},
    "select_field_msg":       {"en": "⚠  Please select a field",              "ur": "⚠  فیلڈ منتخب کریں"},
    "select_farm_opt":        {"en": "Select farm...",                        "ur": "فارم منتخب کریں..."},
    "select_field_opt":       {"en": "Select field...",                       "ur": "فیلڈ منتخب کریں..."},
    # ── Analytics ─────────────────────────────────────────────────────────────
    "select_farm_field_msg":  {"en": "Select a farm and field to view analytics", "ur": "تجزیات دیکھنے کے لیے فارم اور فیلڈ منتخب کریں"},
    "loading_txt":            {"en": "Loading...",                            "ur": "لوڈ ہو رہا ہے..."},
    "no_history_msg":         {"en": "No history found. Run imagery analysis first.", "ur": "کوئی تاریخ نہیں۔ پہلے سیٹلائٹ تجزیہ چلائیں۔"},
    # ── Map ───────────────────────────────────────────────────────────────────
    "all_farms_opt":          {"en": "🌍  All Farms",                         "ur": "🌍  تمام فارم"},
    "loading_farms":          {"en": "Loading farms...",                      "ur": "فارم لوڈ ہو رہے ہیں..."},
    "map_farm_label":         {"en": "🌍  Farm:",                             "ur": "🌍  فارم:"},
    "map_reset":              {"en": "🔍  Reset",                             "ur": "🔍  دوبارہ ترتیب"},
    "map_error":              {"en": "Error loading farms",                   "ur": "فارم لوڈ کرنے میں خرابی"},
    # ── Band View ─────────────────────────────────────────────────────────────
    "fetch_bands":            {"en": "🛰  Fetch Band Composites",             "ur": "🛰  بینڈ کمپوزٹ حاصل کریں"},
    "select_field_fetch":     {"en": "Select a field and click Fetch Band Composites", "ur": "فیلڈ منتخب کریں اور بینڈ کمپوزٹ حاصل کریں"},
    "fetching_bands_btn":     {"en": "⏳  Fetching from GEE...",              "ur": "⏳  جی ای ای سے حاصل ہو رہا ہے..."},
    "band_load_error":        {"en": "Error loading fields",                  "ur": "فیلڈز لوڈ کرنے میں خرابی"},
    # ── Login ─────────────────────────────────────────────────────────────────
    "welcome_back":           {"en": "Welcome back",                          "ur": "خوش آمدید"},
    "signin_subtitle":        {"en": "Sign in to your AgroSense account",     "ur": "اپنے اکاؤنٹ میں داخل ہوں"},
    "email_label_login":      {"en": "Email address",                         "ur": "ای میل پتہ"},
    "password_label_login":   {"en": "Password",                              "ur": "پاس ورڈ"},
    "signin_btn":             {"en": "Sign In →",                             "ur": "← داخل ہوں"},
    "signing_in":             {"en": "Signing in...",                         "ur": "داخل ہو رہے ہیں..."},
    "create_account_link":    {"en": "Create a new account",                  "ur": "نیا اکاؤنٹ بنائیں"},
    "login_tagline":          {"en": "Satellite-Based Crop\nIntelligence for Pakistan", "ur": "پاکستان کے لیے\nسیٹلائٹ بنیاد فصل انٹیلیجنس"},
    "invalid_login":          {"en": "Invalid email or password. Please try again.", "ur": "غلط ای میل یا پاس ورڈ۔ دوبارہ کوشش کریں۔"},
    "enter_credentials":      {"en": "Please enter your email and password",  "ur": "ای میل اور پاس ورڈ درج کریں"},
    "or_divider":             {"en": "  or  ",                                "ur": "  یا  "},
    # ── Register ──────────────────────────────────────────────────────────────
    "create_account_title":   {"en": "Create Account",                        "ur": "اکاؤنٹ بنائیں"},
    "monitor_crops":          {"en": "Start monitoring your crops",           "ur": "اپنی فصلوں کی نگرانی شروع کریں"},
    "full_name_label":        {"en": "Full Name",                             "ur": "پورا نام"},
    "email_reg_label":        {"en": "Email",                                 "ur": "ای میل"},
    "password_reg_label":     {"en": "Password",                              "ur": "پاس ورڈ"},
    "role_label":             {"en": "Role",                                  "ur": "کردار"},
    "create_account_btn":     {"en": "Create Account",                        "ur": "اکاؤنٹ بنائیں"},
    "creating_account":       {"en": "Creating account...",                   "ur": "اکاؤنٹ بنایا جا رہا ہے..."},
    "all_fields_required":    {"en": "All fields are required",               "ur": "تمام خانے ضروری ہیں"},
    "reg_success_msg":        {"en": "Account created! You can now sign in.", "ur": "اکاؤنٹ بن گیا! اب داخل ہو سکتے ہیں۔"},
    "success_title":          {"en": "Success",                               "ur": "کامیابی"},
    "reg_window_title":       {"en": "AgroSense — Register",                  "ur": "ایگرو سینس — رجسٹریشن"},
    "reg_password_ph":        {"en": "min 8 characters",                       "ur": "کم از کم 8 حروف"},
    # ── Table headers ─────────────────────────────────────────────────────────
    "tbl_date":               {"en": "Date",                                  "ur": "تاریخ"},
    "tbl_ndvi":               {"en": "NDVI",                                  "ur": "NDVI"},
    "tbl_evi":                {"en": "EVI",                                   "ur": "EVI"},
    "tbl_ndwi":               {"en": "NDWI",                                  "ur": "NDWI"},
    "tbl_ndre":               {"en": "NDRE",                                  "ur": "NDRE"},
    "tbl_lai":                {"en": "LAI",                                   "ur": "LAI"},
}


class LanguageManager(QObject):
    language_changed = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self._lang = "en"

    @property
    def current_lang(self) -> str:
        return self._lang

    def tr(self, key: str) -> str:
        entry = STRINGS.get(key, {})
        return entry.get(self._lang, entry.get("en", key))

    def is_urdu(self) -> bool:
        return self._lang == "ur"

    def toggle(self):
        self._lang = "ur" if self._lang == "en" else "en"
        app = QApplication.instance()
        if app:
            if self._lang == "ur":
                app.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
                self._apply_urdu_font(app)
            else:
                app.setLayoutDirection(Qt.LayoutDirection.LeftToRight)
                app.setFont(QFont("Segoe UI", 10))
        self.language_changed.emit(self._lang)

    def _apply_urdu_font(self, app):
        for family in ("Noto Nastaliq Urdu", "Traditional Arabic", "Arial Unicode MS"):
            f = QFont(family, 12)
            if f.family() == family:
                app.setFont(f)
                return
        app.setFont(QFont("Arial", 11))


LM = LanguageManager()
