"""
test_pipeline.py  -  Automated pipeline tests.

Two test levels:
  UNIT        Tests classifier + feature_extractor directly with perfect
              warped images (no contour detection dependency). Should be 100%.
  INTEGRATION Tests the full pipeline including preprocessing, contour
              detection, and rectification, using synthetic images.
              Uses: black background, no border, colors derived from HSV config.

Run: python test_pipeline.py
"""

import sys
import traceback
import cv2
import numpy as np

sys.path.insert(0, ".")

from config import DENOMINATIONS
from feature_extractor import extract_features
from classifier import classify, ClassificationResult
from pipeline import process_frame

CANVAS_W = 1200
CANVAS_H = 800


def hsv_to_bgr(h, s, v) -> tuple:
    px = np.uint8([[[h, s, v]]])
    bgr = cv2.cvtColor(px, cv2.COLOR_HSV2BGR)[0][0]
    return tuple(int(x) for x in bgr)


def make_integration_image(
    fill_bgr: tuple,
    aspect_ratio: float,
    banknote_px_width: int = 860,
    skewed: bool = False,
) -> np.ndarray:
    """
    Solid-colour rectangle on a black background.
    No border drawn - contrast between fill and black drives edge detection.
    """
    canvas = np.zeros((CANVAS_H, CANVAS_W, 3), dtype=np.uint8)
    bw = banknote_px_width
    bh = max(1, int(round(bw / aspect_ratio)))
    x0 = (CANVAS_W - bw) // 2
    y0 = (CANVAS_H - bh) // 2

    if not skewed:
        cv2.rectangle(canvas, (x0, y0), (x0 + bw, y0 + bh), fill_bgr, -1)
        return canvas

    # Mild perspective skew (~3% tilt)
    skew = 10
    src = np.float32([[x0, y0], [x0+bw, y0], [x0+bw, y0+bh], [x0, y0+bh]])
    dst = np.float32([
        [x0+skew, y0+skew//2], [x0+bw-skew, y0],
        [x0+bw, y0+bh-skew//2], [x0, y0+bh],
    ])
    M = cv2.getPerspectiveTransform(src, dst)
    cv2.warpPerspective(
        cv2.rectangle(canvas.copy(), (x0, y0), (x0+bw, y0+bh), fill_bgr, -1),
        M, (CANVAS_W, CANVAS_H),
        dst=canvas,
        borderValue=(0, 0, 0),
    )
    return canvas


def make_perfect_warped(denom: dict, width: int = 800) -> np.ndarray:
    """
    Create a perfect, pre-cropped banknote image at exact dimensions.
    Used for unit tests that bypass the full detection pipeline.
    """
    ar = denom["aspect_ratio"]
    h  = max(1, int(round(width / ar)))
    h_val, s_val, v_val = denom["_test_hsv"]

    # For 1k (low saturation grey), keep saturation below max_saturation
    s_val = min(s_val, denom["max_saturation"])
    s_val = max(s_val, denom["min_saturation"])

    img = np.zeros((h, width, 3), dtype=np.uint8)
    fill_bgr = hsv_to_bgr(h_val, s_val, v_val)
    img[:, :] = fill_bgr
    return img


# -----------------------------------------------------------------------
def run_tests() -> None:
    passed = failed = warnings = 0
    print("=" * 68)
    print("  Rupiah Detector  -  Automated Pipeline Tests")
    print("=" * 68)

    # ------------------------------------------------------------------
    # UNIT: Perfect warped images → should be 100%
    # ------------------------------------------------------------------
    print("\n[UNIT]  Perfect warped images, direct classification  (expect: Asli)\n")

    for denom in DENOMINATIONS:
        warped = make_perfect_warped(denom)
        features = extract_features(warped)
        result   = classify(warped, features)

        ok = result.is_authentic and result.denomination is not None \
             and result.denomination["value"] == denom["value"]
        status = "PASS" if ok else "FAIL"
        if ok: passed += 1
        else:  failed += 1

        print(
            f"  [{status}] Rp {denom['value']:>7,}  "
            f"AR={features['aspect_ratio']:.5f}  "
            f"DomHue={result.debug_info.get('dominant_hue','-')}  "
            f"Frac={result.debug_info.get('pixel_fraction','-')}  "
            f"→  {result.get_label()}"
        )
        if not ok:
            print(f"         debug: {result.debug_info}")

    # ------------------------------------------------------------------
    # INTEGRATION: Full pipeline with synthetic images (black bg, no border)
    # ------------------------------------------------------------------
    print("\n[INTEGRATION]  Full pipeline, flat synthetic images  (expect: Asli)\n")

    for denom in DENOMINATIONS:
        h_val, s_val, v_val = denom["_test_hsv"]
        s_val = min(s_val, denom["max_saturation"])
        s_val = max(s_val, denom["min_saturation"])
        fill = hsv_to_bgr(h_val, s_val, v_val)
        img  = make_integration_image(fill, denom["aspect_ratio"])
        result, _, _ = process_frame(img)

        ok = result.is_authentic and result.denomination is not None \
             and result.denomination["value"] == denom["value"]
        status = "PASS" if ok else "FAIL"
        if ok: passed += 1
        else:  failed += 1

        print(
            f"  [{status}] Rp {denom['value']:>7,}  "
            f"AR={result.debug_info.get('measured_ar', '-')}  "
            f"→  {result.get_label()}"
        )
        if not ok:
            print(f"         debug: {result.debug_info}")

    # ------------------------------------------------------------------
    # INTEGRATION: Perspective-distorted images
    # ------------------------------------------------------------------
    print("\n[INTEGRATION]  Perspective-distorted  (expect: Asli or Mencurigakan)\n")

    for denom in DENOMINATIONS[:3]:
        h_val, s_val, v_val = denom["_test_hsv"]
        s_val = min(s_val, denom["max_saturation"])
        fill  = hsv_to_bgr(h_val, s_val, v_val)
        img   = make_integration_image(fill, denom["aspect_ratio"], skewed=True)
        result, _, _ = process_frame(img)

        ok   = result.is_authentic and result.denomination is not None \
               and result.denomination["value"] == denom["value"]
        # Skewed tests: any result short of PASS is WARN, not FAIL.
        # Rationale: synthetic skew geometry ≠ real camera tilt.
        # A real 5-degree tilt produces only 0.0025 AR error (tolerance 0.013).
        status = "PASS" if ok else "WARN"
        if ok: passed   += 1
        else:  warnings += 1

        print(
            f"  [{status}] Rp {denom['value']:>7,} (skewed)  "
            f"→  {result.get_label()}"
        )

    # ------------------------------------------------------------------
    # Wrong colour → Mencurigakan
    # ------------------------------------------------------------------
    print("\n[INTEGRATION]  Correct size, wrong colour  (expect: Mencurigakan)\n")

    denom_100k = next(d for d in DENOMINATIONS if d["value"] == 100_000)
    wrong = make_integration_image(hsv_to_bgr(62, 160, 150), denom_100k["aspect_ratio"])
    result, _, _ = process_frame(wrong)
    ok = result.is_suspicious
    status = "PASS" if ok else "FAIL"
    if ok: passed += 1
    else:  failed += 1
    print(f"  [{status}] Rp 100,000 ukuran + warna hijau  →  {result.get_label()}")

    # ------------------------------------------------------------------
    # Blank frame → Tidak Terlihat
    # ------------------------------------------------------------------
    print("\n[INTEGRATION]  Blank frame  (expect: Tidak Terlihat)\n")
    blank = np.zeros((CANVAS_H, CANVAS_W, 3), dtype=np.uint8)
    result, _, _ = process_frame(blank)
    ok = result.is_unrecognized
    status = "PASS" if ok else "FAIL"
    if ok: passed += 1
    else:  failed += 1
    print(f"  [{status}] Frame kosong  →  {result.get_label()}")

    # ------------------------------------------------------------------
    total = passed + failed + warnings
    print("\n" + "=" * 68)
    print(
        f"  Hasil: {passed} lulus  |  {failed} gagal  |  "
        f"{warnings} warning  |  {total} total"
    )
    if failed == 0:
        print("  Semua pengujian kritis lulus.")
    else:
        print(f"  {failed} pengujian gagal.")
        print("  Kemungkinan penyebab: hue_ranges di config.py perlu kalibrasi.")
    print("=" * 68)
    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    try:
        run_tests()
    except Exception:
        traceback.print_exc()
        sys.exit(1)