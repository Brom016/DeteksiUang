"""
main.py  -  Rupiah Banknote Detector  -  Auto-Scan Mode

Usage:
  python main.py                  Live camera, fully automatic scanning
  python main.py --image FILE     Analyse a single image file
  python main.py --debug          Camera mode with debug overlay
  python main.py --calibrate      Interactive HSV calibration tool
"""

import argparse
import sys
import time
from collections import deque

import cv2
import numpy as np

from tts_engine import init as tts_init, speak
from pipeline import process_frame
from classifier import ClassificationResult
from config import (
    CAMERA_INDEX, CAMERA_URL, FRAME_WIDTH, FRAME_HEIGHT, DISPLAY_SCALE,
    STABILITY_FRAMES, COOLDOWN_SECONDS, NO_MONEY_MSG_INTERVAL,
)

# Colours used in the UI overlay
C_GREEN   = (30, 210, 30)
C_YELLOW  = (30, 210, 210)
C_ORANGE  = (30, 120, 255)
C_RED     = (30, 30, 240)
C_GREY    = (160, 160, 160)
C_WHITE   = (240, 240, 240)
C_BG      = (20, 20, 20)


# Stability buffer  -  requires N consecutive identical detections
class StabilityBuffer:
    """
    Accumulates consecutive detection results.
    Returns a result only when STABILITY_FRAMES identical results arrive.
    Enforces a cooldown after each announcement.
    """

    def __init__(self):
        self._history: deque = deque(maxlen=STABILITY_FRAMES)
        self._cooldown_until: float = 0.0

    def feed(self, result: ClassificationResult) -> ClassificationResult | None:
        now = time.time()
        if now < self._cooldown_until:
            return None  # Still in cooldown

        if result.denomination is not None:
            key = (result.denomination["value"], result.is_authentic)
            self._history.append(key)
        else:
            self._history.clear()
            return None

        if (len(self._history) == STABILITY_FRAMES
                and len(set(self._history)) == 1):
            self._cooldown_until = now + COOLDOWN_SECONDS
            self._history.clear()
            return result

        return None

    @property
    def in_cooldown(self) -> bool:
        return time.time() < self._cooldown_until

    @property
    def cooldown_remaining(self) -> float:
        return max(0.0, self._cooldown_until - time.time())

    @property
    def progress(self) -> float:
        """0.0 → 1.0: how close to a stable detection."""
        if not self._history:
            return 0.0
        # Only count a streak if all entries so far are the same
        if len(set(self._history)) > 1:
            return 0.0
        return len(self._history) / STABILITY_FRAMES


# Drawing helpers
def _text(img, text, pt, scale=0.65, color=C_WHITE, thickness=2):
    cv2.putText(img, text, pt, cv2.FONT_HERSHEY_SIMPLEX, scale,
                (0, 0, 0), thickness + 2, cv2.LINE_AA)
    cv2.putText(img, text, pt, cv2.FONT_HERSHEY_SIMPLEX, scale,
                color, thickness, cv2.LINE_AA)


def _draw_guide_rect(img):
    """Faint guide rectangle showing the ideal placement zone."""
    h, w = img.shape[:2]
    gx = int(w * 0.08)
    gy = int(h * 0.18)
    gw = int(w * 0.84)
    gh = int(h * 0.64)
    cv2.rectangle(img, (gx, gy), (gx + gw, gy + gh), (80, 80, 80), 1, cv2.LINE_AA)
    # Corner markers
    clen = 20
    for (cx, cy), (dx, dy) in [
        ((gx, gy), (1, 1)), ((gx+gw, gy), (-1, 1)),
        ((gx, gy+gh), (1, -1)), ((gx+gw, gy+gh), (-1, -1)),
    ]:
        cv2.line(img, (cx, cy), (cx + dx*clen, cy), C_GREY, 2, cv2.LINE_AA)
        cv2.line(img, (cx, cy), (cx, cy + dy*clen), C_GREY, 2, cv2.LINE_AA)


def _draw_stability_bar(img, progress: float, in_cooldown: bool, cd_remaining: float):
    h, w = img.shape[:2]
    bx, by = 12, h - 28
    bw, bh = w - 24, 14

    # Background pill
    cv2.rectangle(img, (bx, by), (bx+bw, by+bh), (40, 40, 40), -1, cv2.LINE_AA)
    cv2.rectangle(img, (bx, by), (bx+bw, by+bh), (70, 70, 70), 1, cv2.LINE_AA)

    if in_cooldown:
        # Countdown: bar shrinks
        ratio = cd_remaining / COOLDOWN_SECONDS
        fill_w = int(bw * ratio)
        cv2.rectangle(img, (bx, by), (bx+fill_w, by+bh), C_GREEN, -1, cv2.LINE_AA)
        _text(img, f"Selesai  {cd_remaining:.1f}s", (bx + 6, by + bh - 2),
              scale=0.45, color=(0, 0, 0), thickness=1)
    elif progress > 0:
        fill_w = int(bw * progress)
        bar_color = C_YELLOW if progress < 0.7 else C_GREEN
        cv2.rectangle(img, (bx, by), (bx+fill_w, by+bh), bar_color, -1, cv2.LINE_AA)
        pct = int(progress * 100)
        _text(img, f"Mendeteksi... {pct}%", (bx + 6, by + bh - 2),
              scale=0.45, color=(0, 0, 0), thickness=1)
    else:
        _text(img, "Arahkan uang ke kamera", (bx + 6, by + bh - 2),
              scale=0.45, color=C_GREY, thickness=1)


def _draw_status_banner(img, result: ClassificationResult | None,
                         in_cooldown: bool, last_label: str):
    h, w = img.shape[:2]
    # Semi-transparent dark bar at top
    overlay = img.copy()
    cv2.rectangle(overlay, (0, 0), (w, 52), C_BG, -1)
    cv2.addWeighted(overlay, 0.65, img, 0.35, 0, img)

    if in_cooldown and last_label:
        col = C_GREEN if "Asli" in last_label else C_ORANGE
        _text(img, last_label, (14, 34), scale=0.80, color=col)
    elif result is not None and result.denomination is not None:
        label = result.get_label()
        col = C_GREEN if result.is_authentic else C_ORANGE
        _text(img, label, (14, 34), scale=0.80, color=col)
    else:
        _text(img, "Siap memindai uang Rupiah TE 2022", (14, 34),
              scale=0.68, color=C_GREY)


def _draw_contour_overlay(img, contour, result: ClassificationResult | None,
                           progress: float):
    if contour is None:
        return
    if result is None or result.denomination is None:
        color = C_GREY
    elif result.is_authentic:
        color = C_GREEN if progress == 0 else C_YELLOW
    else:
        color = C_ORANGE
    cv2.drawContours(img, [contour], -1, color, 3, cv2.LINE_AA)


# Camera auto-detection loop
def run_camera_mode(debug: bool = False) -> None:
    if CAMERA_URL:
        cap = cv2.VideoCapture(CAMERA_URL)
        print(f"[INFO] Using IP camera: {CAMERA_URL}")
    else:
        cap = cv2.VideoCapture(CAMERA_INDEX)
        print(f"[INFO] Using local camera #{CAMERA_INDEX}")
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, FRAME_WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_HEIGHT)

    if not cap.isOpened():
        print("[ERROR] Cannot open camera")
        speak("Kamera tidak ditemukan")
        sys.exit(1)

    speak("Sistem siap memindai")
    print("[INFO] Auto-scan aktif. Tekan Q untuk keluar.")

    buf          = StabilityBuffer()
    last_label   = ""
    last_result  = None
    last_contour = None
    no_money_ts  = 0.0     # timestamp of last "no money" audio
    frame_n      = 0

    while True:
        ret, frame = cap.read()
        if not ret:
            break
        frame_n += 1

        if frame_n % 2 == 0:
            result, _, warped = process_frame(frame, debug_overlay=False)

            # Extract contour for overlay separately (lightweight re-run)
            from preprocessor import preprocess, detect_edges, find_banknote_contour
            preprocessed = preprocess(frame)
            edges        = detect_edges(preprocessed)
            last_contour = find_banknote_contour(edges, frame.shape, preprocessed)

            last_result = result
            stable = buf.feed(result)

            if stable is not None:
                label = stable.get_label()
                last_label = label
                speak(label)
                print(f"[RESULT] {label}")
                if debug:
                    print(f"[DEBUG]  {stable.debug_info}")

            # "No money" periodic audio cue
            elif (result.is_unrecognized
                  and result.debug_info.get("reason") == "no_contour"
                  and not buf.in_cooldown
                  and time.time() - no_money_ts > NO_MONEY_MSG_INTERVAL):
                speak("Uang Tidak Terlihat, Dekatkan Kamera")
                no_money_ts = time.time()

        display = frame.copy()

        if not buf.in_cooldown:
            _draw_guide_rect(display)
            _draw_contour_overlay(display, last_contour, last_result, buf.progress)

        _draw_status_banner(display, last_result, buf.in_cooldown, last_label)
        _draw_stability_bar(display, buf.progress, buf.in_cooldown, buf.cooldown_remaining)

        if debug and last_result is not None:
            di = last_result.debug_info
            dbg_lines = [
                f"AR: {di.get('measured_ar', '-'):.5f}  target: {di.get('target_ar', '-')}",
                f"DomHue: {di.get('dominant_hue', '-')}  "
                f"Frac: {di.get('pixel_fraction', '-')}",
            ]
            for i, line in enumerate(dbg_lines):
                _text(display, line, (14, 58 + i * 22), scale=0.5, color=C_YELLOW)

        # Resize display if needed
        if DISPLAY_SCALE < 1.0:
            disp_w = int(display.shape[1] * DISPLAY_SCALE)
            disp_h = int(display.shape[0] * DISPLAY_SCALE)
            display = cv2.resize(display, (disp_w, disp_h), interpolation=cv2.INTER_LINEAR)

        cv2.imshow("Rupiah Detector  [ Q = keluar ]", display)

        key = cv2.waitKey(1) & 0xFF
        if key == ord("q"):
            break

    cap.release()
    cv2.destroyAllWindows()


# Single-image mode
def run_image_mode(image_path: str, debug: bool = False) -> None:
    frame = cv2.imread(image_path)
    if frame is None:
        print(f"[ERROR] Cannot read: {image_path}")
        sys.exit(1)

    result, annotated, warped = process_frame(frame, debug_overlay=debug)
    label = result.get_label()

    print(f"[RESULT] {label}")
    print(f"[DEBUG]  {result.debug_info}")
    speak(label)

    cv2.imshow("Result  [ press any key ]", annotated)
    if warped is not None and debug:
        cv2.imshow("Warped Crop", warped)
    cv2.waitKey(0)
    cv2.destroyAllWindows()


# HSV calibration tool
def _open_camera():
    if CAMERA_URL:
        cap = cv2.VideoCapture(CAMERA_URL)
        print(f"[INFO] Using IP camera: {CAMERA_URL}")
    else:
        cap = cv2.VideoCapture(CAMERA_INDEX)
        print(f"[INFO] Using local camera #{CAMERA_INDEX}")
    return cap


def run_calibration_mode() -> None:
    cap = _open_camera()
    if not cap.isOpened():
        print("[ERROR] Cannot open camera")
        sys.exit(1)

    win = "Kalibrasi HSV  [ S=simpan  Q=keluar ]"
    cv2.namedWindow(win)
    for name, hi, lo in [("H Min", 179, 0), ("H Max", 179, 179),
                          ("S Min", 255, 40), ("V Min", 255, 30)]:
        cv2.createTrackbar(name, win, lo, hi, lambda _: None)

    print("\n[KALIBRASI] Arahkan kamera ke nominal uang.")
    print("            Atur slider hingga HANYA warna dominan uang yang putih di mask.")
    print("            Tekan S untuk menyimpan nilai, Q untuk keluar.\n")

    while True:
        ret, frame = cap.read()
        if not ret:
            break
        hmin = cv2.getTrackbarPos("H Min", win)
        hmax = cv2.getTrackbarPos("H Max", win)
        smin = cv2.getTrackbarPos("S Min", win)
        vmin = cv2.getTrackbarPos("V Min", win)

        hsv  = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        mask = cv2.inRange(hsv, np.array([hmin, smin, vmin]),
                           np.array([hmax, 255, 255]))
        masked = cv2.bitwise_and(frame, frame, mask=mask)
        info = f"H:[{hmin}-{hmax}]  S_min:{smin}  V_min:{vmin}"
        cv2.putText(frame, info, (10, 30), cv2.FONT_HERSHEY_SIMPLEX,
                    0.7, (0, 255, 255), 2)
        # Resize display if needed
        if DISPLAY_SCALE < 1.0:
            disp_w = int(frame.shape[1] * DISPLAY_SCALE)
            disp_h = int(frame.shape[0] * DISPLAY_SCALE)
            display_frame = cv2.resize(frame, (disp_w, disp_h), interpolation=cv2.INTER_LINEAR)
            display_mask = cv2.resize(masked, (disp_w, disp_h), interpolation=cv2.INTER_LINEAR)
        else:
            display_frame = frame
            display_mask = masked
        cv2.imshow(win, display_frame)
        cv2.imshow("Mask", display_mask)

        key = cv2.waitKey(1) & 0xFF
        if key == ord("q"):
            break
        if key == ord("s"):
            print(f"  -> hue_ranges: [({hmin}, {hmax})],  min_saturation: {smin}")
            print("    Perbarui nilai ini di config.py untuk nominal yang sedang dikalibrasi.\n")

    cap.release()
    cv2.destroyAllWindows()


# Entry point
def main() -> None:
    parser = argparse.ArgumentParser(
        description="Rupiah TE 2022 Detector  -  Alat Bantu Tunanetra"
    )
    parser.add_argument("--image",     type=str, default=None)
    parser.add_argument("--debug",     action="store_true")
    parser.add_argument("--calibrate", action="store_true")
    args = parser.parse_args()

    tts_init()

    if args.calibrate:
        run_calibration_mode()
    elif args.image:
        run_image_mode(args.image, debug=args.debug)
    else:
        run_camera_mode(debug=args.debug)


if __name__ == "__main__":
    main()