# config.py - Central configuration for Rupiah TE 2022 detection system
# (single-emission: TE 2022 only)

BANKNOTE_WIDTH_MM = 65

# ── TE 2022 (5 mm step between denominations, more vibrant colours) ────
DENOMINATIONS = [
    {
        "value": 100_000,
        "label_id": "Seratus Ribu Rupiah",
        "length_mm": 151,
        "aspect_ratio": 151 / 65,
        "hue_ranges": [(0, 10), (170, 179)],
        "min_saturation": 60,
        "max_saturation": 255,
        "_test_hsv": (5, 170, 160),
    },
    {
        "value": 50_000,
        "label_id": "Lima Puluh Ribu Rupiah",
        "length_mm": 146,
        "aspect_ratio": 146 / 65,
        "hue_ranges": [(100, 130)],
        "min_saturation": 60,
        "max_saturation": 255,
        "_test_hsv": (115, 170, 160),
    },
    {
        "value": 20_000,
        "label_id": "Dua Puluh Ribu Rupiah",
        "length_mm": 141,
        "aspect_ratio": 141 / 65,
        "hue_ranges": [(40, 85)],
        "min_saturation": 60,
        "max_saturation": 255,
        "_test_hsv": (60, 170, 160),
    },
    {
        "value": 10_000,
        "label_id": "Sepuluh Ribu Rupiah",
        "length_mm": 136,
        "aspect_ratio": 136 / 65,
        "hue_ranges": [(130, 160)],
        "min_saturation": 50,
        "max_saturation": 255,
        "_test_hsv": (145, 150, 160),
    },
    {
        "value": 5_000,
        "label_id": "Lima Ribu Rupiah",
        "length_mm": 131,
        "aspect_ratio": 131 / 65,
        "hue_ranges": [(8, 28)],
        "min_saturation": 50,
        "max_saturation": 255,
        "_test_hsv": (18, 150, 160),
    },
    {
        "value": 2_000,
        "label_id": "Dua Ribu Rupiah",
        "length_mm": 126,
        "aspect_ratio": 126 / 65,
        "hue_ranges": [(70, 100)],
        "min_saturation": 25,
        "max_saturation": 255,
        "_test_hsv": (85, 130, 150),
    },
    {
        "value": 1_000,
        "label_id": "Seribu Rupiah",
        "length_mm": 121,
        "aspect_ratio": 121 / 65,
        "hue_ranges": [(0, 179)],
        "min_saturation": 0,
        "max_saturation": 35,
        "_test_hsv": (90, 25, 180),
    },
]

DENOMINATIONS.sort(key=lambda d: d["value"], reverse=True)

# Template directory for number detection
TEMPLATE_DIR = "assets/templates"

# Auto-calibration: dynamically learn hue ranges from live detections.
# Disabled by default — enable only after verifying hue ranges for your camera.
AUTO_CALIBRATE = False

# Matching tolerances
ASPECT_RATIO_TOLERANCE = 0.025
MIN_HUE_PIXEL_FRACTION = 0.10
HUE_PEAK_MARGIN = 8

# Number detection (template matching)
NUMBER_ROI = (0.50, 0.55, 0.98, 0.95)
TEMPLATE_MATCH_THRESHOLD = 0.30       # min confidence to accept template match
NUMBER_WEIGHT = 0.65                   # weight of number score in final decision
COLOR_WEIGHT = 0.35                    # weight of color score

# Contour detection
MIN_CONTOUR_AREA_RATIO = 0.05
MAX_CONTOUR_AREA_RATIO = 0.97
MIN_SHAPE_AR = 1.80
MAX_SHAPE_AR = 2.75

# Rectification
WARP_OUTPUT_WIDTH = 640

# ── Detection mode ─────────────────────────────────────────────────────
# True  = snapshot mode: quick contour check per frame, snapshot on
#         stability, then one thorough classification.  Faster & more
#         accurate because the stability check is cheap (no full pipeline).
# False = streaming mode: run full pipeline every frame, accumulate
#         identical results via StabilityBuffer before announcing.
SNAPSHOT_MODE = True

# Snapshot-mode tunables
SNAPSHOT_CONTOUR_STREAK = 5   # consecutive frames with contour before snap
SNAPSHOT_COOLDOWN = 2.0        # seconds before next snapshot allowed
MAX_PREVIEW_FPS = 30           # contour-check frame rate limit

# Streaming-mode tunables (used only when SNAPSHOT_MODE = False)
STABILITY_FRAMES = 3           # consecutive identical detections before announcing
MAX_PROCESS_FPS = 10           # throttle: at most N frames/sec run full pipeline
COOLDOWN_SECONDS = 1.0         # pause between TTS announcements
NO_MONEY_MSG_INTERVAL = 3.0    # how often "no money" can repeat

# Camera
CAMERA_INDEX = 0
CAMERA_URL = "http://10.22.26.145:8080/video"
FRAME_WIDTH = 1280
FRAME_HEIGHT = 720

# Display resize factor (1.0 = original, 0.75 = 75% size)
DISPLAY_SCALE = 0.80
