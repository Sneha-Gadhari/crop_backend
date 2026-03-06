"""
services/crop_recommender.py
────────────────────────────
Backend service for the Sheshank2609/crop-recommendation-system HuggingFace Space.

Combines two models:
  Model 1 — NPK / soil & climate  (Random Forest, Crop_recommendation.csv)
             Input  : 7 raw features [N, P, K, temperature, humidity, ph, rainfall]
             Output : probability over ~22 crop classes (no scaling needed)
             Files  : model1_npk.pkl, model1_label_encoder.pkl

  Model 2 — Regional suitability  (weighted scoring, 26 yrs Maharashtra district data)
             Input  : district name + season string
             Output : Suitability_Score per crop from model2_full_scored.csv
             Extras : Recommendation label, Crop_Freq_Pct, Avg_Yield (t/ha)

Combined score = w_npk × Model1_prob + (1 − w_npk) × Model2_score

Local cache: models/crop_model/
Files are downloaded from HuggingFace at first startup and cached locally.
"""

import os
import shutil
import numpy as np
import pandas as pd
import joblib

# ── Emoji map ─────────────────────────────────────────────────────────────────
CROP_EMOJI: dict[str, str] = {
    # Model 1 crops (lowercase label_enc.classes_ values)
    "rice"        : "🌾", "maize"       : "🌽", "cotton"      : "🌿",
    "jute"        : "🌿", "coconut"     : "🥥", "papaya"      : "🍈",
    "orange"      : "🍊", "apple"       : "🍎", "mango"       : "🥭",
    "banana"      : "🍌", "grapes"      : "🍇", "watermelon"  : "🍉",
    "muskmelon"   : "🍈", "pomegranate" : "🍎", "lentil"      : "🫘",
    "blackgram"   : "🫘", "mungbean"    : "🫘", "mothbeans"   : "🫘",
    "pigeonpeas"  : "🫘", "kidneybeans" : "🫘", "chickpea"    : "🫘",
    "coffee"      : "☕",
    # Model 2 crops (Maharashtra regional dataset)
    "wheat"       : "🌾", "jowar"       : "🌾", "bajra"       : "🌾",
    "gram"        : "🫘", "arhar/tur"   : "🫘", "soyabean"    : "🫘",
    "soybean"     : "🫘", "groundnut"   : "🥜", "sunflower"   : "🌻",
    "sugarcane"   : "🎋", "onion"       : "🧅", "tomato"      : "🍅",
    "ragi"        : "🌾", "urad"        : "🫘", "sesamum"     : "🌿",
    "safflower"   : "🌼", "linseed"     : "🌼",
}

# ── Local cache paths ─────────────────────────────────────────────────────────
_MODEL_DIR    = "models/crop_model"
_M1_MODEL     = os.path.join(_MODEL_DIR, "model1_npk.pkl")
_M1_ENCODER   = os.path.join(_MODEL_DIR, "model1_label_encoder.pkl")
_M2_CSV       = os.path.join(_MODEL_DIR, "model2_full_scored.csv")

_HF_REPO = "Sheshank2609/crop-recommendation-system"


def _norm(name: str) -> str:
    """Normalise crop name for cross-model matching (same logic as reference file)."""
    return (str(name).strip().lower()
            .replace(" ", "").replace("(", "").replace(")", "")
            .replace("-", "").replace("/", "").replace("&", ""))


class CropRecommender:
    """
    Dual-model crop recommender:
      Model 1 scores crops on soil/climate fit (NPK Random Forest).
      Model 2 scores crops on historical regional suitability (Maharashtra 26-year data).
      Combined score = w_npk × M1 + (1 − w_npk) × M2.

    Usage
    -----
    rec = CropRecommender()
    results = rec.recommend(
        N=90, P=42, K=43, temperature=25, humidity=80, ph=6.5, rainfall=200,
        district="Akola", season="Kharif",
        w_npk=0.4, top_n=3,
    )
    """

    def __init__(self, hf_token: str = ""):
        self.model1    = None   # sklearn RandomForestClassifier
        self.label_enc = None   # LabelEncoder  (classes_ = lowercase crop strings)
        self.model2_df = None   # pd.DataFrame  (regional scoring table)
        self.source    = "mock"
        self._token    = hf_token or None
        self._load()

    # ── Loader ────────────────────────────────────────────────────────────────
    def _load(self):
        if self._load_local():
            return
        self._load_hf()

    def _load_local(self) -> bool:
        if all(os.path.exists(f) for f in [_M1_MODEL, _M1_ENCODER, _M2_CSV]):
            try:
                self.model1    = joblib.load(_M1_MODEL)
                self.label_enc = joblib.load(_M1_ENCODER)
                self.model2_df = pd.read_csv(_M2_CSV)
                self.source    = f"local:{_MODEL_DIR}"
                n_districts    = self.model2_df["District"].nunique()
                n_crops        = len(self.label_enc.classes_)
                print(f"✅ Crop models loaded from local cache "
                      f"({n_crops} NPK crops, {n_districts} districts in Model 2)")
                return True
            except Exception as e:
                print(f"⚠️  Local crop model load failed: {e}")
        return False

    def _load_hf(self):
        try:
            from huggingface_hub import hf_hub_download
            kw = {"repo_id": _HF_REPO, "token": self._token}

            m1_path  = hf_hub_download(**kw, filename="model1_npk.pkl")
            enc_path = hf_hub_download(**kw, filename="model1_label_encoder.pkl")
            csv_path = hf_hub_download(**kw, filename="model2_full_scored.csv")

            self.model1    = joblib.load(m1_path)
            self.label_enc = joblib.load(enc_path)
            self.model2_df = pd.read_csv(csv_path)
            self.source    = _HF_REPO

            # Cache locally for offline use
            os.makedirs(_MODEL_DIR, exist_ok=True)
            for src, dst in [(m1_path, _M1_MODEL), (enc_path, _M1_ENCODER), (csv_path, _M2_CSV)]:
                if src != dst:
                    shutil.copy2(src, dst)

            print(f"✅ Crop models downloaded from {_HF_REPO} and cached.")
        except Exception as e:
            print(f"⚠️  Crop model unavailable: {e}. Mock predictions will be used.")

    # ── Model 1: soil/climate probabilities ───────────────────────────────────
    def _m1_scores(
        self,
        N: float, P: float, K: float,
        temperature: float, humidity: float,
        ph: float, rainfall: float,
    ) -> dict[str, float]:
        """
        Returns { crop_name (str) : probability (float) } for all Model 1 classes.
        Raw feature input — no scaling needed (model trained on raw values).
        """
        if self.model1 is None:
            return {}
        features = np.array([[N, P, K, temperature, humidity, ph, rainfall]])
        proba    = self.model1.predict_proba(features)[0]
        # label_enc.classes_ contains lowercase strings e.g. "rice", "maize"
        return dict(zip(self.label_enc.classes_, proba.tolist()))

    # ── Model 2: regional suitability scores ──────────────────────────────────
    def _m2_scores(self, district: str, season: str) -> dict[str, float]:
        """
        Returns { crop_name (str) : suitability_score (float 0–1) }
        for all crops historically recorded in this district/season.
        """
        if self.model2_df is None:
            return {}
        mask = (
            (self.model2_df["District"] == district) &
            (self.model2_df["Season"]   == season)
        )
        region = self.model2_df[mask]
        return dict(zip(region["Crop"], region["Suitability_Score"].astype(float)))

    # ── Combined recommendation ───────────────────────────────────────────────
    def recommend(
        self,
        # Soil & climate (Model 1 inputs)
        N: float, P: float, K: float,
        temperature: float, humidity: float,
        ph: float, rainfall: float,
        # Location context (Model 2 inputs)
        district: str = "",
        season  : str = "Kharif",
        # Blend weights
        w_npk: float = 0.4,
        top_n: int   = 3,
    ) -> list[dict]:
        """
        Returns a ranked list of top_n crop dicts.

        Each dict contains:
            crop_name     str    display name (title-cased)
            emoji         str    crop emoji
            confidence    float  combined score as % (0–100)
            npk_score     float  Model 1 probability as %
            region_score  float  Model 2 suitability as %
            suitability   str    "Highly Suitable" / "Moderately Suitable" / etc.
            grown_pct     float  % of years this crop was grown in this district
            avg_yield     float  average yield in t/ha for this district
        """
        if self.model1 is None:
            return self._mock(season)

        w_region = round(1.0 - w_npk, 4)

        m1 = self._m1_scores(N, P, K, temperature, humidity, ph, rainfall)
        m2 = self._m2_scores(district, season)

        # Normalised lookup for cross-model name matching
        m1_norm = {_norm(k): (k, v) for k, v in m1.items()}
        m2_norm = {_norm(k): (k, v) for k, v in m2.items()}

        rows = []
        for key in set(m1_norm) | set(m2_norm):
            _, s1             = m1_norm.get(key, (key, 0.0))
            crop_display, s2  = m2_norm.get(key, (key, 0.0))
            if key not in m2_norm:
                crop_display = m1_norm[key][0].title()

            combined = round(w_npk * s1 + w_region * s2, 6)

            # Pull extra detail from Model 2 table (single matching row)
            r = pd.DataFrame()
            if self.model2_df is not None and district:
                r = self.model2_df[
                    (self.model2_df["District"] == district) &
                    (self.model2_df["Season"]   == season)   &
                    (self.model2_df["Crop"].apply(_norm) == key)
                ]

            rows.append({
                "crop_name"   : crop_display,
                "emoji"       : CROP_EMOJI.get(_norm(crop_display), "🌾"),
                "confidence"  : round(combined * 100, 1),
                "npk_score"   : round(s1 * 100, 1),
                "region_score": round(s2 * 100, 1),
                "suitability" : r["Recommendation"].values[0]              if not r.empty else "No regional data",
                "grown_pct"   : round(float(r["Crop_Freq_Pct"].values[0]), 1) if not r.empty else 0.0,
                "avg_yield"   : round(float(r["Avg_Yield"].values[0]),     2) if not r.empty else 0.0,
            })

        return sorted(rows, key=lambda x: x["confidence"], reverse=True)[:top_n]

    # ── Season-aware mock fallback ────────────────────────────────────────────
    def _mock(self, season: str = "Kharif") -> list[dict]:
        """Realistic Maharashtra mock for when models are unavailable."""
        if season == "Rabi":
            return [
                {"crop_name": "Wheat",    "emoji": "🌾", "confidence": 88.0,
                 "npk_score": 0.0, "region_score": 88.0,
                 "suitability": "Highly Suitable",     "grown_pct": 72.4, "avg_yield": 1.48},
                {"crop_name": "Gram",     "emoji": "🫘", "confidence": 74.0,
                 "npk_score": 0.0, "region_score": 74.0,
                 "suitability": "Moderately Suitable", "grown_pct": 58.1, "avg_yield": 0.88},
                {"crop_name": "Onion",    "emoji": "🧅", "confidence": 61.0,
                 "npk_score": 0.0, "region_score": 61.0,
                 "suitability": "Moderately Suitable", "grown_pct": 44.5, "avg_yield": 12.4},
            ]
        if season in ("Zaid", "Summer"):
            return [
                {"crop_name": "Maize",      "emoji": "🌽", "confidence": 85.0,
                 "npk_score": 85.0, "region_score": 0.0,
                 "suitability": "No regional data", "grown_pct": 0.0, "avg_yield": 0.0},
                {"crop_name": "Watermelon", "emoji": "🍉", "confidence": 70.0,
                 "npk_score": 70.0, "region_score": 0.0,
                 "suitability": "No regional data", "grown_pct": 0.0, "avg_yield": 0.0},
                {"crop_name": "Mungbean",   "emoji": "🫘", "confidence": 58.0,
                 "npk_score": 58.0, "region_score": 0.0,
                 "suitability": "No regional data", "grown_pct": 0.0, "avg_yield": 0.0},
            ]
        # Kharif default
        return [
            {"crop_name": "Soyabean", "emoji": "🫘", "confidence": 91.0,
             "npk_score": 0.0, "region_score": 91.0,
             "suitability": "Highly Suitable",     "grown_pct": 96.2, "avg_yield": 0.92},
            {"crop_name": "Cotton",   "emoji": "🌿", "confidence": 76.0,
             "npk_score": 0.0, "region_score": 76.0,
             "suitability": "Moderately Suitable", "grown_pct": 84.6, "avg_yield": 1.46},
            {"crop_name": "Rice",     "emoji": "🌾", "confidence": 63.0,
             "npk_score": 63.0, "region_score": 0.0,
             "suitability": "No regional data",    "grown_pct": 0.0,  "avg_yield": 0.0},
        ]

    # ── UI helpers ────────────────────────────────────────────────────────────
    @property
    def districts(self) -> list[str]:
        """All districts available in Model 2 (for dropdown population)."""
        if self.model2_df is None:
            return []
        return sorted(self.model2_df["District"].unique().tolist())

    @property
    def seasons(self) -> list[str]:
        """All seasons available in Model 2 (for dropdown population)."""
        if self.model2_df is None:
            return []
        return sorted(self.model2_df["Season"].unique().tolist())