# preprocessor.py - Edge-based banknote contour detection

import cv2
import numpy as np

from config import MIN_CONTOUR_AREA_RATIO, MAX_CONTOUR_AREA_RATIO, MIN_SHAPE_AR, MAX_SHAPE_AR


def preprocess(image: np.ndarray) -> np.ndarray:
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0.8)
    return blurred


def _adaptive_canny(gray: np.ndarray) -> np.ndarray:
    # Try Otsu-based thresholds; fallback to fixed if image is near-uniform
    otsu_val, _ = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    if otsu_val < 5 or otsu_val > 250:
        low, high = 30, 100
    else:
        low = max(10, int(0.4 * otsu_val))
        high = max(30, int(1.2 * otsu_val))
    edges = cv2.Canny(gray, low, high)
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
    closed = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, kernel, iterations=2)
    return closed


def _enhanced_preprocess(image: np.ndarray) -> np.ndarray:
    # Aggressive CLAHE + bilateral for low-contrast / uneven lighting scenes
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    enhanced = clahe.apply(gray)
    return cv2.bilateralFilter(enhanced, d=7, sigmaColor=50, sigmaSpace=50)


def detect_edges(preprocessed: np.ndarray) -> np.ndarray:
    return _adaptive_canny(preprocessed)


def _is_good_shape(contour: np.ndarray, image_area: float) -> tuple:
    area = cv2.contourArea(contour)
    area_ratio = area / image_area
    if area_ratio < MIN_CONTOUR_AREA_RATIO or area_ratio > MAX_CONTOUR_AREA_RATIO:
        return False, 0, 0

    x, y, w, h = cv2.boundingRect(contour)
    if h < 5 or w < 5:
        return False, 0, 0

    ar = max(w, h) / min(w, h)
    if not (MIN_SHAPE_AR <= ar <= MAX_SHAPE_AR):
        return False, 0, 0

    hull = cv2.convexHull(contour)
    hull_area = cv2.contourArea(hull)
    if hull_area < 1:
        return False, 0, 0

    solidity = area / hull_area
    rect_area = w * h
    rectangularity = area / rect_area if rect_area > 0 else 0

    if solidity < 0.5 or rectangularity < 0.4:
        return False, 0, 0

    return True, ar, rectangularity


def _refine_contour(contour: np.ndarray) -> np.ndarray:
    peri = cv2.arcLength(contour, True)
    for eps in (0.01, 0.015, 0.02, 0.03, 0.04):
        approx = cv2.approxPolyDP(contour, eps * peri, True)
        if 4 <= len(approx) <= 6:
            return approx
    return cv2.convexHull(contour)


def find_banknote_contour(
    edges: np.ndarray, image_shape: tuple, preprocessed: np.ndarray | None = None,
    original_image: np.ndarray | None = None,
) -> np.ndarray | None:
    h, w = image_shape[:2]
    image_area = float(h * w)

    # Try Canny-based detection
    contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    best = None
    best_score = -1

    for c in contours:
        ok, ar, rect_score = _is_good_shape(c, image_area)
        if not ok:
            continue
        ar_penalty = abs(ar - 2.23)
        score = rect_score - ar_penalty * 0.3
        if score > best_score:
            best_score = score
            best = c

    # Try enhanced preprocessing + Canny for low-contrast scenes
    if best is None and original_image is not None:
        enhanced = _enhanced_preprocess(original_image)
        enhanced_edges = _adaptive_canny(enhanced)
        c2, _ = cv2.findContours(enhanced_edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        for c in c2:
            ok, ar, rect_score = _is_good_shape(c, image_area)
            if not ok:
                continue
            ar_penalty = abs(ar - 2.23)
            score = rect_score - ar_penalty * 0.3
            if score > best_score:
                best_score = score
                best = c

    # Convex hull fallback for folded/bent notes
    if best is None and contours:
        tops = sorted(contours, key=cv2.contourArea, reverse=True)[:5]
        if len(tops) > 1:
            merged = np.vstack(tops)
            hull = cv2.convexHull(merged)
            ok, ar, rect_score = _is_good_shape(hull, image_area)
            if ok:
                ar_penalty = abs(ar - 2.23)
                score = rect_score - ar_penalty * 0.3
                if score > best_score:
                    best_score = score
                    best = hull

    # Relaxed fallback: largest contour with banknote-like bounding rect AR
    if best is None and contours:
        for c in sorted(contours, key=cv2.contourArea, reverse=True):
            area = cv2.contourArea(c)
            if area / image_area < 0.05:
                continue
            x, y, bw, bh = cv2.boundingRect(c)
            if bw < 10 or bh < 10:
                continue
            ar = max(bw, bh) / min(bw, bh)
            if MIN_SHAPE_AR <= ar <= MAX_SHAPE_AR:
                hull = cv2.convexHull(c)
                if cv2.contourArea(hull) / image_area >= 0.05:
                    best = c
                    break

    # Otsu threshold fallback: handles images where Canny produces broken edges
    if best is None and original_image is not None:
        gray = cv2.cvtColor(original_image, cv2.COLOR_BGR2GRAY)
        blurred = cv2.GaussianBlur(gray, (5, 5), 0.8)
        _, thresh = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
        kernel_open = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
        thresh = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, kernel_open, iterations=2)
        kernel_close = cv2.getStructuringElement(cv2.MORPH_RECT, (7, 7))
        thresh = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel_close, iterations=2)
        c3, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        for c in sorted(c3, key=cv2.contourArea, reverse=True):
            area = cv2.contourArea(c)
            if area / image_area < 0.05:
                continue
            x, y, bw, bh = cv2.boundingRect(c)
            if bw < 10 or bh < 10:
                continue
            ar = max(bw, bh) / min(bw, bh)
            if MIN_SHAPE_AR <= ar <= MAX_SHAPE_AR:
                hull = cv2.convexHull(c)
                if cv2.contourArea(hull) / image_area >= 0.05:
                    best = c
                    break

    if best is None:
        return None

    # Verify final hull area
    hull = cv2.convexHull(best)
    if cv2.contourArea(hull) / image_area < MIN_CONTOUR_AREA_RATIO:
        return None

    return _refine_contour(best)
