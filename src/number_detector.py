"""
number_detector.py  -  Detect denomination number via region-based
template matching on the rectified banknote image.

Uses real templates (cropped from sample banknote images) of the
bottom-right number region.  Matching is done with normalised
cross-correlation (TM_CCOEFF_NORMED) directly on grayscale, which
captures the unique layout of each denomination's number area.

Fallback: synthetic templates are tried only when no real template
matches above threshold, ensuring robust detection when real
templates are available.
"""

import os
import cv2
import numpy as np

from config import DENOMINATIONS, NUMBER_ROI, TEMPLATE_MATCH_THRESHOLD, TEMPLATE_DIR

TEMPLATE_DIR = os.path.join(os.path.dirname(__file__), "..", TEMPLATE_DIR)

# Cache: {value: grayscale_template}
_cache: dict[int, np.ndarray] = {}


def _load_templates() -> dict[int, np.ndarray]:
    result = {}
    for d in DENOMINATIONS:
        val = d["value"]
        if val in _cache:
            result[val] = _cache[val]
            continue
        path = os.path.join(TEMPLATE_DIR, f"{val}.png")
        if not os.path.exists(path):
            continue
        img = cv2.imread(path, cv2.IMREAD_GRAYSCALE)
        if img is None:
            continue
        _cache[val] = img
        result[val] = img
    return result


def _crop_roi(warped: np.ndarray,
              roi: tuple[float, float, float, float] | None = None) -> np.ndarray | None:
    if roi is None:
        roi = NUMBER_ROI
    h, w = warped.shape[:2]
    x1 = max(0, int(w * roi[0]))
    y1 = max(0, int(h * roi[1]))
    x2 = min(w, int(w * roi[2]))
    y2 = min(h, int(h * roi[3]))
    if x2 <= x1 or y2 <= y1:
        return None
    return cv2.cvtColor(warped[y1:y2, x1:x2], cv2.COLOR_BGR2GRAY)


def _match_against_all(roi: np.ndarray,
                       templates: dict[int, np.ndarray],
                       scales: list[float],
                       ) -> tuple[int | None, float]:
    """Run template matching for all templates at all given scales."""
    best_val: int | None = None
    best_score = -1.0
    roi_h, roi_w = roi.shape

    for val, tmpl in sorted(templates.items(), key=lambda x: -x[0]):
        th, tw = tmpl.shape
        for scale in scales:
            sw, sh = int(tw * scale), int(th * scale)
            if sw < 10 or sh < 10 or sw > roi_w or sh > roi_h:
                continue
            scaled = cv2.resize(tmpl, (sw, sh), interpolation=cv2.INTER_AREA)
            _, max_val, _, _ = cv2.minMaxLoc(
                cv2.matchTemplate(roi, scaled, cv2.TM_CCOEFF_NORMED)
            )
            if max_val > best_score:
                best_score = float(max_val)
                best_val = val
        # Early exit
        if best_score > 0.90:
            break
    return best_val, best_score


def detect_number(warped: np.ndarray) -> tuple[int | None, float]:
    """Standard detection — fast, single ROI, coarse-to-fine scales."""
    templates = _load_templates()
    if not templates:
        return None, 0.0

    roi = _crop_roi(warped)
    if roi is None or roi.shape[0] < 20 or roi.shape[1] < 20:
        return None, 0.0

    coarse = [0.7, 0.85, 1.0, 1.15, 1.3]
    fine   = [0.78, 0.92, 1.08, 1.22]

    # Coarse pass
    best_val, best_score = _match_against_all(roi, templates, coarse)

    # Fine pass around the winning scale from coarse (approximate:
    # re-run with the combined scale list for simplicity)
    if best_score > 0:
        combined = sorted(set(coarse + fine))
        best_val, best_score = _match_against_all(roi, templates, combined)

    if best_score < TEMPLATE_MATCH_THRESHOLD:
        return None, best_score
    return best_val, best_score


def detect_number_enhanced(warped: np.ndarray) -> tuple[int | None, float]:
    """
    Enhanced detection for snapshot mode.
    - More scales (denser coverage).
    - Tries ROI shifts (±2%) to compensate for rectification imprecision.
    """
    templates = _load_templates()
    if not templates:
        return None, 0.0

    # Dense scale coverage   (12 scales instead of coarse-to-fine 9)
    scales = [0.55, 0.65, 0.75, 0.85, 0.92, 1.0,
              1.08, 1.15, 1.25, 1.35, 1.45, 1.55]

    # ROI shifts: sliding window around the nominal position
    dxs = [-0.02, 0.0, 0.02]
    dys = [-0.02, 0.0, 0.02]

    best_val: int | None = None
    best_score = -1.0

    for dx in dxs:
        for dy in dys:
            shifted = (NUMBER_ROI[0] + dx, NUMBER_ROI[1] + dy,
                       NUMBER_ROI[2] + dx, NUMBER_ROI[3] + dy)
            roi = _crop_roi(warped, shifted)
            if roi is None or roi.shape[0] < 20 or roi.shape[1] < 20:
                continue
            val, score = _match_against_all(roi, templates, scales)
            if score > best_score:
                best_score = score
                best_val = val
                if best_score > 0.92:  # very confident
                    break
        if best_score > 0.92:
            break

    if best_score < TEMPLATE_MATCH_THRESHOLD:
        return None, best_score
    return best_val, best_score
