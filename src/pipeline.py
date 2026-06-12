# pipeline.py - Full PCD pipeline for a single BGR frame

import cv2
import numpy as np

from preprocessor import preprocess, detect_edges, find_banknote_contour
from rectifier import rectify_banknote
from feature_extractor import extract_features
from classifier import classify, ClassificationResult


def quick_contour_detect(frame: np.ndarray):
    """Fast contour check — skips rectify, features, classification.
    Returns the contour or None."""
    preprocessed = preprocess(frame)
    edges = detect_edges(preprocessed)
    return find_banknote_contour(
        edges, frame.shape, preprocessed
    )


def process_frame(
    frame: np.ndarray,
    debug_overlay: bool = False,
    snapshot_mode: bool = False,
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
        return result, annotated, None, None

    if debug_overlay:
        cv2.drawContours(annotated, [contour], -1, (0, 220, 255), 2)

    warped, raw_ar = rectify_banknote(frame, contour)
    if warped is None:
        result = ClassificationResult(
            is_unrecognized=True, debug_info={"reason": "rectification_failed"}
        )
        return result, annotated, None, contour

    features = extract_features(warped)
    if raw_ar > 0:
        features["aspect_ratio"] = raw_ar
    result = classify(warped, features, snapshot_mode=snapshot_mode)

    if debug_overlay:
        _draw_debug(annotated, result, features)

    return result, annotated, warped, contour


def _put(img, text, color, y=40):
    cv2.putText(img, text, (18, y), cv2.FONT_HERSHEY_SIMPLEX, 0.85,
                (0, 0, 0), 3, cv2.LINE_AA)
    cv2.putText(img, text, (18, y), cv2.FONT_HERSHEY_SIMPLEX, 0.85,
                color, 2, cv2.LINE_AA)


def _draw_debug(img, result: ClassificationResult, features: dict):
    color = (0, 200, 60) if result.is_authentic else (0, 120, 255)
    info = result.debug_info

    num_line = ""
    if info.get("number_match"):
        num_line = f"Angka: Rp {info.get('number_value', '?'):,}  "
        num_line += f"conf: {info.get('number_confidence', 0):.3f}"
    else:
        num_line = f"Angka: tdk terdeteksi  (conf: {info.get('number_confidence', 0):.3f})"

    lines = [
        result.get_label(),
        f"AR: {features['aspect_ratio']:.5f}  target: {info.get('target_ar', '-')}",
        f"Geo: {result.confidence_geo:.3f}  "
        f"Hue: {info.get('dominant_hue', '-')}",
        f"Color: {info.get('color_score', 0):.3f}  "
        f"Comb: {info.get('combined', 0):.3f}",
        num_line,
    ]
    y = 35
    for line in lines:
        cv2.putText(img, line, (18, y), cv2.FONT_HERSHEY_SIMPLEX, 0.55,
                    (0, 0, 0), 3, cv2.LINE_AA)
        cv2.putText(img, line, (18, y), cv2.FONT_HERSHEY_SIMPLEX, 0.55,
                    color, 2, cv2.LINE_AA)
        y += 22
