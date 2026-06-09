"""
config.py  -  Central configuration for Rupiah TE 2022 detection system.

CALIBRATION NOTE:
  hue_ranges are reasonable starting estimates. Real-world accuracy depends
  heavily on camera white balance and ambient lighting. Run the calibration
  mode and update these values for your camera.

IMPORTANT LIMITATION:
  "Asli" means dimensions + color match BI TE 2022 spec, NOT a full
  authentication. Security features (UV, watermark, thread) are not checked.
"""

# -----------------------------------------------------------------------
# Bank Indonesia TE 2022  -  physical dimensions
# Width: 65 mm (constant for all denominations)
# Length: decreases by exactly 2 mm per step downward
# -----------------------------------------------------------------------
BANKNOTE_WIDTH_MM = 65

DENOMINATIONS = [
    {
        "value": 100_000,
        "label_id": "Seratus Ribu Rupiah",
        "length_mm": 151,
        "aspect_ratio": 151 / 65,
        "hue_ranges": [(0, 12), (165, 179)],   # Red (wraps at 0/180)
        "min_saturation": 60,
        "max_saturation": 255,
        "_test_hsv": (6, 160, 150),
    },
    {
        "value": 50_000,
        "label_id": "Lima Puluh Ribu Rupiah",
        "length_mm": 149,
        "aspect_ratio": 149 / 65,
        "hue_ranges": [(100, 130)],             # Blue
        "min_saturation": 60,
        "max_saturation": 255,
        "_test_hsv": (115, 160, 150),
    },
    {
        "value": 20_000,
        "label_id": "Dua Puluh Ribu Rupiah",
        "length_mm": 147,
        "aspect_ratio": 147 / 65,
        "hue_ranges": [(40, 85)],               # Green
        "min_saturation": 60,
        "max_saturation": 255,
        "_test_hsv": (62, 160, 150),
    },
    {
        "value": 10_000,
        "label_id": "Sepuluh Ribu Rupiah",
        "length_mm": 145,
        "aspect_ratio": 145 / 65,
        "hue_ranges": [(130, 160)],             # Purple / Violet
        "min_saturation": 50,
        "max_saturation": 255,
        "_test_hsv": (145, 150, 150),
    },
    {
        "value": 5_000,
        "label_id": "Lima Ribu Rupiah",
        "length_mm": 143,
        "aspect_ratio": 143 / 65,
        "hue_ranges": [(8, 28)],                # Brown / dark orange
        "min_saturation": 50,
        "max_saturation": 255,
        "_test_hsv": (18, 150, 150),
    },
    {
        "value": 2_000,
        "label_id": "Dua Ribu Rupiah",
        "length_mm": 141,
        "aspect_ratio": 141 / 65,
        "hue_ranges": [(70, 100)],              # Teal / grey-green
        "min_saturation": 25,
        "max_saturation": 255,
        "_test_hsv": (85, 120, 140),
    },
    {
        "value": 1_000,
        "label_id": "Seribu Rupiah",
        "length_mm": 139,
        "aspect_ratio": 139 / 65,
        "hue_ranges": [(0, 179)],               # Silver/grey: any hue, LOW saturation
        "min_saturation": 0,
        "max_saturation": 35,
        "_test_hsv": (90, 20, 175),
    },
]

DENOMINATIONS.sort(key=lambda d: d["aspect_ratio"], reverse=True)

# -----------------------------------------------------------------------
# Matching tolerances
# -----------------------------------------------------------------------
# Gap between adjacent ARs: 2/65 ≈ 0.031
# Tolerance 0.013 leaves a ~0.005 dead zone on each side
ASPECT_RATIO_TOLERANCE = 0.013

# Minimum fraction of pixels matching target hue (pixel-fraction check)
MIN_HUE_PIXEL_FRACTION = 0.10

# Dominant hue tolerance: the peak hue must land within ±HUE_PEAK_MARGIN
# bins of the target range edges
HUE_PEAK_MARGIN = 8

# Geometry alone can classify when color is ambiguous (grey denominations)
REQUIRE_BOTH_FEATURES = True

# -----------------------------------------------------------------------
# Contour detection
# -----------------------------------------------------------------------
MIN_CONTOUR_AREA_RATIO = 0.05    # 5% of frame (allows more distance)
MAX_CONTOUR_AREA_RATIO = 0.97
# Canny thresholds (fallback; adaptive uses Otsu auto-calc)
CANNY_THRESHOLD_LOW  = 30
CANNY_THRESHOLD_HIGH = 120

# Valid banknote shape: aspect ratio must fall in this range or reject
MIN_SHAPE_AR = 1.80
MAX_SHAPE_AR = 2.75

# -----------------------------------------------------------------------
# Rectification
# -----------------------------------------------------------------------
WARP_OUTPUT_WIDTH = 800

# -----------------------------------------------------------------------
# Auto-detection stability (main.py)
# -----------------------------------------------------------------------
STABILITY_FRAMES  = 8     # consecutive identical results needed
COOLDOWN_SECONDS  = 2.8   # pause after announcement before next detection
NO_MONEY_MSG_INTERVAL = 5.0  # seconds between "tidak terdeteksi" audio cues

# -----------------------------------------------------------------------
# Camera
# -----------------------------------------------------------------------
CAMERA_INDEX  = 0
FRAME_WIDTH   = 1280
FRAME_HEIGHT  = 720