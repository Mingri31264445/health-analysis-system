"""
給 Django View 呼叫的主要入口，分析 BFS 的 PDF 檔案，回傳分析結果。
"""

from pathlib import Path

from .extract_captions import extract_captions
from .detect_template import load_templates_config, detect_template
from .color_analysis import analyze_bfs

_DATA_DIR = Path(__file__).resolve().parent / "data"
_CONFIG_PATH = _DATA_DIR / "templates_config.json"
_COORDS_DIR = _DATA_DIR / "coords"

# 判斷單一 PDF 內、各象限日期是否一致
def _resolve_detected_date(dates):
    """
    根據單一 PDF 內、各象限各自抓到的日期，判斷這份 PDF 的
    「偵測日期」結果。
    回傳：{"date": "2025/7/25" 或 None, "status": "ok"/"inconsistent"/"not_found"}
    """
    values = list(dates.values())
    if not values:
        return {"date": None, "status": "not_found"}
    unique_values = set(values)
    if len(unique_values) == 1:
        return {"date": values[0], "status": "ok"}
    return {"date": None, "status": "inconsistent"}


def analyze_bfs_pdf(pdf_path):
    """
    給 Django View 呼叫的主要入口。
    """
    # 1. 擷取說明文字
    try:
        captions, dates = extract_captions(pdf_path)
    except Exception as e:
        return {
            "detected_template": "",
            "analysis_status": "needs_review",
            "analysis_result": {"reason": f"PDF 文字擷取失敗：{e}"},
        }

    # 2. 判斷模板
    date_detection = _resolve_detected_date(dates)
    templates_config = load_templates_config(_CONFIG_PATH)
    detection = detect_template(captions, templates_config)

    if detection["status"] != "success":
        return {
            "detected_template": "",
            "analysis_status": "needs_review",
            "analysis_result": {**detection, "date_detection": date_detection},
        }

    template_key = detection["template"]
    coords_path = _COORDS_DIR / detection["coords_file"]

    # 3. 色彩分析
    try:
        color_result = analyze_bfs(pdf_path, coords_path)
    except Exception as e:
        return {
            "detected_template": template_key,
            "analysis_status": "needs_review",
            "analysis_result": {
                "reason": f"色彩分析失敗：{e}",
                "detection": detection,
                "date_detection": date_detection,
            },
        }

    return {
        "detected_template": template_key,
        "analysis_status": "success",
        "analysis_result": {
            "detection": detection, 
            "color_analysis": color_result,
            "date_detection": date_detection, 
        },
    }