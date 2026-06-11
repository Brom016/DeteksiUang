import cv2, sys
sys.path.insert(0, 'src')
from preprocessor import preprocess, detect_edges, find_banknote_contour
from rectifier import rectify_banknote
from feature_extractor import extract_features
from classifier import classify

for f in ['100k.png','50k.png','20k.png']:
    img = cv2.imread(f'images/{f}')
    if img is None:
        print(f'{f}: cannot load')
        continue
    print(f'=== {f} ({img.shape[1]}x{img.shape[0]}) ===')
    preprocessed = preprocess(img)
    edges = detect_edges(preprocessed)
    contour = find_banknote_contour(edges, img.shape, preprocessed, original_image=img)
    if contour is None:
        print('  -> no_contour')
        continue
    warped, raw_ar = rectify_banknote(img, contour)
    if warped is None:
        print('  -> rectification_failed')
        continue
    features = extract_features(warped)
    if raw_ar > 0:
        features['aspect_ratio'] = raw_ar
    result = classify(warped, features)
    print(f'  Result: {result.get_label()}')
    d = result.debug_info
    for k, v in d.items():
        print(f'    {k}: {v}')
    print()

print('Done')
