"""
feature_extractor.py  -  Aspect ratio and HSV color feature extraction.

Two color-analysis methods are provided and used together in the classifier:

  1. Dominant Hue  (primary)
     Finds the histogram peak of the Hue channel among saturated pixels.
     More robust to partial occlusion and distant/small-area banknotes.

  2. Pixel Fraction  (secondary)
     Fraction of total pixels that fall within the target hue range.
     Used as a cross-check when the dominant hue is ambiguous.
"""

import cv2
import numpy as np


def get_aspect_ratio(warped: np.ndarray) -> float:
    h, w = warped.shape[:2]
    return w / h if h > 0 else 0.0


def get_dominant_hue(
    warped: np.ndarray,
    min_saturation: int = 50,
    max_saturation: int = 255,
) -> int | None:
    """
    Return the most common Hue value (0–179) among saturated pixels.

    Smooths the 180-bin histogram with a Gaussian-like window to handle
    the red hue wrap-around at 0/179 and reduce quantisation noise.

    Returns None if the image contains too few saturated pixels
    (e.g. grey/silver denominations with low saturation).
    """
    # Light blur to reduce noise before color analysis
    blurred = cv2.GaussianBlur(warped, (3, 3), 0.5)
    hsv = cv2.cvtColor(blurred, cv2.COLOR_BGR2HSV)
    sat = hsv[:, :, 1]
    val = hsv[:, :, 2]

    sat_mask = (sat >= min_saturation) & (sat <= max_saturation) & (val >= 30)
    total_sat = int(sat_mask.sum())

    if total_sat < 200:
        return None

    hue_vals = hsv[:, :, 0][sat_mask]
    hist, _ = np.histogram(hue_vals, bins=180, range=(0, 180))

    # Mirror-pad histogram to handle red wrap at 0/179
    padded = np.concatenate([hist[-10:], hist, hist[:10]])
    smoothed = np.convolve(padded, np.array([1, 2, 3, 2, 1], dtype=float) / 9, mode='same')
    smoothed = smoothed[10:-10]

    return int(np.argmax(smoothed))


def compute_hue_fraction(
    warped: np.ndarray,
    hue_ranges: list,
    min_saturation: int = 50,
    max_saturation: int = 255,
) -> float:
    """
    Fraction of total pixels matching any of the given hue ranges
    (after saturation gate).  Returns 0.0–1.0.
    """
    blurred = cv2.GaussianBlur(warped, (3, 3), 0.5)
    hsv = cv2.cvtColor(blurred, cv2.COLOR_BGR2HSV)
    total = warped.shape[0] * warped.shape[1]
    if total == 0:
        return 0.0

    mask = np.zeros(warped.shape[:2], dtype=np.uint8)
    for h_min, h_max in hue_ranges:
        m = cv2.inRange(
            hsv,
            np.array([h_min, min_saturation, 30], dtype=np.uint8),
            np.array([h_max, max_saturation, 255], dtype=np.uint8),
        )
        mask = cv2.bitwise_or(mask, m)

    return int(cv2.countNonZero(mask)) / total


def extract_features(warped: np.ndarray) -> dict:
    h, w = warped.shape[:2]
    return {
        "aspect_ratio": w / h if h > 0 else 0.0,
        "image_size": (w, h),
    }