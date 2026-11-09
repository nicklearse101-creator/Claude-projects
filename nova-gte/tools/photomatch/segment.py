"""Photo car silhouette by GrabCut, seeded from the current model render (sure-FG = eroded model mask minus
glass/wheel-free margins, sure-BG = outside a dilated mask)."""
import sys, numpy as np, cv2
from PIL import Image
import preview as pv
c = sys.argv[1]; it = int(sys.argv[2]) if len(sys.argv) > 2 else 5
img, mask = pv.render(c)
ph = np.array(Image.open(pv.PH[c]).convert('RGB'))
H, W = mask.shape
k = max(3, W // 60)
fg = cv2.erode(mask, np.ones((k, k), np.uint8))
bg = cv2.dilate(mask, np.ones((k, k), np.uint8))
gc = np.full((H, W), cv2.GC_PR_BGD, np.uint8)
gc[mask > 0] = cv2.GC_PR_FGD
gc[fg > 0] = cv2.GC_FGD
gc[bg == 0] = cv2.GC_BGD
bgd = np.zeros((1, 65), np.float64); fgd = np.zeros((1, 65), np.float64)
cv2.grabCut(cv2.cvtColor(ph, cv2.COLOR_RGB2BGR), gc, None, bgd, fgd, it, cv2.GC_INIT_WITH_MASK)
seg = np.where((gc == cv2.GC_FGD) | (gc == cv2.GC_PR_FGD), 255, 0).astype(np.uint8)
# keep the largest component, fill holes
n, lab, st, _ = cv2.connectedComponentsWithStats(seg)
if n > 1:
    big = 1 + np.argmax(st[1:, cv2.CC_STAT_AREA]); seg = np.where(lab == big, 255, 0).astype(np.uint8)
cv2.imwrite(f'seg_{c}.png', seg)
o = ph.astype(np.float32)
o[cv2.morphologyEx(seg, cv2.MORPH_GRADIENT, np.ones((3, 3), np.uint8)) > 0] = [255, 0, 255]
o[cv2.morphologyEx(mask, cv2.MORPH_GRADIENT, np.ones((3, 3), np.uint8)) > 0] = [0, 255, 255]
im = Image.fromarray(o.astype(np.uint8)); im.thumbnail((1600, 1200)); im.save(f'seg_{c}.jpg', quality=88)
print('done', c)
