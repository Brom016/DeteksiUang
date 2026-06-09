"""
rectifier.py  -  Perspective correction.

Key improvement: tries approxPolyDP to find the actual 4 corner points of
the quadrilateral (perspective-distorted banknote) before falling back to
minAreaRect.  This gives significantly more accurate aspect-ratio recovery
when the camera is held at an angle.

  approxPolyDP  → exact corners of the trapezoid → best AR accuracy
  minAreaRect   → bounding rectangle of all contour points → fallback
"""

import cv2
import numpy as np

from config import WARP_OUTPUT_WIDTH


def order_points(pts: np.ndarray) -> np.ndarray:
    """
    Order 4 points: [top-left, top-right, bottom-right, bottom-left].
    Uses sum/diff method which is robust to any rotation.
    """
    rect = np.zeros((4, 2), dtype=np.float32)
    s = pts.sum(axis=1)
    rect[0] = pts[np.argmin(s)]    # top-left
    rect[2] = pts[np.argmax(s)]    # bottom-right
    d = np.diff(pts, axis=1).ravel()
    rect[1] = pts[np.argmin(d)]    # top-right
    rect[3] = pts[np.argmax(d)]    # bottom-left
    return rect


def _get_four_corners(contour: np.ndarray) -> np.ndarray | None:
    """
    Try to extract exactly 4 corner points from the contour.

    Strategy:
      1. Iterate several epsilon values for approxPolyDP until we get
         exactly 4 vertices.  Works well for clean quadrilaterals
         (including perspective-distorted rectangles / trapezoids).
      2. Fall back to minAreaRect if no 4-vertex approximation is found.
    """
    peri = cv2.arcLength(contour, True)

    for eps_factor in (0.02, 0.03, 0.04, 0.05, 0.06):
        approx = cv2.approxPolyDP(contour, eps_factor * peri, True)
        if len(approx) == 4:
            return approx.reshape(4, 2).astype(np.float32)

    # Fallback: minimum-area enclosing rectangle
    rect_box = cv2.minAreaRect(contour)
    return cv2.boxPoints(rect_box).astype(np.float32)


def rectify_banknote(
    image: np.ndarray, contour: np.ndarray
) -> tuple:
    """
    Produce a flat, landscape-oriented crop of the banknote.

    Returns (warped_image, aspect_ratio) or (None, None) on failure.
    """
    corners = _get_four_corners(contour)
    if corners is None:
        return None, None

    ordered = order_points(corners)
    tl, tr, br, bl = ordered

    width_top    = float(np.linalg.norm(tr - tl))
    width_bottom = float(np.linalg.norm(br - bl))
    height_left  = float(np.linalg.norm(bl - tl))
    height_right = float(np.linalg.norm(br - tr))

    raw_w = max(width_top, width_bottom)
    raw_h = max(height_left, height_right)

    if raw_w < 1 or raw_h < 1:
        return None, None

    src_pts = ordered.copy()

    # Enforce landscape orientation (width > height)
    if raw_h > raw_w:
        raw_w, raw_h = raw_h, raw_w
        src_pts = np.array([bl, tl, tr, br], dtype=np.float32)

    scale   = WARP_OUTPUT_WIDTH / raw_w
    out_w   = WARP_OUTPUT_WIDTH
    out_h   = max(1, int(round(raw_h * scale)))

    dst_pts = np.array(
        [[0, 0], [out_w - 1, 0], [out_w - 1, out_h - 1], [0, out_h - 1]],
        dtype=np.float32,
    )

    M      = cv2.getPerspectiveTransform(src_pts, dst_pts)
    warped = cv2.warpPerspective(image, M, (out_w, out_h))

    return warped, out_w / out_h