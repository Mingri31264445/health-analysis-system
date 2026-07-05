"""
BFS 顏色統計核心邏輯。
"""

import json

import cv2
import numpy as np
from pdf2image import convert_from_path

QUADRANTS = ["左上", "右上", "左下", "右下"]

LEVELS = {
    1: {"name": "活躍", "rgb": (255, 255, 150)},
    2: {"name": "理想", "rgb": (255, 255,   0)},
    3: {"name": "暫緩", "rgb": (253,  95,   0)},
    4: {"name": "減弱", "rgb": (255,   0,   0)},
    5: {"name": "異常", "rgb": (128,   0,   0)},
    6: {"name": "嚴重", "rgb": (  0,   0,   0)},
}
SAMPLE_RADIUS = 3
SUSPICIOUS_DIST_THRESHOLD = 80


def load_coords(coords_json_path):
    with open(coords_json_path, encoding="utf-8") as f:
        data = json.load(f)
    return {q: [tuple(p) for p in data[q]] for q in QUADRANTS if q in data}


def _sample_color(img, x, y, radius=SAMPLE_RADIUS):
    h, w = img.shape[:2]
    x1, x2 = max(0, x - radius), min(w, x + radius + 1)
    y1, y2 = max(0, y - radius), min(h, y + radius + 1)
    region = img[y1:y2, x1:x2] # 取得樣本區域
    avg_bgr = region.mean(axis=(0, 1))
    return (int(avg_bgr[2]), int(avg_bgr[1]), int(avg_bgr[0])) # 將OpenCV的BGR轉成RGB


def _closest_level(rgb):
    best_level, best_dist = 1, float("inf")
    r, g, b = rgb
    for level, info in LEVELS.items():
        lr, lg, lb = info["rgb"]
        dist = ((r - lr) ** 2 + (g - lg) ** 2 + (b - lb) ** 2) ** 0.5 # 三維兩點間距離
        if dist < best_dist:
            best_dist = dist
            best_level = level
    return best_level, best_dist


def analyze_bfs(pdf_path, coords_json_path, dpi=150):
    coords_by_quadrant = load_coords(coords_json_path)

    images = convert_from_path(pdf_path, dpi=dpi)
    img = cv2.cvtColor(np.array(images[0]), cv2.COLOR_RGB2BGR)

    quadrant_counts = {q: {i: 0 for i in range(1, 7)} for q in coords_by_quadrant} # 各象限的顏色等級計數
    quadrant_totals = {q: 0 for q in coords_by_quadrant}
    suspicious = [] # 疑似異常點

    point_index = 0
    for quadrant, points in coords_by_quadrant.items():
        for (x, y) in points:
            point_index += 1
            rgb = _sample_color(img, x, y)
            level, dist = _closest_level(rgb)

            quadrant_counts[quadrant][level] += 1
            quadrant_totals[quadrant] += 1

            # 色彩距離過大，可能是異常點
            if dist > SUSPICIOUS_DIST_THRESHOLD:
                suspicious.append({
                    "index": point_index, "x": x, "y": y, "rgb": rgb,
                    "level": level, "distance": round(dist, 1), "quadrant": quadrant,
                })

    return {
        "quadrant_counts": quadrant_counts,
        "quadrant_totals": quadrant_totals,
        "total_all": sum(quadrant_totals.values()),
        "suspicious": suspicious,
        "regions_present": list(coords_by_quadrant.keys()),
    }