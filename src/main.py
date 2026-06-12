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
from pipeline import process_frame, quick_contour_detect
from classifier import ClassificationResult
from config import (
    CAMERA_INDEX, CAMERA_URL, FRAME_WIDTH, FRAME_HEIGHT, DISPLAY_SCALE,
    SNAPSHOT_MODE, SNAPSHOT_CONTOUR_STREAK, SNAPSHOT_COOLDOWN,
    MAX_PREVIEW_FPS, STABILITY_FRAMES, COOLDOWN_SECONDS,
    NO_MONEY_MSG_INTERVAL, MAX_PROCESS_FPS,
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


# ── Camera helpers ──────────────────────────────────────────────────

def _open_camera():
    if CAMERA_URL:
        cap = cv2.VideoCapture(CAMERA_URL)
        print(f"[INFO] Using IP camera: {CAMERA_URL}")
    else:
        cap = cv2.VideoCapture(CAMERA_INDEX)
        print(f"[INFO] Using local camera #{CAMERA_INDEX}")
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, FRAME_WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_HEIGHT)
    return cap


def _resize_display(img: np.ndarray) -> np.ndarray:
    if DISPLAY_SCALE < 1.0:
        dw = int(img.shape[1] * DISPLAY_SCALE)
        dh = int(img.shape[0] * DISPLAY_SCALE)
        return cv2.resize(img, (dw, dh), interpolation=cv2.INTER_LINEAR)
    return img


def _wait_quit() -> bool:
    """Return True if user pressed Q."""
    return (cv2.waitKey(1) & 0xFF) == ord("q")


# ── Snapshot mode  (take a picture when the note is steady) ────────

def _run_snapshot_mode(debug: bool) -> None:
    cap = _open_camera()
    if not cap.isOpened():
        print("[ERROR] Cannot open camera")
        speak("Kamera tidak ditemukan")
        sys.exit(1)
    speak("Sistem siap memindai")
    print("[INFO] Snapshot mode aktif. Arahkan uang ke kamera. Tekan Q untuk keluar.")

    streak        = 0
    last_contour  = None
    last_label    = ""
    last_result   = None
    cooldown_until = 0.0
    processing    = False
    snap_frame    = None
    no_money_ts   = 0.0
    min_interval  = 1.0 / MAX_PREVIEW_FPS
    prev_ts       = 0.0

    while True:
        ret, frame = cap.read()
        if not ret:
            break
        now = time.time()

        # ── Snapshot processing (runs once after capture) ──────────
        if processing and snap_frame is not None:
            print("[SNAP] Memproses snapshot...")
            result, _, _, contour = process_frame(
                snap_frame, debug_overlay=debug, snapshot_mode=True
            )
            label = result.get_label()
            last_label = label
            last_result = result
            last_contour = contour
            speak(label)
            print(f"[RESULT] {label}")
            if debug:
                print(f"[DEBUG]  {result.debug_info}")
            streak = 0
            cooldown_until = now + SNAPSHOT_COOLDOWN
            processing = False
            snap_frame = None
            continue

        # ── Cooldown ──────────────────────────────────────────────
        if now < cooldown_until:
            display = frame.copy()
            _draw_guide_rect(display)
            _draw_contour_overlay(display, last_contour, last_result, 0.0)
            _draw_status_banner(display, last_result, True, last_label)
            _draw_stability_bar(display, 1.0, True, cooldown_until - now)
            cv2.imshow("Rupiah Detector  [ Q = keluar ]", _resize_display(display))
            if _wait_quit():
                break
            continue

        # ── Quick contour check (every frame, no full pipeline) ───
        if now - prev_ts >= min_interval:
            prev_ts = now
            c = quick_contour_detect(frame)
            if c is not None:
                streak += 1
                last_contour = c
            else:
                streak = 0
                last_contour = None

        progress = min(1.0, streak / SNAPSHOT_CONTOUR_STREAK)

        # ── Trigger snapshot ──────────────────────────────────────
        if streak >= SNAPSHOT_CONTOUR_STREAK:
            processing = True
            snap_frame = frame.copy()
            print(f"[SNAP] Kontur stabil selama {streak} frame → snapshot")
            continue

        # ── "No money" prompt ─────────────────────────────────────
        if last_contour is None and now - no_money_ts > NO_MONEY_MSG_INTERVAL:
            # Only speak once per interval
            no_money_ts = now
            # Don't spam TTS, just show on screen

        # ── Draw UI ───────────────────────────────────────────────
        display = frame.copy()
        _draw_guide_rect(display)
        _draw_contour_overlay(display, last_contour, None, progress)
        _draw_status_banner(display, last_result, False,
                            last_label if last_label else "")
        _draw_stability_bar(display, progress, False, 0.0)
        cv2.imshow("Rupiah Detector  [ Q = keluar ]", _resize_display(display))
        if _wait_quit():
            break

    cap.release()
    cv2.destroyAllWindows()


# ── Streaming mode  (full pipeline every frame, stability buffer) ──

def _run_streaming_mode(debug: bool) -> None:
    cap = _open_camera()
    if not cap.isOpened():
        print("[ERROR] Cannot open camera")
        speak("Kamera tidak ditemukan")
        sys.exit(1)
    speak("Sistem siap memindai")
    print("[INFO] Streaming mode aktif. Tekan Q untuk keluar.")

    buf          = StabilityBuffer()
    last_label   = ""
    last_result  = None
    last_contour = None
    no_money_ts  = 0.0
    process_ts   = 0.0
    min_interval = 1.0 / MAX_PROCESS_FPS

    while True:
        ret, frame = cap.read()
        if not ret:
            break
        now = time.time()

        if now - process_ts >= min_interval:
            process_ts = now
            result, _, _, last_contour = process_frame(frame, debug_overlay=False)
            last_result = result
            stable = buf.feed(result)

            if stable is not None:
                label = stable.get_label()
                last_label = label
                speak(label)
                print(f"[RESULT] {label}")
                if debug:
                    print(f"[DEBUG]  {stable.debug_info}")
            elif (result.is_unrecognized
                  and result.debug_info.get("reason") == "no_contour"
                  and not buf.in_cooldown
                  and now - no_money_ts > NO_MONEY_MSG_INTERVAL):
                speak("Uang Tidak Terlihat, Dekatkan Kamera")
                no_money_ts = now

        display = frame.copy()
        if not buf.in_cooldown:
            _draw_guide_rect(display)
            _draw_contour_overlay(display, last_contour, last_result, buf.progress)
        _draw_status_banner(display, last_result, buf.in_cooldown, last_label)
        _draw_stability_bar(display, buf.progress, buf.in_cooldown, buf.cooldown_remaining)

        if debug and last_result is not None:
            di = last_result.debug_info
            dbg = [
                f"AR: {di.get('measured_ar', '-'):.5f}  target: {di.get('target_ar', '-')}",
                f"DomHue: {di.get('dominant_hue', '-')}  "
                f"Frac: {di.get('pixel_fraction', '-')}",
            ]
            for i, line in enumerate(dbg):
                _text(display, line, (14, 58 + i * 22), scale=0.5, color=C_YELLOW)

        cv2.imshow("Rupiah Detector  [ Q = keluar ]", _resize_display(display))
        if _wait_quit():
            break

    cap.release()
    cv2.destroyAllWindows()


# Camera auto-detection loop — dispatcher
def run_camera_mode(debug: bool = False) -> None:
    if SNAPSHOT_MODE:
        _run_snapshot_mode(debug)
    else:
        _run_streaming_mode(debug)


# Single-image mode
def run_image_mode(image_path: str, debug: bool = False) -> None:
    frame = cv2.imread(image_path)
    if frame is None:
        print(f"[ERROR] Cannot read: {image_path}")
        sys.exit(1)

    result, annotated, warped, _ = process_frame(frame, debug_overlay=debug)
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