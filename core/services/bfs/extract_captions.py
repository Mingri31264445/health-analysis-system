"""
從 BFS 的 PDF 報告中擷取每個象限的說明文字。
用日期字串（例如 "2025/7/25"）當錨點找出每一行的位置，
再依錨點的 x0 / top 座標分群，判斷屬於左上/右上/左下/右下哪個象限。
"""

import re

import pdfplumber

DATE_PATTERN = re.compile(r'^\d{4}/\d{1,2}/\d{1,2}$')
LEADING_NUMBER_PATTERN = re.compile(r'^\d+')


def _cluster_into_two_groups(values):
    """
    用最大間隙當分界把一維數值分成兩群，
    只有一群數值時全部歸類為群 0
    """
    uniq_sorted = sorted(set(values))
    if len(uniq_sorted) <= 1:
        return {v: 0 for v in uniq_sorted}
    gaps = [(uniq_sorted[i + 1] - uniq_sorted[i], i) for i in range(len(uniq_sorted) - 1)]
    _, split_at = max(gaps)
    return {v: (0 if v <= uniq_sorted[split_at] else 1) for v in uniq_sorted}


def extract_captions(pdf_path, page_index=0):
    """
    回傳一組 tuple：(captions, dates)
    captions 格式：{"左上": "脾-消化系統-胃前壁ANTERIOR WALL OF STOMACH", ...}
    dates    格式：{"左上": "2025/7/25", ...}
    兩者的 key（象限）完全一致，只回傳實際存在說明文字的象限。
    """
    captions = {}
    dates = {}

    with pdfplumber.open(pdf_path) as pdf:
        page = pdf.pages[page_index]
        words = page.extract_words()
        anchors = [w for w in words if DATE_PATTERN.match(w["text"])]

        x_group_of = _cluster_into_two_groups([a["x0"] for a in anchors]) #X
        top_group_of = _cluster_into_two_groups([a["top"] for a in anchors]) #Y

        for anchor in anchors:
            same_row_anchors = [
                a for a in anchors
                if abs(a["top"] - anchor["top"]) < 2 and a["x0"] > anchor["x0"]
            ]
            boundary_x = min((a["x0"] for a in same_row_anchors), default=page.width + 1)

            # 抓出跟日期在同一排（高度差小於 2），且橫向範圍剛好落在日期與右邊界之間的文字。
            same_line_words = [
                w for w in words
                if abs(w["top"] - anchor["top"]) < 2
                and anchor["x0"] <= w["x0"] < boundary_x
            ]

            next_anchor_top = min(
                (a["top"] for a in anchors
                 if a["top"] > anchor["top"] + 2 and anchor["x0"] <= a["x0"] < boundary_x),
                default=anchor["top"] + 20
            )
            wrap_words = [
                w for w in words
                if anchor["top"] + 2 < w["top"] < min(anchor["top"] + 20, next_anchor_top)
                and anchor["x0"] <= w["x0"] < boundary_x
            ]

            line_words = same_line_words + wrap_words
            line_words.sort(key=lambda w: (round(w["top"] / 5), w["x0"]))
            full_line = " ".join(w["text"] for w in line_words)

            after_date = full_line[len(anchor["text"]):].strip()
            clean_text = LEADING_NUMBER_PATTERN.sub("", after_date)

            is_left = x_group_of[anchor["x0"]] == 0
            is_upper = top_group_of[anchor["top"]] == 0
            if is_left and is_upper:
                quadrant = "左上"
            elif not is_left and is_upper:
                quadrant = "右上"
            elif is_left and not is_upper:
                quadrant = "左下"
            else:
                quadrant = "右下"

            captions[quadrant] = clean_text
            dates[quadrant] = anchor["text"]

    return captions, dates