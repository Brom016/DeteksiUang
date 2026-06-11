# classifier.py - Denomination classification

from config import DENOMINATIONS, ASPECT_RATIO_TOLERANCE, MIN_HUE_PIXEL_FRACTION, HUE_PEAK_MARGIN, AUTO_CALIBRATE
from feature_extractor import get_dominant_hue, compute_hue_fraction
from calibrator import get_hue_ranges, record_hue, save_calibration


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
    # Score 1.0 at exact match, decays to 0 at ±0.06
    dist = abs(measured - target)
    return max(0.0, 1.0 - dist / 0.06)


def classify(warped_image, features: dict) -> ClassificationResult:
    ar = features["aspect_ratio"]

    # Extract dominant hue for color matching
    dom_hue = get_dominant_hue(warped_image, min_saturation=30, max_saturation=255)

    best_denom = None
    best_score = -1
    best_info = {}
    has_any_color_match = False

    for d in DENOMINATIONS:
        hue_ranges = get_hue_ranges(d["value"], d["hue_ranges"])
        min_sat = d["min_saturation"]
        max_sat = d["max_saturation"]

        # AR score
        ar_s = _ar_score(ar, d["aspect_ratio"])

        # Color check: dominant hue
        dh = get_dominant_hue(warped_image, min_saturation=min_sat, max_saturation=max_sat)
        dom_ok = (dh is not None and _hue_in_ranges(dh, hue_ranges, margin=HUE_PEAK_MARGIN))

        # Color check: pixel fraction
        frac = compute_hue_fraction(warped_image, hue_ranges, min_sat, max_sat)
        frac_ok = frac >= MIN_HUE_PIXEL_FRACTION

        # Combined color score
        if dom_ok or frac_ok:
            color_score = min(1.0, max(dom_ok * 0.6, frac))
        else:
            color_score = 0.0

        # Final combined
        combined = ar_s * (0.5 + 0.5 * color_score)

        if combined > best_score:
            best_score = combined
            best_denom = d
            best_info = {
                "measured_ar": round(ar, 5),
                "target_ar": round(d["aspect_ratio"], 5),
                "dominant_hue": dh,
                "dom_ok": dom_ok,
                "pixel_fraction": round(frac, 4),
                "frac_ok": frac_ok,
                "color_match": color_score > 0,
                "ar_score": round(ar_s, 4),
                "color_score": round(color_score, 4),
                "combined": round(combined, 4),
            }

        if color_score > 0:
            has_any_color_match = True

    if best_denom is None or best_score < 0.01:
        return ClassificationResult(
            is_unrecognized=True,
            debug_info={"reason": "no_match", "measured_ar": round(ar, 4)},
        )

    # Record hue for auto-calibration when confident
    if AUTO_CALIBRATE and best_info.get("color_match") and best_info.get("ar_score", 0) > 0.5:
        hue_val = best_info.get("dominant_hue")
        if hue_val is not None:
            record_hue(best_denom["value"], hue_val)
            save_calibration()

    is_auth = best_info["color_match"] and best_score > 0.15

    return ClassificationResult(
        denomination=best_denom,
        is_authentic=is_auth,
        is_suspicious=not is_auth,
        confidence_geo=best_info.get("ar_score", 0),
        confidence_color=best_info.get("color_score", 0),
        confidence_total=best_score,
        debug_info=best_info,
    )
