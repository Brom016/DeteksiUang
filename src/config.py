# config.py - Central configuration for Rupiah TE 2022 detection system

BANKNOTE_WIDTH_MM = 65

DENOMINATIONS = [
    {
        "value": 100_000,
        "label_id": "Seratus Ribu Rupiah",
        "length_mm": 151,
        "aspect_ratio": 151 / 65,
        "hue_ranges": [(0, 12), (165, 179)],
        "min_saturation": 60,
        "max_saturation": 255,
        "_test_hsv": (6, 160, 150),
    },
    {
        "value": 50_000,
        "label_id": "Lima Puluh Ribu Rupiah",
        "length_mm": 149,
        "aspect_ratio": 149 / 65,
        "hue_ranges": [(100, 130)],
        "min_saturation": 60,
        "max_saturation": 255,
        "_test_hsv": (115, 160, 150),
    },
    {
        "value": 20_000,
        "label_id": "Dua Puluh Ribu Rupiah",
        "length_mm": 147,
        "aspect_ratio": 147 / 65,
        "hue_ranges": [(40, 85)],
        "min_saturation": 60,
        "max_saturation": 255,
        "_test_hsv": (62, 160, 150),
    },
    {
        "value": 10_000,
        "label_id": "Sepuluh Ribu Rupiah",
        "length_mm": 145,
        "aspect_ratio": 145 / 65,
        "hue_ranges": [(130, 160)],
        "min_saturation": 50,
        "max_saturation": 255,
        "_test_hsv": (145, 150, 150),
    },
    {
        "value": 5_000,
        "label_id": "Lima Ribu Rupiah",
        "length_mm": 143,
        "aspect_ratio": 143 / 65,
        "hue_ranges": [(8, 28)],
        "min_saturation": 50,
        "max_saturation": 255,
        "_test_hsv": (18, 150, 150),
    },
    {
        "value": 2_000,
        "label_id": "Dua Ribu Rupiah",
        "length_mm": 141,
        "aspect_ratio": 141 / 65,
        "hue_ranges": [(70, 100)],
        "min_saturation": 25,
        "max_saturation": 255,
        "_test_hsv": (85, 120, 140),
    },
    {
        "value": 1_000,
        "label_id": "Seribu Rupiah",
        "length_mm": 139,
        "aspect_ratio": 139 / 65,
        "hue_ranges": [(0, 179)],
        "min_saturation": 0,
        "max_saturation": 35,
        "_test_hsv": (90, 20, 175),
    },
]

DENOMINATIONS.sort(key=lambda d: d["aspect_ratio"], reverse=True)

# Auto-calibration: dynamically learn hue ranges from live detections
AUTO_CALIBRATE = True

# Matching tolerances
ASPECT_RATIO_TOLERANCE = 0.013
MIN_HUE_PIXEL_FRACTION = 0.10
HUE_PEAK_MARGIN = 8



# Contour detection
MIN_CONTOUR_AREA_RATIO = 0.05
MAX_CONTOUR_AREA_RATIO = 0.97
MIN_SHAPE_AR = 1.80
MAX_SHAPE_AR = 2.75

# Rectification
WARP_OUTPUT_WIDTH = 800

# Auto-detection stability (main.py)
STABILITY_FRAMES = 8
COOLDOWN_SECONDS = 2.8
NO_MONEY_MSG_INTERVAL = 5.0

# Camera
CAMERA_INDEX = 0
CAMERA_URL = "http://10.22.24.170:8080/video"
FRAME_WIDTH = 1280
FRAME_HEIGHT = 720

# Display resize factor (1.0 = original, 0.75 = 75% size)
DISPLAY_SCALE = 0.80
