import cv2, sys
sys.path.insert(0, 'src')
from preprocessor import preprocess, detect_edges, find_banknote_contour
from rectifier import rectify_banknote
from feature_extractor import extract_features
from classifier import classify

img = cv2.imread('images/100k.png')
preprocessed = preprocess(img)
edges = detect_edges(preprocessed)
cv2.imwrite('images/debug_100k_preprocessed.jpg', preprocessed)
cv2.imwrite('images/debug_100k_edges.jpg', edges)

contour = find_banknote_contour(edges, img.shape, preprocessed, original_image=img)
if contour is not None:
    cpy = img.copy()
    cv2.drawContours(cpy, [contour], -1, (0,0,255), 2)
    cv2.imwrite('images/debug_100k_contour.jpg', cpy)
    print(f'Contour found, {len(contour)} points')
    warped, raw_ar = rectify_banknote(img, contour)
    if warped is not None:
        cv2.imwrite('images/debug_100k_warped.jpg', warped)
        print(f'Warped shape: {warped.shape}, raw_ar={raw_ar:.4f}')
        h, w = warped.shape[:2]
        print(f'Image AR: {w/h:.4f}')
    else:
        print('Rectification failed')
else:
    print('No contour found (100k)')
    print(f'Edges shape={edges.shape}, sum={edges.sum()}')

print()
# Also save edges for 50k
img2 = cv2.imread('images/50k.png')
pre2 = preprocess(img2)
edges2 = detect_edges(pre2)
cv2.imwrite('images/debug_50k_edges.jpg', edges2)
contour2 = find_banknote_contour(edges2, img2.shape, pre2, original_image=img2)
if contour2 is not None:
    print('50k: contour found')
    cpy2 = img2.copy()
    cv2.drawContours(cpy2, [contour2], -1, (0,0,255), 2)
    cv2.imwrite('images/debug_50k_contour.jpg', cpy2)
    warped2, raw_ar2 = rectify_banknote(img2, contour2)
    if warped2 is not None:
        print(f'50k warped: {warped2.shape}, raw_ar={raw_ar2:.4f}')
        cv2.imwrite('images/debug_50k_warped.jpg', warped2)
else:
    print('50k: no contour found')

print('Done debugging')
