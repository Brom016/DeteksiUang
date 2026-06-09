"""
preprocessor.py  -  Improved image preparation and banknote contour detection.

Key improvements over v1:
  - CLAHE (local contrast enhancement) handles uneven / dim lighting
  - Bilateral filter preserves sharp edges while reducing texture noise
  - Adaptive Canny: thresholds auto-calculated from Otsu's method
  - Contour validation includes aspect-ratio plausibility check
  - Fallback to Otsu global threshold when Canny produces no useful contours
"""

import cv2
import numpy as np

from config import (
    MIN_CONTOUR_AREA_RATIO,
    MAX_CONTOUR_AREA_RATIO,
    MIN_SHAPE_AR,
    MAX_SHAPE_AR,
)

_CLAHE = cv2.createCLAHE(clipLimit=2.5, tileGridSize=(8, 8))


def preprocess(image: np.ndarray) -> np.ndarray:
    """
    Convert to grayscale, enhance local contrast, and apply bilateral filter.
    Bilateral preserves the banknote's outer edge while smoothing internal texture.
    """
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    enhanced = _CLAHE.apply(gray)
    filtered = cv2.bilateralFilter(enhanced, d=9, sigmaColor=75, sigmaSpace=75)
    return filtered


def _adaptive_canny(gray: np.ndarray) -> np.ndarray:
    """
    Canny with thresholds derived from Otsu's optimal threshold.
    Works much better than fixed thresholds across varying lighting conditions.
    """
    otsu_val, _ = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    low  = max(10, 0.33 * otsu_val)
    high = max(30, otsu_val)
    edges = cv2.Canny(gray, low, high)
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
    return cv2.morphologyEx(edges, cv2.MORPH_CLOSE, kernel)


def _otsu_threshold(gray: np.ndarray) -> np.ndarray:
    """
    Fallback: global Otsu threshold → dilate heavily to get blob boundaries.
    Less precise but catches what Canny misses on low-contrast images.
    """
    _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
    return cv2.dilate(thresh, kernel, iterations=2)


def detect_edges(preprocessed: np.ndarray) -> np.ndarray:
    """Return the edge map using adaptive Canny (primary strategy)."""
    return _adaptive_canny(preprocessed)


def _select_best_contour(contours: list, image_area: float) -> np.ndarray | None:
    """
    Pick the largest contour that:
      - covers between MIN and MAX of the frame area
      - approximates to a 4–8 vertex polygon (roughly rectangular)
      - has an aspect ratio plausibly matching a banknote (1.8–2.75)
    """
    candidates = sorted(contours, key=cv2.contourArea, reverse=True)[:8]

    for contour in candidates:
        area_ratio = cv2.contourArea(contour) / image_area
        if area_ratio < MIN_CONTOUR_AREA_RATIO or area_ratio > MAX_CONTOUR_AREA_RATIO:
            continue

        peri = cv2.arcLength(contour, True)
        approx = cv2.approxPolyDP(contour, 0.02 * peri, True)
        if not (4 <= len(approx) <= 8):
            continue

        # Quick shape check: bounding-rect AR should be within banknote range
        x, y, w, h = cv2.boundingRect(contour)
        if h == 0:
            continue
        ar = max(w, h) / min(w, h)
        if not (MIN_SHAPE_AR <= ar <= MAX_SHAPE_AR):
            continue

        return contour

    return None


def find_banknote_contour(
    edges: np.ndarray, image_shape: tuple, preprocessed: np.ndarray | None = None
) -> np.ndarray | None:
    """
    Find the banknote contour using Canny edges (primary) with an Otsu fallback.
    Pass `preprocessed` to enable the fallback strategy.
    """
    h, w = image_shape[:2]
    image_area = float(h * w)

    # --- Primary: Canny-derived edges ---
    contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    result = _select_best_contour(contours, image_area)
    if result is not None:
        return result

    # --- Fallback: Otsu threshold (catches low-contrast scenes) ---
    if preprocessed is not None:
        otsu_edges = _otsu_threshold(preprocessed)
        contours2, _ = cv2.findContours(otsu_edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        result2 = _select_best_contour(contours2, image_area)
        if result2 is not None:
            return result2

    return None