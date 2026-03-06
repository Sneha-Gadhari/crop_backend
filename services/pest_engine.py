"""
Pest Engine — weather-triggered + community-report pest alerts.
All data is calibrated for Maharashtra crops, seasons and typical weather patterns.
"""

# ── Pest treatment database ─────────────────────────────────────────
# key → (chemical_action, organic_action, description)
PEST_DB: dict[str, tuple[str, str, str]] = {
    # Cotton pests — Vidarbha / Marathwada dominant
    "Whitefly": (
        "Apply imidacloprid 0.3 ml/L or thiamethoxam 0.2 g/L. Install yellow sticky traps at 10/acre.",
        "Neem oil 5 ml/L every 7 days. Yellow sticky traps. Encourage Encarsia parasitoid.",
        "Vector of cotton leaf curl virus. High humidity >70% triggers outbreaks.",
    ),
    "Pink Bollworm": (
        "Release sterile moths (if available). Apply spinosad 45 SC 0.5 ml/L. Destroy old cotton stalks.",
        "Pheromone traps at 5/acre. Light traps at field edge. Bt spray on young bolls.",
        "Most destructive cotton pest in Maharashtra. Peaks Sept–Oct in Kharif.",
    ),
    "American Bollworm": (
        "Apply chlorantraniliprole 18.5 SC 0.3 ml/L or emamectin benzoate 5 SG 0.4 g/L.",
        "Bt (Bacillus thuringiensis) spray. Pheromone traps. Predators: Trichogramma cards.",
        "Major Kharif cotton pest. Temp 25–32°C + humidity >65% triggers peak activity.",
    ),
    "Jassid": (
        "Apply dimethoate 30 EC 1.5 ml/L or imidacloprid. Avoid excess nitrogen.",
        "Neem oil 5 ml/L. Maintain field sanitation. Border crops of maize as trap crop.",
        "Causes leaf curl and hopper burn. Common in young cotton in July–August.",
    ),
    "Thrips": (
        "Apply fipronil 5 SC 1 ml/L. Drench soil around base of young plants.",
        "Blue sticky traps. Neem seed kernel extract 5%. Reflective mulch.",
        "Damage seedlings in April–June. Spreads TSWV virus in solanaceous crops.",
    ),
    # Rice pests — Konkan, Thane, Raigad, Ratnagiri
    "Brown Planthopper": (
        "Drain field and allow to dry. Apply buprofezin 25 SC 1 ml/L or pymetrozine. Avoid excess N.",
        "Release Lycosa spider predators. Light traps. Avoid close planting.",
        "Key rice pest. Causes 'hopperburn'. Temp 25–30°C + humidity >85% + waterlogged = outbreak.",
    ),
    "Stem Borer": (
        "Apply cartap hydrochloride 4G (10 kg/acre) at tillering or chlorpyrifos 20 EC.",
        "Trichogramma japonicum release at 50,000/acre. Pull and destroy dead hearts early.",
        "Causes 'dead heart' at vegetative stage and 'white ear' at flowering.",
    ),
    "Gall Midge": (
        "Apply carbofuran 3G (10 kg/acre) at 20 days after transplanting.",
        "Resistant varieties (Abhaya, Lalat). Early transplanting before peak gall midge flight.",
        "Creates 'silver shoot' (onion leaf). Peak July–August. Common in Raigad, Ratnagiri.",
    ),
    "Leaf Folder": (
        "Apply chlorpyrifos 20 EC 2 ml/L. Clip affected leaves before applying.",
        "Neem oil 5 ml/L. Trichogramma chilonis 50,000/acre. Avoid N excess.",
        "Folds leaf longitudinally. Humidity >80% + dense canopy triggers outbreaks.",
    ),
    # Soybean pests — Marathwada, Vidarbha
    "Girdle Beetle": (
        "Apply chlorpyrifos 20 EC 2 ml/L at 20–25 DAS. Remove and destroy girdled stems.",
        "Clean field of soybean debris post-harvest. Crop rotation with non-legume.",
        "Major Kharif soybean pest. Girdles stem causing plant death. Peak July–Aug.",
    ),
    "Spodoptera": (
        "Apply emamectin benzoate 5 SG 0.4 g/L or chlorantraniliprole 18.5 SC.",
        "Pheromone traps. Bt spray (Bacillus thuringiensis var. kurstaki). Hand-pick egg masses.",
        "Defoliates soybean rapidly. Temp 28–35°C triggers multiple generations.",
    ),
    "Tobacco Caterpillar": (
        "Apply chlorpyrifos 20 EC 2.5 ml/L or quinalphos 25 EC 2 ml/L.",
        "Neem cake soil application. Light traps at night. Egg mass destruction.",
        "Polyphagous. Attacks soybean, cotton, groundnut. Outbreaks after heavy rain.",
    ),
    "Aphid": (
        "Apply dimethoate 30 EC 1.5 ml/L if > 20 aphids per plant. Avoid broad-spectrum insecticides.",
        "Soap solution 5 g/L. Lady bird beetle conservation. Yellow sticky traps.",
        "Colony-forming. Transmits viral diseases. Cool dry weather (15–20°C) favours outbreaks.",
    ),
    # Wheat pests — Nashik, Pune highlands, parts of Vidarbha
    "Powdery Mildew": (
        "Apply propiconazole 25 EC 1 ml/L or tebuconazole at first sign.",
        "Spray diluted milk (1:9 ratio) or potassium bicarbonate 5 g/L. Improve airflow.",
        "Fungal — cool temp 8–15°C + humidity 75% triggers outbreaks in Rabi wheat.",
    ),
    "Rust (Yellow/Brown)": (
        "Apply propiconazole 25 EC 1 ml/L or tebuconazole + trifloxystrobin urgently.",
        "Use resistant varieties. Avoid late sowing. Remove volunteer wheat plants.",
        "Fungal. Yellow rust at 10–15°C, brown rust at 15–25°C. Spreads fast in Nashik hills.",
    ),
    # Maize pests — widespread Maharashtra
    "Fall Armyworm": (
        "Apply chlorantraniliprole 18.5 SC 0.3 ml/L. Scout whorl every 3 days. Apply granules in whorl.",
        "Apply Bt spray (Bacillus thuringiensis) early. Pheromone traps. Trichogramma release.",
        "Exotic invasive. Causes major whorl damage. Temp 28–38°C + dry conditions triggers.",
    ),
    "Maize Stem Borer": (
        "Apply carbofuran 3G in whorl (5 kg/acre). Chlorpyrifos 20 EC 2 ml/L spray.",
        "Trichogramma chilonis cards 50,000/acre. Pull dead hearts. Crop rotation.",
        "Chilo partellus. Creates 'dead heart'. Jun–Sep peak in Kharif maize.",
    ),
    # Sugarcane pests — Kolhapur, Sangli, Satara, Solapur
    "Pyrilla": (
        "Apply chlorpyrifos 20 EC 2 ml/L. Install light traps. Roguing infested sets.",
        "Epipyrops parasitoid release. Neem oil spray. Destroy stubble after harvest.",
        "Sugarcane planthopper. Causes sooty mould. Common in flooded conditions.",
    ),
    "Top Borer": (
        "Apply chlorpyrifos 10 G (6 kg/acre) or fipronil in irrigation water.",
        "Trichogramma japonicum 50,000/acre. Destroy infested tops. Light traps.",
        "Most serious sugarcane pest in Maharashtra. Kills growing point (dead heart).",
    ),
    # Onion/Vegetable pests — Nashik, Pune, Satara
    "Thrips (Onion)": (
        "Apply fipronil 5 SC 1 ml/L or spinosad 45 SC 0.5 ml/L alternately.",
        "Blue sticky traps. Neem oil 5 ml/L. Reflective silver mulch reduces landing.",
        "Major onion pest in Nashik. Causes silver streak. Low humidity + hot dry weather.",
    ),
    "Late Blight": (
        "Apply metalaxyl-M 4% + mancozeb 64% WP 2.5 g/L urgently. Destroy infected plants.",
        "Copper sulfate spray (3 g/L). Remove infected plant debris immediately.",
        "Phytophthora infestans. Potato and tomato. Cool wet weather 15–25°C triggers.",
    ),
}

# ── Pest trigger rules for Maharashtra crops ─────────────────────────
# (crop, season, temp_min, temp_max, humidity_min, pest_name, severity, days_to_peak)
# Severity: "HIGH" / "MEDIUM" / "LOW"
PEST_RULES: list[tuple] = [
    # Cotton — Kharif — Vidarbha/Marathwada
    ("Cotton",      "Kharif",  28, 36, 70, "Whitefly",          "HIGH",   3),
    ("Cotton",      "Kharif",  25, 33, 65, "American Bollworm", "HIGH",   5),
    ("Cotton",      "Kharif",  26, 34, 60, "Pink Bollworm",     "HIGH",   7),
    ("Cotton",      "Kharif",  22, 32, 55, "Jassid",            "MEDIUM", 8),
    # Rice — Kharif — Konkan / Thane / Raigad
    ("Rice",        "Kharif",  25, 30, 85, "Brown Planthopper", "HIGH",   4),
    ("Rice",        "Kharif",  22, 32, 75, "Stem Borer",        "MEDIUM", 6),
    ("Rice",        "Kharif",  24, 31, 80, "Leaf Folder",       "MEDIUM", 5),
    ("Rice",        "Kharif",  23, 29, 82, "Gall Midge",        "MEDIUM", 7),
    # Soybean — Kharif — Marathwada / Vidarbha
    ("Soybean",     "Kharif",  25, 35, 65, "Girdle Beetle",     "HIGH",   4),
    ("Soybean",     "Kharif",  28, 38, 55, "Spodoptera",        "HIGH",   3),
    ("Soybean",     "Kharif",  26, 34, 60, "Tobacco Caterpillar","MEDIUM",5),
    # Wheat — Rabi
    ("Wheat",       "Rabi",    8,  16, 75, "Powdery Mildew",    "MEDIUM", 7),
    ("Wheat",       "Rabi",    10, 22, 72, "Rust (Yellow/Brown)","HIGH",  5),
    ("Wheat",       "Rabi",    12, 20, 60, "Aphid",             "LOW",   10),
    # Maize — Kharif
    ("Maize",       "Kharif",  28, 38, 50, "Fall Armyworm",     "HIGH",   2),
    ("Maize",       "Kharif",  24, 34, 60, "Maize Stem Borer",  "MEDIUM", 6),
    # Sugarcane — Whole Year / Kharif
    ("Sugarcane",   "Kharif",  28, 36, 70, "Top Borer",         "HIGH",   8),
    ("Sugarcane",   "Kharif",  25, 34, 75, "Pyrilla",           "MEDIUM", 6),
    # Onion — Rabi — Nashik dominant
    ("Onion",       "Rabi",    18, 28, 45, "Thrips (Onion)",    "HIGH",   3),
    # Tomato / Potato — Late Blight
    ("Tomato",      "Kharif",  15, 25, 80, "Late Blight",       "HIGH",   3),
    ("Potato",      "Rabi",    12, 22, 78, "Late Blight",       "HIGH",   3),
    # Pigeonpeas / Tur — Marathwada
    ("Pigeonpeas",  "Kharif",  26, 34, 65, "Tobacco Caterpillar","MEDIUM",5),
    ("Pigeonpeas",  "Kharif",  28, 36, 60, "Thrips",            "LOW",   10),
]


class PestEngine:
    def weather_alerts(self, crop: str, weather: dict, season: str = "Kharif") -> list[dict]:
        """Return weather-triggered pest alerts for the given crop + current weather."""
        temp = weather.get("temperature", 28)
        hum  = weather.get("humidity", 70)
        alerts = []

        for (c, s, tlo, thi, hmin, pest, sev, days) in PEST_RULES:
            if c.lower() != crop.lower():
                continue
            if season and s.lower() != season.lower():
                continue
            if tlo <= temp <= thi and hum >= hmin:
                info = PEST_DB.get(pest)
                if info:
                    action, organic, desc = info
                else:
                    action  = "Consult your local Krishi Vigyan Kendra (KVK)."
                    organic = "Neem oil 5 ml/L spray as general preventive."
                    desc    = ""
                alerts.append({
                    "pest_name"      : pest,
                    "crop"           : crop,
                    "severity"       : sev,
                    "alert_type"     : "weather_prediction",
                    "report_count"   : 0,
                    "trigger_reason" : (
                        f"Temp {temp:.0f}°C + Humidity {hum:.0f}% match {pest} "
                        f"outbreak conditions. {desc}"
                    ).strip(),
                    "action"         : action,
                    "organic"        : organic,
                    "days_until_peak": days,
                    "time_posted"    : "Now",
                })
        return alerts

    def action(self, pest: str) -> str:
        info = PEST_DB.get(pest)
        return info[0] if info else "Consult your local Krishi Vigyan Kendra (KVK)."

    def organic(self, pest: str) -> str:
        info = PEST_DB.get(pest)
        return info[1] if info else "Neem oil 5 ml/L spray every 7 days."

    def description(self, pest: str) -> str:
        info = PEST_DB.get(pest)
        return info[2] if info else ""