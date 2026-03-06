"""
Risk Engine — scores agricultural risk 0–100 across four dimensions,
and provides budget affordability checks for each crop.
"""

# ── Crop ideal growing conditions (Maharashtra) ───────────────────────
CROP_PROFILES: dict[str, dict] = {
    "rice"        : dict(temp=(22, 32), rain=(800, 2000), ph=(5.5, 7.0), seasons=["Kharif"]),
    "wheat"       : dict(temp=(12, 25), rain=(350, 700),  ph=(6.0, 7.5), seasons=["Rabi"]),
    "cotton"      : dict(temp=(25, 35), rain=(500, 1000), ph=(6.0, 8.0), seasons=["Kharif"]),
    "soybean"     : dict(temp=(20, 32), rain=(600, 1000), ph=(6.0, 7.5), seasons=["Kharif"]),
    "soyabean"    : dict(temp=(20, 32), rain=(600, 1000), ph=(6.0, 7.5), seasons=["Kharif"]),
    "maize"       : dict(temp=(18, 32), rain=(500, 900),  ph=(5.8, 7.5), seasons=["Kharif", "Rabi"]),
    "sugarcane"   : dict(temp=(20, 35), rain=(800, 1800), ph=(6.0, 8.0), seasons=["Kharif", "Whole Year"]),
    "groundnut"   : dict(temp=(24, 32), rain=(400, 700),  ph=(5.5, 7.5), seasons=["Kharif"]),
    "banana"      : dict(temp=(20, 35), rain=(800, 1800), ph=(5.5, 7.5), seasons=["Kharif", "Whole Year"]),
    "mango"       : dict(temp=(24, 38), rain=(600, 1200), ph=(5.5, 7.5), seasons=["Whole Year"]),
    "coconut"     : dict(temp=(22, 35), rain=(900, 2000), ph=(5.5, 8.0), seasons=["Whole Year"]),
    "pomegranate" : dict(temp=(22, 38), rain=(300, 700),  ph=(6.5, 8.0), seasons=["Kharif", "Rabi"]),
    "grapes"      : dict(temp=(15, 35), rain=(300, 700),  ph=(5.5, 7.5), seasons=["Rabi", "Whole Year"]),
    "onion"       : dict(temp=(13, 28), rain=(200, 600),  ph=(6.0, 7.5), seasons=["Rabi", "Kharif"]),
    "tomato"      : dict(temp=(18, 30), rain=(400, 900),  ph=(6.0, 7.5), seasons=["Rabi", "Kharif"]),
    "chickpea"    : dict(temp=(15, 28), rain=(250, 600),  ph=(6.0, 8.0), seasons=["Rabi"]),
    "gram"        : dict(temp=(15, 28), rain=(250, 600),  ph=(6.0, 8.0), seasons=["Rabi"]),
    "pigeonpeas"  : dict(temp=(22, 34), rain=(500, 900),  ph=(5.5, 7.5), seasons=["Kharif"]),
    "arhar/tur"   : dict(temp=(22, 34), rain=(500, 900),  ph=(5.5, 7.5), seasons=["Kharif"]),
    "lentil"      : dict(temp=(15, 25), rain=(300, 600),  ph=(6.0, 7.5), seasons=["Rabi"]),
    "orange"      : dict(temp=(20, 35), rain=(600, 1200), ph=(6.0, 7.5), seasons=["Whole Year"]),
    "coffee"      : dict(temp=(18, 28), rain=(1200, 2200),ph=(5.5, 6.5), seasons=["Kharif"]),
    "jute"        : dict(temp=(24, 35), rain=(1000, 2000),ph=(6.0, 7.0), seasons=["Kharif"]),
    "mungbean"    : dict(temp=(25, 35), rain=(350, 750),  ph=(6.0, 7.5), seasons=["Kharif", "Zaid"]),
    "blackgram"   : dict(temp=(25, 35), rain=(400, 800),  ph=(6.0, 7.5), seasons=["Kharif", "Rabi"]),
    "mothbeans"   : dict(temp=(28, 38), rain=(200, 500),  ph=(6.5, 8.0), seasons=["Kharif"]),
    "kidneybeans" : dict(temp=(16, 28), rain=(400, 800),  ph=(6.0, 7.5), seasons=["Kharif", "Rabi"]),
    "papaya"      : dict(temp=(22, 36), rain=(800, 1800), ph=(5.5, 7.0), seasons=["Whole Year"]),
    "apple"       : dict(temp=(8, 22),  rain=(600, 1100), ph=(5.5, 7.0), seasons=["Rabi"]),
    "watermelon"  : dict(temp=(24, 36), rain=(300, 700),  ph=(6.0, 7.5), seasons=["Zaid"]),
    "muskmelon"   : dict(temp=(24, 36), rain=(300, 700),  ph=(6.0, 7.5), seasons=["Zaid"]),
    "bajra"       : dict(temp=(25, 38), rain=(200, 600),  ph=(6.0, 7.5), seasons=["Kharif"]),
    "jowar"       : dict(temp=(25, 35), rain=(300, 700),  ph=(6.0, 7.5), seasons=["Kharif", "Rabi"]),
    "ragi"        : dict(temp=(20, 32), rain=(500, 1000), ph=(5.5, 7.0), seasons=["Kharif"]),
    "sunflower"   : dict(temp=(18, 30), rain=(500, 800),  ph=(6.0, 7.5), seasons=["Rabi"]),
    "urad"        : dict(temp=(25, 35), rain=(400, 800),  ph=(6.0, 7.5), seasons=["Kharif", "Rabi"]),
    "sesamum"     : dict(temp=(25, 35), rain=(400, 700),  ph=(6.0, 7.0), seasons=["Kharif"]),
    "safflower"   : dict(temp=(15, 30), rain=(200, 500),  ph=(6.0, 7.5), seasons=["Rabi"]),
}

# ── Market data (price_trend, demand_level, oversupply_risk, volatility 0-100) ──
MARKET_DATA: dict[str, tuple] = {
    "rice"       : ("STABLE",   "HIGH",   False, 25),
    "wheat"      : ("STABLE",   "HIGH",   False, 20),
    "cotton"     : ("DOWN",     "MEDIUM", True,  65),
    "soybean"    : ("UP",       "HIGH",   False, 35),
    "soyabean"   : ("UP",       "HIGH",   False, 35),
    "maize"      : ("UP",       "HIGH",   False, 30),
    "sugarcane"  : ("STABLE",   "HIGH",   False, 20),
    "groundnut"  : ("UP",       "HIGH",   False, 40),
    "banana"     : ("STABLE",   "HIGH",   False, 35),
    "mango"      : ("UP",       "HIGH",   False, 45),
    "coconut"    : ("STABLE",   "MEDIUM", False, 30),
    "pomegranate": ("UP",       "HIGH",   False, 40),
    "grapes"     : ("UP",       "HIGH",   False, 50),
    "onion"      : ("VOLATILE", "HIGH",   True,  80),
    "tomato"     : ("VOLATILE", "HIGH",   True,  75),
    "chickpea"   : ("UP",       "HIGH",   False, 35),
    "gram"       : ("UP",       "HIGH",   False, 35),
    "pigeonpeas" : ("UP",       "HIGH",   False, 40),
    "arhar/tur"  : ("UP",       "HIGH",   False, 40),
    "lentil"     : ("STABLE",   "MEDIUM", False, 30),
    "orange"     : ("STABLE",   "MEDIUM", False, 35),
    "coffee"     : ("UP",       "MEDIUM", False, 40),
    "jute"       : ("STABLE",   "MEDIUM", False, 25),
    "mungbean"   : ("UP",       "HIGH",   False, 35),
    "blackgram"  : ("UP",       "HIGH",   False, 35),
    "papaya"     : ("STABLE",   "MEDIUM", False, 40),
    "watermelon" : ("STABLE",   "HIGH",   False, 40),
    "muskmelon"  : ("STABLE",   "MEDIUM", False, 40),
    "apple"      : ("UP",       "HIGH",   False, 40),
    "bajra"      : ("STABLE",   "HIGH",   False, 30),
    "jowar"      : ("STABLE",   "HIGH",   False, 28),
    "ragi"       : ("STABLE",   "MEDIUM", False, 25),
    "sunflower"  : ("UP",       "MEDIUM", False, 38),
    "urad"       : ("UP",       "HIGH",   False, 35),
    "sesamum"    : ("UP",       "MEDIUM", False, 42),
    "safflower"  : ("STABLE",   "LOW",    False, 30),
    "mothbeans"  : ("UP",       "HIGH",   False, 38),
    "kidneybeans": ("STABLE",   "MEDIUM", False, 30),
}

# ── Input cost benchmarks (₹/acre, Maharashtra, CACP/NABARD/KVK data) ──
INPUT_COSTS: dict[str, dict] = {
    "rice"       : dict(seed=1800, fertilizer=3500, pesticide=2000, labor=4500, irrigation=1500, total=14000),
    "wheat"      : dict(seed=2000, fertilizer=3000, pesticide=1200, labor=3500, irrigation=1500, total=12000),
    "cotton"     : dict(seed=2500, fertilizer=4000, pesticide=5000, labor=6000, irrigation=2500, total=22000),
    "soybean"    : dict(seed=2200, fertilizer=2500, pesticide=2000, labor=3000, irrigation=1000, total=11500),
    "soyabean"   : dict(seed=2200, fertilizer=2500, pesticide=2000, labor=3000, irrigation=1000, total=11500),
    "maize"      : dict(seed=1800, fertilizer=3200, pesticide=1800, labor=3500, irrigation=2000, total=13000),
    "sugarcane"  : dict(seed=5000, fertilizer=6000, pesticide=3000, labor=12000,irrigation=5000, total=35000),
    "groundnut"  : dict(seed=3000, fertilizer=2500, pesticide=2000, labor=4000, irrigation=1500, total=14000),
    "banana"     : dict(seed=4000, fertilizer=5000, pesticide=3000, labor=8000, irrigation=4000, total=25000),
    "mango"      : dict(seed=3000, fertilizer=4500, pesticide=3500, labor=6000, irrigation=3000, total=22000),
    "pomegranate": dict(seed=5000, fertilizer=5000, pesticide=4000, labor=7000, irrigation=5000, total=28000),
    "grapes"     : dict(seed=6000, fertilizer=6000, pesticide=5000, labor=10000,irrigation=6000, total=35000),
    "onion"      : dict(seed=2000, fertilizer=3000, pesticide=2500, labor=5000, irrigation=2000, total=16000),
    "tomato"     : dict(seed=1500, fertilizer=3000, pesticide=3000, labor=5500, irrigation=2000, total=17000),
    "chickpea"   : dict(seed=2500, fertilizer=2000, pesticide=1500, labor=2500, irrigation=500,  total=10000),
    "gram"       : dict(seed=2500, fertilizer=2000, pesticide=1500, labor=2500, irrigation=500,  total=10000),
    "pigeonpeas" : dict(seed=2000, fertilizer=2000, pesticide=1800, labor=3000, irrigation=500,  total=10500),
    "arhar/tur"  : dict(seed=2000, fertilizer=2000, pesticide=1800, labor=3000, irrigation=500,  total=10500),
    "lentil"     : dict(seed=2000, fertilizer=1800, pesticide=1000, labor=2500, irrigation=500,  total=9000),
    "orange"     : dict(seed=3000, fertilizer=4000, pesticide=3000, labor=5000, irrigation=3500, total=21000),
    "coffee"     : dict(seed=4000, fertilizer=4000, pesticide=3000, labor=8000, irrigation=3000, total=25000),
    "jute"       : dict(seed=1500, fertilizer=3000, pesticide=1500, labor=4000, irrigation=1000, total=13000),
    "mungbean"   : dict(seed=1500, fertilizer=2000, pesticide=1200, labor=2500, irrigation=800,  total=9000),
    "blackgram"  : dict(seed=1500, fertilizer=2000, pesticide=1200, labor=2500, irrigation=800,  total=9000),
    "urad"       : dict(seed=1500, fertilizer=2000, pesticide=1200, labor=2500, irrigation=800,  total=9000),
    "watermelon" : dict(seed=2500, fertilizer=3000, pesticide=2000, labor=4000, irrigation=2500, total=16000),
    "muskmelon"  : dict(seed=2500, fertilizer=2500, pesticide=1800, labor=3500, irrigation=2000, total=14500),
    "papaya"     : dict(seed=3000, fertilizer=3500, pesticide=2500, labor=5000, irrigation=3000, total=18000),
    "coconut"    : dict(seed=3500, fertilizer=4000, pesticide=2500, labor=5500, irrigation=3500, total=21000),
    "bajra"      : dict(seed=1200, fertilizer=2000, pesticide=800,  labor=2500, irrigation=500,  total=8000),
    "jowar"      : dict(seed=1200, fertilizer=2000, pesticide=800,  labor=2500, irrigation=500,  total=8000),
    "sunflower"  : dict(seed=1500, fertilizer=2500, pesticide=1200, labor=2500, irrigation=1000, total=10000),
    "ragi"       : dict(seed=1000, fertilizer=1800, pesticide=700,  labor=2500, irrigation=400,  total=7500),
    "sesamum"    : dict(seed=1200, fertilizer=1800, pesticide=800,  labor=2500, irrigation=400,  total=8000),
    "safflower"  : dict(seed=1200, fertilizer=2000, pesticide=800,  labor=2000, irrigation=400,  total=7500),
    "mothbeans"  : dict(seed=1200, fertilizer=1500, pesticide=800,  labor=2000, irrigation=300,  total=7000),
    "kidneybeans": dict(seed=2000, fertilizer=2500, pesticide=1500, labor=3000, irrigation=800,  total=10500),
    "apple"      : dict(seed=4000, fertilizer=5000, pesticide=4000, labor=8000, irrigation=4000, total=28000),
}
DEFAULT_INPUT_COST = dict(seed=2000, fertilizer=3000, pesticide=2000, labor=4000, irrigation=1500, total=14000)


class RiskEngine:

    def score(
        self,
        crop: str,
        season: str,
        temp: float,
        humidity: float,
        rainfall: float,
        land: float,
        budget: float | None,
    ) -> dict:
        """
        Returns {total, level, breakdown} where each component is 0–100.
        Weights: weather 35%, market 30%, input_cost 20%, pest 15%.
        """
        w = self._weather_risk(crop, temp, rainfall, humidity)
        m = self._market_risk(crop)
        c = self._cost_risk(crop, land, budget)
        p = self._pest_risk(crop, season, temp, humidity)

        total = round(w * 0.35 + m * 0.30 + c * 0.20 + p * 0.15, 1)
        level = "LOW" if total <= 33 else "MEDIUM" if total <= 60 else "HIGH"

        return {
            "total"    : total,
            "level"    : level,
            "breakdown": {
                "weather"   : round(w, 1),
                "market"    : round(m, 1),
                "input_cost": round(c, 1),
                "pest"      : round(p, 1),
            },
        }

    def affordability(self, crop: str, land: float, budget: float | None) -> dict:
        """
        Budget affordability for the Flutter card.

        Returns:
          can_afford          bool
          input_cost          float   total ₹ for land_acres
          cost_per_acre       float
          budget_remaining    float   budget − input_cost  (negative = over budget)
          budget_ratio        float   input_cost / budget  (>1 = over budget)
          affordability_label str     human-readable label
        """
        cost_data    = INPUT_COSTS.get(crop.lower(), DEFAULT_INPUT_COST)
        input_cost   = round(cost_data["total"] * land, 0)
        cost_per_acre = cost_data["total"]

        if not budget:
            return {
                "can_afford"          : True,
                "input_cost"          : input_cost,
                "cost_per_acre"       : cost_per_acre,
                "budget_remaining"    : None,
                "budget_ratio"        : None,
                "affordability_label" : "No budget set",
            }

        ratio     = input_cost / budget
        remaining = round(budget - input_cost, 0)

        if ratio < 0.5:
            label, can = "Comfortably within budget", True
        elif ratio < 0.85:
            label, can = "Within your budget", True
        elif ratio < 1.0:
            label, can = "Within your upper budget", True
        elif ratio < 1.2:
            label, can = "Slightly over budget", False
        else:
            label, can = "Over budget", False

        return {
            "can_afford"          : can,
            "input_cost"          : input_cost,
            "cost_per_acre"       : cost_per_acre,
            "budget_remaining"    : remaining,
            "budget_ratio"        : round(ratio, 3),
            "affordability_label" : label,
        }

    # ── Weather risk (0–100) ─────────────────────────────────────────
    def _weather_risk(self, crop: str, temp: float, rainfall: float, humidity: float) -> float:
        p = CROP_PROFILES.get(crop.lower(), {})
        score = 0.0
        tlo, thi = p.get("temp", (20, 33))
        tmid = (tlo + thi) / 2
        if tlo <= temp <= thi:
            score += 0
        elif abs(temp - tmid) < 5:
            score += 20
        elif abs(temp - tmid) < 10:
            score += 50
        else:
            score += 85
        rlo, rhi = p.get("rain", (400, 1200))
        if rainfall < rlo * 0.4:   score += 60
        elif rainfall < rlo * 0.7: score += 35
        elif rainfall < rlo:       score += 15
        elif rainfall <= rhi:      score += 0
        elif rainfall <= rhi*1.3:  score += 20
        else:                      score += 55
        if humidity > 90:          score += 20
        elif humidity < 30:        score += 15
        return min(score, 100)

    # ── Market risk (0–100) ──────────────────────────────────────────
    def _market_risk(self, crop: str) -> float:
        info = MARKET_DATA.get(crop.lower())
        if not info:
            return 45.0
        trend, demand, oversupply, volatility = info
        trend_score    = {"UP": 10, "STABLE": 30, "DOWN": 70, "VOLATILE": 75}[trend]
        demand_score   = {"HIGH": 0, "MEDIUM": 25, "LOW": 60}[demand]
        oversupply_sc  = 35 if oversupply else 0
        raw = trend_score * 0.4 + demand_score * 0.3 + oversupply_sc * 0.15 + volatility * 0.15
        return min(raw, 100)

    # ── Input cost risk (0–100) ──────────────────────────────────────
    def _cost_risk(self, crop: str, land: float, budget: float | None) -> float:
        if not budget:
            return 40.0
        cost_data  = INPUT_COSTS.get(crop.lower(), DEFAULT_INPUT_COST)
        total_cost = cost_data["total"] * land
        ratio = total_cost / budget
        if ratio < 0.5:  return 5.0
        if ratio < 0.7:  return 15.0
        if ratio < 0.85: return 30.0
        if ratio < 1.0:  return 55.0
        if ratio < 1.2:  return 75.0
        return 95.0

    # ── Pest/disease risk (0–100) ────────────────────────────────────
    def _pest_risk(self, crop: str, season: str, temp: float, humidity: float) -> float:
        from services.pest_engine import PEST_RULES
        risk_map = {"HIGH": 80, "MEDIUM": 45, "LOW": 20}
        best = 10.0
        for (c, s, tlo, thi, hmin, pest, sev, _days) in PEST_RULES:
            if c.lower() != crop.lower():
                continue
            if s.lower() not in (season.lower(), "whole year"):
                continue
            if tlo <= temp <= thi and humidity >= hmin:
                best = max(best, float(risk_map.get(sev, 20)))
        return best