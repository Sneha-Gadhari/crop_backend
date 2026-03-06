"""
Soil Classifier — wraps the local Pixsoil SavedModel (11 classes).
Falls back to a colour-heuristic when the model isn't available.

Model architecture (confirmed from keras_metadata.pb):
  Input  : 256×256×3  float32  [0, 1]   (key: 'conv2d_62_input')
  Layers : 4× Conv2D(29 filters) + MaxPool → Flatten → Dense(29,29,29,11) → Softmax
  Output : 11 classes (softmax probabilities)

Pixsoil label order — from the JS export (DO NOT REORDER):
  0: alike       ← ambiguous / mixed signal  ┐
  1: clay                                     │ actual soil types
  2: dry rocky                                │
  3: grassy      ← vegetated surface          ├ non-soil context labels
  4: gravel                                   │
  5: humus                                    │
  6: loam                                     │
  7: not         ← non-soil image             ┘
  8: sandy
  9: silty
 10: yellow      ← laterite / iron-rich (Deccan / Konkan context)

Notes:
  • 'alike', 'grassy', 'not' are quality/context labels — not soil types.
    When the model predicts these the classifier uses the runner-up valid class
    or falls back to the colour heuristic.
  • 'yellow' = laterite in Maharashtra context (Konkan belt).
  • Model expects pixel_value / 255.0  — NO ImageNet mean/std normalisation.
"""

import io
import os
import numpy as np
from PIL import Image

# ── 11 Pixsoil class labels (JS export order — must not change) ───────
SOIL_LABELS: list[str] = [
    "alike",      # 0 — non-agronomic, triggers fallback
    "clay",       # 1
    "dry rocky",  # 2
    "grassy",     # 3 — non-agronomic, triggers fallback
    "gravel",     # 4
    "humus",      # 5
    "loam",       # 6
    "not",        # 7 — non-agronomic, triggers fallback
    "sandy",      # 8
    "silty",      # 9
    "yellow",     # 10
]

# Labels that are NOT real soil predictions → attempt runner-up or fallback
_INVALID_LABELS: set[str] = {"alike", "grassy", "not"}

# ── Agronomic profiles keyed on Pixsoil label ────────────────────────
# NPK in mg/kg (ppm), pH range, best crops for Maharashtra context.
# Sources: ICAR Soil Health Card norms, NBSS&LUP Maharashtra atlas,
#          Krishi Vigyan Kendra advisory bulletins.
SOIL_PROFILES: dict[str, dict] = {
    "clay": dict(
        display_name="Clay Soil",
        N=(50, 80), P=(35, 65), K=(70, 110), pH=(5.5, 7.5),
        crops=["Rice", "Jute", "Sugarcane", "Banana", "Taro"],
        description=(
            "Heavy texture, slow drainage, high water-holding capacity. "
            "Swells when wet. Good for water-intensive Kharif crops."
        ),
    ),
    "dry rocky": dict(
        display_name="Dry Rocky / Skeletal Soil",
        N=(10, 25), P=(5, 18), K=(20, 45), pH=(6.5, 8.0),
        crops=["Millet", "Sorghum", "Groundnut", "Castor", "Pulses"],
        description=(
            "Shallow depth over rock, poor moisture retention. "
            "Suited only to drought-tolerant crops with minimal inputs."
        ),
    ),
    "gravel": dict(
        display_name="Gravelly / Coarse Soil",
        N=(12, 28), P=(6, 20), K=(22, 50), pH=(6.5, 8.0),
        crops=["Millet", "Sorghum", "Groundnut", "Castor"],
        description=(
            "Coarse texture, very fast drainage, low fertility. "
            "Requires organic amendment and mulching."
        ),
    ),
    "humus": dict(
        display_name="Humus / Organic-Rich Soil",
        N=(100, 140), P=(60, 90), K=(100, 150), pH=(6.0, 7.5),
        crops=["Vegetables", "Maize", "Rice", "Groundnut", "Banana"],
        description=(
            "Dark, organic-rich, high CEC and biological activity. "
            "Very fertile; found near forest fringes and wetlands in Konkan."
        ),
    ),
    "loam": dict(
        display_name="Loamy Soil",
        N=(70, 110), P=(45, 75), K=(85, 130), pH=(6.0, 7.5),
        crops=["Wheat", "Maize", "Soybean", "Cotton", "Vegetables"],
        description=(
            "Ideal sand-silt-clay balance. Best water retention and drainage. "
            "Most versatile soil for Maharashtra crops."
        ),
    ),
    "sandy": dict(
        display_name="Sandy Soil",
        N=(15, 30), P=(8, 20), K=(25, 55), pH=(6.0, 7.5),
        crops=["Millet", "Groundnut", "Watermelon", "Muskmelon", "Castor"],
        description=(
            "Low water and nutrient retention, fast drainage. "
            "Requires heavy organic amendments and frequent irrigation."
        ),
    ),
    "silty": dict(
        display_name="Silty / Alluvial Soil",
        N=(80, 120), P=(40, 70), K=(90, 140), pH=(6.5, 8.0),
        crops=["Rice", "Wheat", "Sugarcane", "Maize", "Banana"],
        description=(
            "Fine particle size, excellent fertility, found along river plains "
            "(Krishna, Godavari basins). High natural N and K."
        ),
    ),
    "yellow": dict(
        display_name="Laterite / Yellow-Red Soil",
        N=(20, 42), P=(10, 26), K=(32, 62), pH=(5.0, 6.5),
        crops=["Cashew", "Coconut", "Rice", "Groundnut", "Mango"],
        description=(
            "Iron and aluminium-rich, heavily leached, acidic. "
            "Common in Konkan belt (Ratnagiri, Sindhudurg, Raigad). "
            "Needs lime and organic matter for most crops."
        ),
    ),
    # ── Fallback for truly unclassifiable images ──────────────────────
    "_unknown": dict(
        display_name="Mixed / Unknown Soil",
        N=(40, 70), P=(25, 50), K=(55, 95), pH=(6.0, 7.5),
        crops=["Sorghum", "Millet", "Groundnut", "Soybean"],
        description="Soil type could not be determined — values are average estimates.",
    ),
}

# Friendly short names for UI chips
SHORT_NAME: dict[str, str] = {
    "clay"       : "Clay",
    "dry rocky"  : "Dry Rocky",
    "gravel"     : "Gravelly",
    "humus"      : "Humus",
    "loam"       : "Loamy",
    "sandy"      : "Sandy",
    "silty"      : "Silty/Alluvial",
    "yellow"     : "Laterite",
    # context labels (shown only if everything fails)
    "alike"      : "Mixed",
    "grassy"     : "Vegetated Surface",
    "not"        : "Non-soil Image",
}

# Indices that ARE valid soil classes
_VALID_INDICES: list[int] = [
    i for i, lbl in enumerate(SOIL_LABELS) if lbl not in _INVALID_LABELS
]


class SoilClassifier:
    MODEL_PATH = "models/soil_model"

    def __init__(self):
        self.model   = None
        self._infer  = None   # cached serving_default callable
        self.source  = "color_heuristic"
        self._load()

    # ── Model loading ────────────────────────────────────────────────
    def _load(self):
        try:
            import tensorflow as tf
            if os.path.exists(self.MODEL_PATH):
                m = tf.saved_model.load(self.MODEL_PATH)
                self._infer = m.signatures["serving_default"]
                self.model  = m
                self.source = "pixsoil_local"
                print("✅ Pixsoil model loaded (11-class, 256×256 input)")
            else:
                print(f"⚠️  Pixsoil model not found at '{self.MODEL_PATH}'. "
                      "Colour heuristic will be used.")
        except Exception as e:
            print(f"⚠️  Pixsoil load error: {e}. Using colour heuristic.")

    # ── Public API ───────────────────────────────────────────────────
    def classify(self, image_bytes: bytes) -> dict:
        """Classify soil from raw image bytes. Returns a full result dict."""
        if self.model is not None:
            return self._run_model(image_bytes)
        return self._color_heuristic(image_bytes)

    # ── TF model inference ───────────────────────────────────────────
    def _run_model(self, image_bytes: bytes) -> dict:
        import tensorflow as tf
        try:
            img = (Image.open(io.BytesIO(image_bytes))
                   .convert("RGB")
                   .resize((256, 256), Image.BILINEAR))

            # Normalise to [0, 1] — no ImageNet mean/std
            arr = np.expand_dims(np.array(img, dtype=np.float32) / 255.0, axis=0)

            # Input signature key confirmed from saved_model.pb proto
            out_dict = self._infer(**{"conv2d_62_input": tf.constant(arr)})
            probs    = list(out_dict.values())[0].numpy()[0]   # shape (11,)

            # Model output is already softmax; verify sum ≈ 1
            if abs(probs.sum() - 1.0) > 0.05:
                probs = _softmax(probs)

            top_idx = int(probs.argmax())
            label   = SOIL_LABELS[top_idx]
            conf    = float(probs[top_idx]) * 100.0

            # If primary prediction is a context label, try best valid class
            if label in _INVALID_LABELS:
                best_valid = max(_VALID_INDICES, key=lambda i: probs[i])
                if probs[best_valid] >= 0.20:          # at least 20 % confidence
                    label = SOIL_LABELS[best_valid]
                    conf  = float(probs[best_valid]) * 100.0
                    print(f"  Context label predicted — using runner-up: {label} ({conf:.1f}%)")
                else:
                    print("  Low confidence on all valid soil labels — falling back to colour heuristic.")
                    return self._color_heuristic(image_bytes)

            return self._build_result(label, conf, "pixsoil_local")

        except Exception as e:
            print(f"Pixsoil inference error: {e}")
            return self._color_heuristic(image_bytes)

    # ── Colour heuristic fallback ─────────────────────────────────────
    # Tuned to map average RGB statistics to the 8 usable Pixsoil labels.
    def _color_heuristic(self, image_bytes: bytes) -> dict:
        img = (Image.open(io.BytesIO(image_bytes))
               .convert("RGB")
               .resize((64, 64)))
        arr        = np.array(img, dtype=np.float32)
        r, g, b    = arr[:, :, 0].mean(), arr[:, :, 1].mean(), arr[:, :, 2].mean()
        brightness = (r + g + b) / 3.0
        redness    = r / (g + 1)          # red-to-green ratio

        if brightness < 55:
            label, conf = "humus",      60.0   # very dark → organic/humus
        elif brightness < 75:
            label, conf = "clay",       62.0   # dark, moist clay
        elif redness > 1.4 and brightness < 130:
            label, conf = "yellow",     63.0   # iron-rich laterite
        elif redness > 1.2 and brightness > 130:
            label, conf = "dry rocky",  58.0   # pale reddish rocky
        elif brightness > 170 and r > 155 and g > 140:
            label, conf = "sandy",      60.0   # pale, uniform → sandy
        elif b > g and brightness < 130:
            label, conf = "clay",       60.0   # blue-grey → heavy clay
        elif g > r * 0.95 and 110 < brightness < 165:
            label, conf = "loam",       59.0   # balanced mid-brown
        elif 100 < brightness < 160 and abs(r - g) < 25:
            label, conf = "silty",      59.0   # uniform mid-tone → alluvial
        elif brightness < 100 and redness < 1.1:
            label, conf = "gravel",     55.0   # dark coarse
        else:
            label, conf = "loam",       52.0   # safe fallback

        return self._build_result(label, conf, "color_heuristic")

    # ── Result builder ───────────────────────────────────────────────
    def _build_result(self, label: str, conf: float, source: str) -> dict:
        profile  = SOIL_PROFILES.get(label, SOIL_PROFILES["_unknown"])
        n_mid    = (profile["N"][0] + profile["N"][1]) // 2
        p_mid    = (profile["P"][0] + profile["P"][1]) // 2
        k_mid    = (profile["K"][0] + profile["K"][1]) // 2
        ph_mid   = round((profile["pH"][0] + profile["pH"][1]) / 2, 1)
        return {
            "soil_type"       : profile["display_name"],
            "soil_label"      : label,
            "soil_type_short" : SHORT_NAME.get(label, profile["display_name"]),
            "confidence"      : round(conf, 1),
            "description"     : profile["description"],
            "estimated_N"     : n_mid,
            "estimated_P"     : p_mid,
            "estimated_K"     : k_mid,
            "estimated_pH"    : ph_mid,
            "n_range"         : list(profile["N"]),
            "p_range"         : list(profile["P"]),
            "k_range"         : list(profile["K"]),
            "ph_range"        : list(profile["pH"]),
            "best_crops"      : profile["crops"],
            "source"          : source,
        }


# ── Utility ───────────────────────────────────────────────────────────
def _softmax(x: np.ndarray) -> np.ndarray:
    e = np.exp(x - x.max())
    return e / e.sum()