import cv2, sys
import numpy as np
sys.path.insert(0, 'src')
from preprocessor import preprocess, detect_edges
from config import MIN_CONTOUR_AREA_RATIO, MAX_CONTOUR_AREA_RATIO, MIN_SHAPE_AR, MAX_SHAPE_AR

img = cv2.imread('images/50k.png')
preprocessed = preprocess(img)
edges = detect_edges(preprocessed)
h, w = img.shape[:2]
image_area = h * w

contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
print(f'Image: {w}x{h} = {image_area}')
print(f'AR range: [{MIN_SHAPE_AR}, {MAX_SHAPE_AR}], area: [{MIN_CONTOUR_AREA_RATIO}, {MAX_CONTOUR_AREA_RATIO}]')
print()

for i, c in enumerate(contours):
    area = cv2.contourArea(c)
    area_frac = area / image_area
    x, y, bw, bh = cv2.boundingRect(c)
    car = max(bw, bh) / min(bw, bh) if min(bw, bh) > 0 else -1
    hull = cv2.convexHull(c)
    hull_area = cv2.contourArea(hull)
    solidity = area / hull_area if hull_area > 0 else 0
    rect_area = bw * bh
    rectangularity = area / rect_area if rect_area > 0 else 0
    
    # Determine failure reason
    fails = []
    if area_frac < MIN_CONTOUR_AREA_RATIO: fails.append(f'area<{MIN_CONTOUR_AREA_RATIO}')
    if area_frac > MAX_CONTOUR_AREA_RATIO: fails.append(f'area>{MAX_CONTOUR_AREA_RATIO}')
    if bw < 5 or bh < 5: fails.append('small_rect')
    if not (MIN_SHAPE_AR <= car <= MAX_SHAPE_AR): fails.append(f'AR={car:.3f} not in [{MIN_SHAPE_AR},{MAX_SHAPE_AR}]')
    if solidity < 0.5: fails.append(f'solidity={solidity:.3f}')
    if rectangularity < 0.4: fails.append(f'recty={rectangularity:.3f}')
    
    reason = ', '.join(fails) if fails else 'PASS'
    print(f'  #{i}: area_frac={area_frac:.3f} area={area:.0f} BR=({bw}x{bh}) AR={car:.3f} '
          f'solidity={solidity:.3f} recty={rectangularity:.3f} pts={len(c)} -> {reason}')
