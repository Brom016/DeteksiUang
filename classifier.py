"""
classifier.py  -  Denomination classification with dual color verification.

Color check now uses TWO independent methods:
  1. Dominant hue peak falls within (or near) the expected range
  2. Pixel fraction exceeds threshold

Color passes if EITHER method agrees.
This reduces false "Mencurigakan" verdicts caused by partial lighting issues.
"""

from config import (
    DENOMINATIONS,
    ASPECT_RATIO_TOLERANCE,
    MIN_HUE_PIXEL_FRACTION,
    HUE_PEAK_MARGIN,
    REQUIRE_BOTH_FEATURES,
)
from feature_extractor import get_dominant_hue, compute_hue_fraction


class ClassificationResult:
    def __init__(
        self,
        denomination=None,
        is_authentic=False,
        is_suspicious=False,
        is_unrecognized=False,
        confidence_geo=0.0,
        confidence_color=0.0,
        debug_info=None,
    ):
        self.denomination = denomination
        self.is_authentic = is_authentic
        self.is_suspicious = is_suspicious
        self.is_unrecognized = is_unrecognized
        self.confidence_geo = confidence_geo
        self.confidence_color = confidence_color
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

    def __repr__(self) -> str:
        return (
            f"ClassificationResult(label='{self.get_label()}', "
            f"geo={self.confidence_geo:.3f}, color={self.confidence_color:.3f})"
        )


def _hue_in_ranges(hue: int, hue_ranges: list, margin: int = 0) -> bool:
    """Check if a hue value (0-179) falls within any of the given ranges."""
    for h_min, h_max in hue_ranges:
        lo = max(0, h_min - margin)
        hi = min(179, h_max + margin)
        if lo <= hue <= hi:
            return True
    return False


def _match_by_aspect_ratio(ar: float):
    best, best_dist = None, float("inf")
    for d in DENOMINATIONS:
        dist = abs(ar - d["aspect_ratio"])
        if dist < ASPECT_RATIO_TOLERANCE and dist < best_dist:
            best_dist = dist
            best = d
    if best is None:
        return None, 0.0
    return best, 1.0 - best_dist / ASPECT_RATIO_TOLERANCE


def classify(warped_image, features: dict) -> ClassificationResult:
    ar = features["aspect_ratio"]
    geo_match, geo_conf = _match_by_aspect_ratio(ar)

    debug = {
        "measured_ar": round(ar, 5),
        "geo_match": geo_match["value"] if geo_match else None,
        "geo_confidence": round(geo_conf, 4),
    }

    if geo_match is None:
        debug["reason"] = "no_ar_match"
        return ClassificationResult(is_unrecognized=True, debug_info=debug)

    min_sat = geo_match["min_saturation"]
    max_sat = geo_match["max_saturation"]

    # --- Color check 1: dominant hue peak ---
    dom_hue = get_dominant_hue(warped_image, min_saturation=min_sat, max_saturation=max_sat)
    dom_ok = (dom_hue is not None and
              _hue_in_ranges(dom_hue, geo_match["hue_ranges"], margin=HUE_PEAK_MARGIN))

    # --- Color check 2: pixel fraction ---
    frac = compute_hue_fraction(warped_image, geo_match["hue_ranges"], min_sat, max_sat)
    frac_ok = frac >= MIN_HUE_PIXEL_FRACTION

    color_match = dom_ok or frac_ok

    debug.update({
        "target_ar": round(geo_match["aspect_ratio"], 5),
        "dominant_hue": dom_hue,
        "dom_hue_ok": dom_ok,
        "pixel_fraction": round(frac, 4),
        "frac_ok": frac_ok,
        "color_match": color_match,
    })

    if REQUIRE_BOTH_FEATURES:
        if color_match:
            return ClassificationResult(
                denomination=geo_match, is_authentic=True,
                confidence_geo=geo_conf, confidence_color=frac,
                debug_info=debug,
            )
        return ClassificationResult(
            denomination=geo_match, is_suspicious=True,
            confidence_geo=geo_conf, confidence_color=frac,
            debug_info=debug,
        )

    return ClassificationResult(
        denomination=geo_match, is_authentic=True,
        confidence_geo=geo_conf, confidence_color=frac,
        debug_info=debug,
    )