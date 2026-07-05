"""
自動判斷 BFS PDF 屬於 templates_config.json 裡的哪一種模板。
"""

import json


def load_templates_config(config_path):
    with open(config_path, encoding="utf-8") as f:
        return json.load(f)


def detect_template(captions, templates_config):
    """
    用左上角快速對答案，再交叉驗證其他象限的說明文字是否符合模板。
    """
    top_left_text = captions.get("左上")

    if not top_left_text:
        return {
            "status": "needs_review",
            "reason": "PDF 中找不到左上象限的說明文字，可能是頁面格式異常",
            "detail": {"captions": captions},
        }

    candidates = [
        key for key, tmpl in templates_config.items()
        if tmpl.get("左上") == top_left_text
    ]

    if not candidates:
        return {
            "status": "needs_review",
            "reason": "左上文字在對照表中找不到符合的模板",
            "detail": {"captions": captions, "top_left_text": top_left_text},
        }

    best_result = None

    for key in candidates:
        tmpl = templates_config[key]
        mismatches = []
        for quadrant, text in captions.items():
            if quadrant == "左上":
                continue
            expected = tmpl.get(quadrant) #應該出現的文字
            if expected is None:
                mismatches.append({"quadrant": quadrant, "extracted": text,
                                    "expected": None, "note": "模板裡沒有這個象限"})
            elif expected != text:
                mismatches.append({"quadrant": quadrant, "extracted": text, "expected": expected})

        if not mismatches:
            return {
                "status": "success",
                "template": key,
                "coords_file": tmpl.get("coords_file"),
                "detail": {"captions": captions, "matched_candidate": key},
            }
        
        # 找出最接近的候選模板
        if best_result is None or len(mismatches) < len(best_result["mismatches"]):
            best_result = {"candidate": key, "mismatches": mismatches}

    return {
        "status": "needs_review",
        "reason": "左上文字有對到候選模板，但其他象限交叉驗證失敗",
        "detail": {
            "captions": captions,
            "candidates_tried": candidates,
            "closest_candidate": best_result["candidate"],
            "mismatches": best_result["mismatches"],
        },
    }