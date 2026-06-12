# classifier.py - Denomination classification (number-first, color-secondary)

from config import (
    DENOMINATIONS,
    ASPECT_RATIO_TOLERANCE,
    MIN_HUE_PIXEL_FRACTION,
    HUE_PEAK_MARGIN,
    AUTO_CALIBRATE,
    TEMPLATE_MATCH_THRESHOLD,
    NUMBER_WEIGHT,
    COLOR_WEIGHT,
)
from feature_extractor import get_dominant_hue, compute_hue_fraction
from calibrator import get_hue_ranges, record_hue, save_calibration
from number_detector import detect_number, detect_number_enhanced


class ClassificationResult:
    def __init__(self, denomination=None, is_authentic=False, is_suspicious=False,
                 is_unrecognized=False, confidence_geo=0.0, confidence_color=0.0,
                 confidence_total=0.0, debug_info=None):
        self.denomination = denomination
        self.is_authentic = is_authentic
        self.is_suspicious = is_suspicious
        self.is_unrecognized = is_unrecognized
        self.confidence_geo = confidence_geo
        self.confidence_color = confidence_color
        self.confidence_total = confidence_total
        self.debug_info = debug_info or {}

    def get_label(self) -> str:
        if self.is_unrecognized:
            reason = self.debug_info.get("reason", "")
            if reason == "no_contour":
                return "Uang Tidak Terlihat, Dekatkan Kamera"
            if reason == "rectification_failed":
                return "Posisi Tidak Terbaca, Coba Lagi"
            return "Uang Tidak Dikenali atau Palsu"
        name = self.denomination["label_id"] if self.denomination else "Tidak Diketahui"
        if self.is_suspicious:
            return f"{name}, Mencurigakan atau Palsu"
        if self.is_authentic:
            return f"{name}, Asli"
        return "Hasil Tidak Tersedia"


def _hue_in_ranges(hue: int, hue_ranges: list, margin: int = 0) -> bool:
    for h_min, h_max in hue_ranges:
        lo = max(0, h_min - margin)
        hi = min(179, h_max + margin)
        if lo <= hue <= hi:
            return True
    return False


def _hue_distance(h1: int, h2: int) -> int:
    d = abs(h1 - h2)
    return min(d, 180 - d)


def _ar_score(measured: float, target: float) -> float:
    dist = abs(measured - target)
    return max(0.0, 1.0 - dist / ASPECT_RATIO_TOLERANCE)


def _color_score_for(warped_image, denom: dict) -> float:
    """Compute combined color score (0.0–1.0) for a single denomination."""
    hue_ranges = get_hue_ranges(denom["value"], denom["hue_ranges"])
    min_sat = denom["min_saturation"]
    max_sat = denom["max_saturation"]

    dh = get_dominant_hue(warped_image, min_saturation=min_sat, max_saturation=max_sat)
    dom_ok = (dh is not None and _hue_in_ranges(dh, hue_ranges, margin=HUE_PEAK_MARGIN))

    frac = compute_hue_fraction(warped_image, hue_ranges, min_sat, max_sat)
    frac_ok = frac >= MIN_HUE_PIXEL_FRACTION

    if dom_ok or frac_ok:
        return min(1.0, max(dom_ok * 0.6, frac))
    return 0.0


def classify(warped_image, features: dict,
             snapshot_mode: bool = False) -> ClassificationResult:
    ar = features["aspect_ratio"]

    # --- STEP 1: Number detection (primary) ---
    num_value, num_conf = (detect_number_enhanced(warped_image)
                           if snapshot_mode else detect_number(warped_image))
    num_denom = None
    if num_value is not None:
        num_denom = next((d for d in DENOMINATIONS if d["value"] == num_value), None)

    # --- STEP 2: Color scoring (secondary) ---
    best_denom = None
    best_score = -1.0
    best_info = {}

    if num_denom is not None and num_conf >= TEMPLATE_MATCH_THRESHOLD:
        color_s = _color_score_for(warped_image, num_denom)
        ar_s = _ar_score(ar, num_denom["aspect_ratio"])

        # Cross-validation: if AR completely disagrees, number is false positive.
        # AR distance > 0.0225 means ar_s < 0.1 — impossible for the claimed
        # denomination given TE 2022's 5 mm step (min ΔAR ≈ 0.077).
        if ar_s < 0.1:
            num_denom = None  # force fallback to AR + color

    if num_denom is not None and num_conf >= TEMPLATE_MATCH_THRESHOLD:
        # Number detected & cross-validated: use as primary, color as verification
        combined = num_conf * NUMBER_WEIGHT + color_s * COLOR_WEIGHT
        if ar_s > 0.5:
            combined = combined * 0.85 + ar_s * 0.15

        best_denom = num_denom
        best_score = combined
        best_info = {
            "measured_ar": round(ar, 5),
            "target_ar": round(num_denom["aspect_ratio"], 5),
            "dominant_hue": get_dominant_hue(warped_image, min_saturation=30, max_saturation=255),
            "number_match": True,
            "number_value": num_value,
            "number_confidence": round(num_conf, 4),
            "color_score": round(color_s, 4),
            "ar_score": round(ar_s, 4),
            "combined": round(combined, 4),
        }

    else:
        # Number not detected or rejected by cross-validation: fallback to AR + color
        for d in DENOMINATIONS:
            ar_s = _ar_score(ar, d["aspect_ratio"])
            color_s = _color_score_for(warped_image, d)
            combined = ar_s * (0.6 + 0.4 * color_s)

            if combined > best_score:
                best_score = combined
                best_denom = d
                best_info = {
                    "measured_ar": round(ar, 5),
                    "target_ar": round(d["aspect_ratio"], 5),
                    "dominant_hue": get_dominant_hue(warped_image, min_saturation=30, max_saturation=255),
                    "number_match": False,
                    "number_value": None,
                    "number_confidence": round(num_conf, 4),
                    "color_score": round(color_s, 4),
                    "ar_score": round(ar_s, 4),
                    "combined": round(combined, 4),
                }

    if best_denom is None or best_score < 0.01:
        return ClassificationResult(
            is_unrecognized=True,
            debug_info={
                "reason": "no_match",
                "measured_ar": round(ar, 4),
                "number_confidence": round(num_conf, 4),
            },
        )

    # Record hue for auto-calibration when confident
    if AUTO_CALIBRATE and best_info.get("color_score", 0) > 0.3 and best_score > 0.4:
        hue_val = best_info.get("dominant_hue")
        if hue_val is not None:
            record_hue(best_denom["value"], hue_val)
            save_calibration()

    # Authenticity: need color match AND good overall score
    colour_ok = best_info.get("color_score", 0) > 0.15
    number_ok = best_info.get("number_match", False) and best_info.get("number_confidence", 0) > 0.3
    is_auth = (colour_ok or number_ok) and best_score > 0.2

    return ClassificationResult(
        denomination=best_denom,
        is_authentic=is_auth,
        is_suspicious=not is_auth,
        confidence_geo=best_info.get("ar_score", 0),
        confidence_color=best_info.get("color_score", 0),
        confidence_total=best_score,
        debug_info=best_info,
    )
