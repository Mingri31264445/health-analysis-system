from .system_mapping import (
    FACE_ORGAN_SYSTEMS, FACE_ZONE_SYSTEMS, MERIDIAN_SYSTEMS, QUESTIONNAIRE_FIELD_SYSTEMS,
    SYSTEMS, SYSTEM_KEYS, bfs_quadrant_systems,
)

QUESTIONNAIRE_HISTORY_FIELDS = (
    "autoimmune_disease", "cardiovascular_disease", "diabetes",
    "chronic_hepatitis", "heart_disease", "heart_valve_insufficiency",
    "liver_cirrhosis", "liver_disease", "spleen_enlarged",
    "lung_tuberculosis", "lung_asthma", "lung_inflammation", "lung_covid19",
    "kidney_disease", "kidney_stone", "hemodialysis", "stomach_ulcer",
    "stomach_reflux", "intestine_inflammation", "intestine_disease",
    "gallbladder_stone", "gallbladder_inflammation", "bladder_stone",
    "bladder_inflammation", "uterine_inflammation", "uterine_tumor",
    "uterine_syndrome", "other_chronic", "other_cancer", "other_nerve",
    "other_disease", "surgery_history",
)

MODULES = (
    ("questionnaire", "健康問卷"),
    ("face", "面診影像"),
    ("bfs", "BFS 檢測"),
    ("meridian", "經絡儀檢測"),
)


def _result(state="pending", reason="尚未選擇資料"):
    return {"state": state, "reason": reason}


def questionnaire_result(questionnaire):
    if questionnaire is None:
        return _result()
    has_history = any(
        bool(getattr(questionnaire, field)) for field in QUESTIONNAIRE_HISTORY_FIELDS
    )
    return _result(
        "yes" if has_history else "no",
        "自述有疾病或手術史" if has_history else "自述無疾病或手術史",
    )


def face_result(face):
    if face is None:
        return _result()
    if face.analysis_status == "failed":
        return _result(reason="面診分析失敗，無法判定")
    if face.analysis_status != "done":
        return _result(reason="面診尚未完成分析")

    total = (face.analysis_report or {}).get("total") or 0
    if total > 0:
        return _result("yes", f"偵測到 {total} 處臉部病灶")
    return _result("no", "無偵測到臉部病灶")


def bfs_result(bfs):
    if bfs is None:
        return _result()
    if bfs.needs_date_review:
        return _result(reason="檢測日期尚待確認")

    files = list(bfs.files.all())
    if not files:
        return _result(reason="尚無 BFS 解析檔案")

    positive = False
    for item in files:
        result = item.analysis_result or {}
        color = result.get("color_analysis") or {}
        counts = color.get("quadrant_counts") or {}
        if item.analysis_status != "success" or not counts or not color.get("total_all"):
            return _result(reason="BFS 檔案尚未全部完成解析")
        if any(
            quadrant.get(level, quadrant.get(str(level), 0)) > 0
            for quadrant in counts.values()
            for level in (5, 6)
        ):
            positive = True

    return _result(
        "yes" if positive else "no",
        "出現異常或嚴重的項目" if positive else "尚無出現異常或嚴重的項目",
    )

def _meridian_limits(meridian):
    """回傳 (高線, 低線, 是否用過高／過低線, 12 筆讀數)；資料不完整時回傳 None。"""
    # 5 線報告用「過高／過低」線；3 線報告沒有這兩條，退回用「高／低」線
    uses_extreme_lines = (
        meridian.threshold_toohigh is not None
        and meridian.threshold_toolow is not None
    )
    high = meridian.threshold_toohigh if uses_extreme_lines else meridian.threshold_high
    low = meridian.threshold_toolow if uses_extreme_lines else meridian.threshold_low
    readings = list(meridian.readings.all())
    if high is None or low is None or high <= low or len(readings) != 12:
        return None
    return high, low, uses_extreme_lines, readings


def _reading_is_abnormal(reading, high, low):
    return any(
        value is not None and (value > high or value < low)
        for value in (
            reading.left_org, reading.left_cmp,
            reading.right_org, reading.right_cmp,
        )
    )


def meridian_result(meridian):
    if meridian is None:
        return _result()

    limits = _meridian_limits(meridian)
    if limits is None:
        return _result(reason="經絡儀門檻或讀數尚未完整")
    high, low, uses_extreme_lines, readings = limits

    positive = any(_reading_is_abnormal(reading, high, low) for reading in readings)
    label = "過旺／過低" if uses_extreme_lines else "高／低"
    return _result(
        "yes" if positive else "no",
        f"讀數出現在{label}的門檻值外" if positive else f"讀數皆落在{label}的門檻值內",
    )

def overall_from_states(states):
    if not all(state in ("yes", "no") for state in states):
        return ""
    count = states.count("yes")
    return "green" if count == 0 else "yellow" if count <= 2 else "red"


def build_report_data(selected):
    evaluators = {
        "questionnaire": questionnaire_result,
        "face": face_result,
        "bfs": bfs_result,
        "meridian": meridian_result,
    }
    dates = {
        "questionnaire": "updated_at",
        "face": "diagnosis_date",
        "bfs": "test_date",
        "meridian": "test_date",
    }
    records = {}
    results = {}
    for key, _label in MODULES:
        obj = selected.get(key)
        date = getattr(obj, dates[key], None) if obj is not None else None
        records[key] = {
            "id": obj.pk if obj is not None else None,
            "date": date.isoformat() if date is not None else None,
        }
        results[key] = evaluators[key](obj)
    # 分系統對照跟著這次儲存的結果一起存，之後資料變動也不會影響已儲存的報告
    results["systems"] = build_system_rows(selected)

    states = [results[key]["state"] for key, _label in MODULES]
    overall = overall_from_states(states)
    return records, results, overall


# ───────────────────────── 分系統對照（七個系統 × 四個模組）─────────────────────────

def _all_systems(result):
    return {key: dict(result) for key in SYSTEM_KEYS}


def _system_cell(positive, yes_reason, no_reason):
    return _result("yes" if positive else "no", yes_reason if positive else no_reason)


def questionnaire_systems(questionnaire):
    if questionnaire is None:
        return _all_systems(_result())
    cells = {}
    for key in SYSTEM_KEYS:
        hits = [f for f in QUESTIONNAIRE_FIELD_SYSTEMS[key] if getattr(questionnaire, f, False)]
        cells[key] = _system_cell(bool(hits), "自述有相關疾病或手術史", "未填報相關疾病")
    return cells


def face_systems(face):
    base = face_result(face)
    if base["state"] == "pending":
        return _all_systems(base)
    if base["state"] == "no":
        return _all_systems(_result("no", "未偵測到候選病灶"))

    zones = (face.analysis_report or {}).get("zones") or {}
    if not zones:
        return _all_systems(_result(reason="此面診沒有分區資料，請重新分析"))
    hit = set()
    for zone in zones.get("hit_zones") or []:
        systems = FACE_ORGAN_SYSTEMS.get(zone.get("organ")) or FACE_ZONE_SYSTEMS.get(zone.get("id"), ())
        hit.update(systems)
    return {
        key: _system_cell(key in hit, "對應分區偵測到候選病灶", "對應分區未偵測到候選病灶")
        for key in SYSTEM_KEYS
    }


def _has_severe_level(counts):
    return any(counts.get(level, counts.get(str(level), 0)) > 0 for level in (5, 6))


def bfs_systems(bfs):
    base = bfs_result(bfs)
    if base["state"] == "pending":
        return _all_systems(base)

    covered = set()
    positive = set()
    for item in bfs.files.all():
        quadrant_counts = ((item.analysis_result or {}).get("color_analysis") or {}).get("quadrant_counts") or {}
        for quadrant, systems in bfs_quadrant_systems(item.detected_template).items():
            covered.update(systems)
            if _has_severe_level(quadrant_counts.get(quadrant) or {}):
                positive.update(systems)

    cells = {}
    for key in SYSTEM_KEYS:
        if key not in covered:
            cells[key] = _result(reason="尚未上傳含此系統的 BFS 檔案")
        else:
            cells[key] = _system_cell(key in positive, "對應象限出現第 5 或 6 級項目", "對應象限未出現第 5 或 6 級項目")
    return cells


def meridian_systems(meridian):
    base = meridian_result(meridian)
    if base["state"] == "pending":
        return _all_systems(base)

    high, low, uses_extreme_lines, readings = _meridian_limits(meridian)
    scope = "紅色警示範圍" if uses_extreme_lines else "高／低門檻外"
    covered = set()
    positive = set()
    for reading in readings:
        systems = MERIDIAN_SYSTEMS.get(reading.meridian, ())
        covered.update(systems)
        if _reading_is_abnormal(reading, high, low):
            positive.update(systems)

    cells = {}
    for key in SYSTEM_KEYS:
        if key not in covered:
            cells[key] = _result(reason="沒有對應的經絡讀數")
        else:
            cells[key] = _system_cell(key in positive, f"對應經絡讀數出現在{scope}", f"對應經絡讀數未進入{scope}")
    return cells


def build_system_rows(selected):
    """七個系統 × 四個模組；每列的燈號沿用總燈號規則（四格都有有效判定才亮）。"""
    evaluators = {
        "questionnaire": questionnaire_systems,
        "face": face_systems,
        "bfs": bfs_systems,
        "meridian": meridian_systems,
    }
    per_module = {key: evaluators[key](selected.get(key)) for key, _label in MODULES}
    rows = []
    for system_key, system_label in SYSTEMS:
        cells = [
            {"module": module_key, **per_module[module_key][system_key]}
            for module_key, _label in MODULES
        ]
        rows.append({
            "key": system_key,
            "label": system_label,
            "cells": cells,
            "overall": overall_from_states([cell["state"] for cell in cells]),
        })
    return rows
