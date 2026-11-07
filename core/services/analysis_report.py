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
        "自述有疾病或手術史" if has_history else "未填報相關疾病或手術史",
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
        return _result("yes", f"偵測到 {total} 處候選病灶（模型尚未驗收，僅供輔助參考）")
    return _result("no", "未偵測到候選病灶（模型尚未驗收，僅供輔助參考）")


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
        "出現第 5 或 6 級項目" if positive else "未出現第 5 或 6 級項目",
    )

def meridian_result(meridian):
    if meridian is None:
        return _result()

    # 5 線報告用「過高／過低」線；3 線報告沒有這兩條，退回用「高／低」線
    uses_extreme_lines = (
        meridian.threshold_toohigh is not None
        and meridian.threshold_toolow is not None
    )
    high = meridian.threshold_toohigh if uses_extreme_lines else meridian.threshold_high
    low = meridian.threshold_toolow if uses_extreme_lines else meridian.threshold_low
    readings = list(meridian.readings.all())
    if high is None or low is None or high <= low or len(readings) != 12:
        return _result(reason="經絡儀門檻或讀數尚未完整")

    positive = any(
        value is not None and (value > high or value < low)
        for reading in readings
        for value in (
            reading.left_org, reading.left_cmp,
            reading.right_org, reading.right_cmp,
        )
    )
    scope = "紅色警示範圍" if uses_extreme_lines else "高／低門檻外"
    return _result(
        "yes" if positive else "no",
        f"讀數出現在{scope}" if positive else f"讀數未進入{scope}",
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

    states = [results[key]["state"] for key, _label in MODULES]
    overall = overall_from_states(states)
    return records, results, overall
