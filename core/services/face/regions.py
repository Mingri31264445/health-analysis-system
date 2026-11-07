"""共用的臉部幾何工具：臉部輪廓、眼部遮罩、色彩統計。

（臟腑分區在 zones.py。）
"""
import math

import cv2
import numpy as np

from . import config

# 臉部輪廓（依序繞一圈）
FACE_OVAL = [10, 338, 297, 332, 284, 251, 389, 356, 454, 323, 361, 288, 397, 365,
             379, 378, 400, 377, 152, 148, 176, 149, 150, 136, 172, 58, 132, 93,
             234, 127, 162, 21, 54, 103, 67, 109]

# 受檢者右眼 / 左眼（用來做眼部遮蔽）
EYE_RIGHT = [33, 160, 158, 133, 153, 144]   # 畫面左側
EYE_LEFT = [362, 385, 387, 263, 373, 380]   # 畫面右側


def face_oval_polygon(points):
    pts = np.asarray(points).round().astype(np.int32)
    return pts[FACE_OVAL]


def polygon_mask(polygon, shape):
    h, w = shape[:2]
    mask = np.zeros((h, w), dtype=np.uint8)
    cv2.fillPoly(mask, [polygon.astype(np.int32)], 255)
    return mask > 0


# 眼睛完整輪廓（依序繞一圈）
EYE_OUTLINE_R = [33, 246, 161, 160, 159, 158, 157, 173, 133, 155, 154, 153, 145, 144, 163, 7]
EYE_OUTLINE_L = [362, 398, 384, 385, 386, 387, 388, 466, 263, 249, 390, 373, 374, 380, 381, 382]


def eye_contour_mask(points, shape, margin=0.05):
    """依眼睛輪廓（不是矩形）做的遮罩：輪廓多邊形再往外擴 margin * 眼距。"""
    pts = np.asarray(points)
    D = float(np.linalg.norm(pts[263] - pts[33]))
    m = np.zeros(shape[:2], dtype=np.uint8)
    for ids in (EYE_OUTLINE_R, EYE_OUTLINE_L):
        cv2.fillPoly(m, [pts[ids].round().astype(np.int32)], 1)
    r = max(2, int(round(margin * D)))
    m = cv2.dilate(m, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * r + 1, 2 * r + 1)))
    return m > 0


def eye_mask(points, shape):
    """雙眼矩形遮罩（True = 眼睛位置）。同時用於隱私遮蔽與排除統計。"""
    h, w = shape[:2]
    pts = np.asarray(points).round().astype(np.int32)
    mask = np.zeros((h, w), dtype=np.uint8)
    for ids in (EYE_RIGHT, EYE_LEFT):
        p = pts[ids]
        x1, y1 = p.min(axis=0)
        x2, y2 = p.max(axis=0)
        dx = max(9, int((x2 - x1) * 0.16))
        dy = max(14, int((y2 - y1) * 0.8))
        cv2.rectangle(mask, (max(0, x1 - dx), max(0, y1 - dy)),
                      (min(w - 1, x2 + dx), min(h - 1, y2 + dy)), 255, -1)
    return mask > 0


def _circular_mean_deg(hues_deg):
    rad = np.deg2rad(hues_deg)
    return float(np.rad2deg(math.atan2(np.sin(rad).mean(), np.cos(rad).mean())) % 360)


def region_stats(img_bgr, masks, exclude=None):
    """各區域色彩統計。

    回傳 {區域: {pixels, R, G, B, H, S, V, L, a, b}}；有效像素不足的區域為 None。
    - RGB：0-255
    - HSV：H 為角度 0-360（紅色附近用圓形平均），S、V 為 0-100
    - Lab：L 0-100；a 越大越偏紅，b 越大越偏黃
    """
    f = img_bgr.astype(np.float32) / 255.0
    hsv = cv2.cvtColor(f, cv2.COLOR_BGR2HSV)
    lab = cv2.cvtColor(f, cv2.COLOR_BGR2Lab)
    gray = img_bgr.mean(axis=2)
    ok = (gray >= config.STAT_DARK) & (img_bgr.max(axis=2) < config.STAT_BRIGHT)
    if exclude is not None:
        ok &= ~exclude

    out = {}
    for name, mask in masks.items():
        valid = mask & ok
        n = int(valid.sum())
        if n < config.STAT_MIN_PIXELS:
            out[name] = None
            continue
        bgr = img_bgr[valid].mean(axis=0)
        h = hsv[..., 0][valid]
        out[name] = {
            "pixels": n,
            "R": round(float(bgr[2]), 1),
            "G": round(float(bgr[1]), 1),
            "B": round(float(bgr[0]), 1),
            "H": round(_circular_mean_deg(h), 1),
            "S": round(float(hsv[..., 1][valid].mean() * 100), 1),
            "V": round(float(hsv[..., 2][valid].mean() * 100), 1),
            "L": round(float(lab[..., 0][valid].mean()), 1),
            "a": round(float(lab[..., 1][valid].mean()), 1),
            "b": round(float(lab[..., 2][valid].mean()), 1),
        }
    return out
