# calibrator.py - Auto HSV calibration from live detections

import json
import os
import time
import numpy as np

_CALIB_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "calibration_profile.json")
_MIN_SAMPLES = 5
_MAX_SAMPLES = 100


class CalibrationProfile:
    def __init__(self):
        self.profiles: dict[int, dict] = {}
        self.load()

    def load(self):
        if os.path.exists(_CALIB_FILE):
            try:
                with open(_CALIB_FILE, "r") as f:
                    data = json.load(f)
                self.profiles = {int(k): v for k, v in data.get("profiles", {}).items()}
            except (json.JSONDecodeError, IOError):
                self.profiles = {}

    def save(self):
        data = {
            "profiles": {str(k): v for k, v in self.profiles.items()},
            "updated": time.time(),
        }
        try:
            with open(_CALIB_FILE, "w") as f:
                json.dump(data, f, indent=2)
        except IOError:
            pass

    def record(self, denomination_value: int, hue: int):
        if hue is None or hue < 0:
            return
        profile = self.profiles.setdefault(denomination_value, {"hue_values": [], "min_saturation": 50})
        hue_list = profile["hue_values"]
        hue_list.append(hue)
        if len(hue_list) > _MAX_SAMPLES:
            hue_list[:len(hue_list) - _MAX_SAMPLES] = []
        if len(hue_list) % 5 == 0:
            self.save()

    def has_data(self, denomination_value: int) -> bool:
        return denomination_value in self.profiles and len(self.profiles[denomination_value].get("hue_values", [])) >= _MIN_SAMPLES

    def get_hue_ranges(self, denomination_value: int, fallback_ranges: list) -> list:
        if not self.has_data(denomination_value):
            return fallback_ranges
        hues = np.array(self.profiles[denomination_value]["hue_values"])
        p10, p90 = int(np.percentile(hues, 10)), int(np.percentile(hues, 90))
        p10 = max(0, min(179, p10))
        p90 = max(0, min(179, p90))
        if p90 - p10 < 10:
            mid = (p10 + p90) // 2
            margin = 15
            p10 = max(0, mid - margin)
            p90 = min(179, mid + margin)
        # handle red wrap-around
        if p90 - p10 > 90:
            return [(0, p90), (p10, 179)]
        return [(p10, p90)]

    def get_min_saturation(self, denomination_value: int, fallback: int = 50) -> int:
        if not self.has_data(denomination_value):
            return fallback
        return self.profiles[denomination_value].get("min_saturation", fallback)

    def get_max_saturation(self, denomination_value: int, fallback: int = 255) -> int:
        return fallback


_calibrator = CalibrationProfile()


def get_calibrator() -> CalibrationProfile:
    return _calibrator


def record_hue(denomination_value: int, hue: int):
    _calibrator.record(denomination_value, hue)


def get_hue_ranges(denomination_value: int, fallback_ranges: list) -> list:
    return _calibrator.get_hue_ranges(denomination_value, fallback_ranges)


def save_calibration():
    _calibrator.save()
