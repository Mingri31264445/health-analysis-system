"""
面診分區落位（轉接層）

把面診引擎的輸出(校正後的照片、478 個臉部關鍵點、偵測框)交給分區模組，
統計各區域、臟腑的候選病灶數，並產生「分區＋圈選＋圖例」總覽圖。
"""
from collections import Counter
from pathlib import Path

import cv2
import numpy as np

from .regions import region_stats
from .render import render_zone_overview
from .zones import (
    BAND_NAMES,
    BAND_ZH,
    ZONE_IDS,
    ZONE_INFO,
    assign_band,
    assign_zone,
    build_zones,
    zone_display_name,
)

OVERVIEW_NAME = 'zones_overview.png'
PHOTO_NAME = 'zones_photo.png'
TARGET_HEIGHT = 1000  # 總覽圖的照片高度，要和 render.py 的預設一致
OTHER_ORGAN = '其他'
# 來源文件把症狀和臟腑寫在同一格，彙總臟腑時只取臟腑本身
ORGAN_ALIAS = {'心、情志': '心', '腎、疲勞酸痛': '腎'}


def _read_image(path):
    image = cv2.imdecode(np.fromfile(str(path), np.uint8), cv2.IMREAD_COLOR)
    if image is None:
        raise ValueError(f'無法讀取圖片：{path}')
    return image


def analyze_zones(preprocessed_path, landmarks, detections, output_path):
    """分區落位。

    preprocessed_path:校正後的照片(座標系統與 landmarks、偵測框相同)
    landmarks:478 個 [x, y]
    detections:[{'box': [x1, y1, x2, y2], ...}]，會在每一筆加上 'zone'、'band' 欄位
    output_path:總覽圖的存檔路徑

    回傳可存進 analysis_report['zones'] 的 dict。
    """
    image = _read_image(preprocessed_path)
    points = np.asarray(landmarks, dtype=np.float32)
    zones = build_zones(points, image.shape)

    lesions = []
    for item in detections:
        zone_id = assign_zone(item['box'], zones)
        band = assign_band(item['box'], zones)
        item['zone'] = zone_display_name(zone_id) if zone_id != 'none' else '臟腑分區外'
        item['band'] = band
        lesions.append({'box': item['box'], 'zone_id': zone_id, 'band': band})

    zone_count = Counter(l['zone_id'] for l in lesions)
    band_count = Counter(l['band'] for l in lesions)
    outside = zone_count.get('none', 0)

    # 總覽圖：照片 + 分區 + 病灶圈選 + 右側圖例
    colors = region_stats(image, zones['masks'])  # 各區平均顏色，圖例用
    zone_rows = [
        {'idx': i, 'id': zid, 'name': zone_display_name(zid),
         'lesions': zone_count.get(zid, 0),
         'rgb': (colors[zid]['R'], colors[zid]['G'], colors[zid]['B']) if colors.get(zid) else None}
        for i, zid in enumerate(ZONE_IDS)
    ]
    band_rows = [{'name': name, 'lesions': band_count.get(name, 0)} for name in BAND_NAMES]
    overview = render_zone_overview(
        image, zones, zone_rows, band_rows, lesions,
        target_height=TARGET_HEIGHT,
        extra_lines=[f'病灶總數 {len(lesions)}，落在臟腑分區外 {outside}'],
    )
    ok, encoded = cv2.imencode('.png', overview)
    if not ok:
        raise ValueError('總覽圖編碼失敗')
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    encoded.tofile(str(output_path))
    # 另存只有照片的版本給網頁用（右側圖例改由網頁顯示，字才讀得清楚）
    scale = max(1.0, TARGET_HEIGHT / image.shape[0])
    photo = overview[:round(image.shape[0] * scale), :round(image.shape[1] * scale)]
    ok, encoded = cv2.imencode('.png', photo)
    if ok:
        encoded.tofile(str(Path(output_path).parent / PHOTO_NAME))

    # 有病灶的區域，依數量由多到少
    hit_zones = [
        {
            'id': zid,
            'name': zone_display_name(zid),
            'organ': ZONE_INFO[zid]['organ'],
            'count': count,
        }
        for zid, count in zone_count.most_common()
        if zid != 'none'
    ]

    # 依臟腑彙總（「—」代表來源文件沒有對應臟腑，歸到「其他」）
    organ_count = Counter()
    for zone in hit_zones:
        organ = ORGAN_ALIAS.get(zone['organ'], zone['organ'])
        organ_count[OTHER_ORGAN if organ == '—' else organ] += zone['count']

    return {
        'overview_image': OVERVIEW_NAME,
        'photo_image': PHOTO_NAME,
        'legend': [
            {'no': i + 1, 'name': zone_display_name(zid), 'count': zone_count.get(zid, 0)}
            for i, zid in enumerate(ZONE_IDS)
        ],
        'zone_total': len(ZONE_IDS),
        'hit_zones': hit_zones,
        'organs': [{'organ': organ, 'count': count} for organ, count in organ_count.most_common()],
        'bands': [
            {'band': name, 'label': BAND_ZH[name], 'count': band_count.get(name, 0)}
            for name in BAND_NAMES
        ],
        'outside_zone': outside,
    }