# rectifier.py - Perspective correction for banknote contours

import cv2
import numpy as np

from config import WARP_OUTPUT_WIDTH


def order_points(pts: np.ndarray) -> np.ndarray:
    rect = np.zeros((4, 2), dtype=np.float32)
    s = pts.sum(axis=1)
    rect[0] = pts[np.argmin(s)]
    rect[2] = pts[np.argmax(s)]
    d = np.diff(pts, axis=1).ravel()
    rect[1] = pts[np.argmin(d)]
    rect[3] = pts[np.argmax(d)]
    return rect


def _get_corners(contour: np.ndarray) -> np.ndarray:
    # If contour already has 4 points (from _refine_contour), use them directly
    if len(contour) == 4:
        return contour.reshape(4, 2).astype(np.float32)
    # Try to find 4 corners via approximation
    peri = cv2.arcLength(contour, True)
    for eps in (0.01, 0.015, 0.02, 0.03, 0.04, 0.05):
        approx = cv2.approxPolyDP(contour, eps * peri, True)
        if len(approx) == 4:
            return approx.reshape(4, 2).astype(np.float32)
    # Fallback: use minAreaRect on the convex hull
    hull = cv2.convexHull(contour)
    rect = cv2.minAreaRect(hull)
    return cv2.boxPoints(rect).astype(np.float32)


def rectify_banknote(image: np.ndarray, contour: np.ndarray) -> tuple:
    corners = _get_corners(contour)
    if corners is None or len(corners) != 4:
        return None, None

    ordered = order_points(corners)
    tl, tr, br, bl = ordered

    width_top = float(np.linalg.norm(tr - tl))
    width_bottom = float(np.linalg.norm(br - bl))
    height_left = float(np.linalg.norm(bl - tl))
    height_right = float(np.linalg.norm(br - tr))

    raw_w = max(width_top, width_bottom)
    raw_h = max(height_left, height_right)

    if raw_w < 2 or raw_h < 2:
        return None, None

    src_pts = ordered.copy()
    if raw_h > raw_w:
        raw_w, raw_h = raw_h, raw_w
        src_pts = np.array([bl, tl, tr, br], dtype=np.float32)

    scale = WARP_OUTPUT_WIDTH / raw_w
    out_w = WARP_OUTPUT_WIDTH
    out_h = max(1, int(round(raw_h * scale)))

    dst_pts = np.array(
        [[0, 0], [out_w - 1, 0], [out_w - 1, out_h - 1], [0, out_h - 1]],
        dtype=np.float32,
    )

    M = cv2.getPerspectiveTransform(src_pts, dst_pts)
    warped = cv2.warpPerspective(image, M, (out_w, out_h))
    raw_ar = raw_w / raw_h if raw_h > 0 else 0.0
    return warped, raw_ar
