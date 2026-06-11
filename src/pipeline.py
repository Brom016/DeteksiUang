# pipeline.py - Full PCD pipeline for a single BGR frame

import cv2
import numpy as np

from preprocessor import preprocess, detect_edges, find_banknote_contour
from rectifier import rectify_banknote
from feature_extractor import extract_features
from classifier import classify, ClassificationResult


def process_frame(
    frame: np.ndarray,
    debug_overlay: bool = False,
) -> tuple:
    annotated = frame.copy()

    preprocessed = preprocess(frame)
    edges = detect_edges(preprocessed)
    contour = find_banknote_contour(
        edges, frame.shape, preprocessed, original_image=frame
    )

    if contour is None:
        result = ClassificationResult(
            is_unrecognized=True, debug_info={"reason": "no_contour"}
        )
        if debug_overlay:
            _put(annotated, "Uang tidak terdeteksi", (0, 0, 220))
        return result, annotated, None

    if debug_overlay:
        cv2.drawContours(annotated, [contour], -1, (0, 220, 255), 2)

    warped, raw_ar = rectify_banknote(frame, contour)
    if warped is None:
        result = ClassificationResult(
            is_unrecognized=True, debug_info={"reason": "rectification_failed"}
        )
        return result, annotated, None

    features = extract_features(warped)
    if raw_ar > 0:
        features["aspect_ratio"] = raw_ar
    result = classify(warped, features)

    if debug_overlay:
        _draw_debug(annotated, result, features)

    return result, annotated, warped


def _put(img, text, color, y=40):
    cv2.putText(img, text, (18, y), cv2.FONT_HERSHEY_SIMPLEX, 0.85,
                (0, 0, 0), 3, cv2.LINE_AA)
    cv2.putText(img, text, (18, y), cv2.FONT_HERSHEY_SIMPLEX, 0.85,
                color, 2, cv2.LINE_AA)


def _draw_debug(img, result: ClassificationResult, features: dict):
    color = (0, 200, 60) if result.is_authentic else (0, 120, 255)
    calibrated = "C" if result.debug_info.get("calibrated") else "H"
    lines = [
        result.get_label(),
        f"AR: {features['aspect_ratio']:.5f}  target: {result.debug_info.get('target_ar', '-')}",
        f"Geo: {result.confidence_geo:.3f}  "
        f"Hue: {result.debug_info.get('dominant_hue', '-')}",
        f"Frac: {result.debug_info.get('pixel_fraction', '-')}  "
        f"C: {'OK' if result.debug_info.get('color_match') else 'FAIL'} ({calibrated})",
    ]
    y = 35
    for line in lines:
        cv2.putText(img, line, (18, y), cv2.FONT_HERSHEY_SIMPLEX, 0.6,
                    (0, 0, 0), 3, cv2.LINE_AA)
        cv2.putText(img, line, (18, y), cv2.FONT_HERSHEY_SIMPLEX, 0.6,
                    color, 2, cv2.LINE_AA)
        y += 24
