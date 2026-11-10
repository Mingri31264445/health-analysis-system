"""
綜合分析結果：七個身體系統 × 四個模組的對照表（純資料，方便老師審閱與修改）。

系統清單取自常見的人體十一大系統，挑出「四個模組都有資料來源」的七個：
神經、內分泌、心血管、淋巴與免疫、呼吸、消化、泌尿（生殖器官併入泌尿，與 BFS 的「泌尿生殖系統」一致）。
骨骼、肌肉、外皮系統沒有任何模組能提供資料，因此不列入。

一個項目可以同時屬於兩個以上的系統；每格只顯示有／無，不會因此重複計數。
標 [待老師確認] 的是為了讓四個模組都有對應而做的中醫對應。
"""
import json
from functools import lru_cache
from pathlib import Path

SYSTEMS = (
    ("neuro", "神經系統"),
    ("endocrine", "內分泌系統"),
    ("cardio", "心血管系統"),
    ("immune", "淋巴與免疫系統"),
    ("respiratory", "呼吸系統"),
    ("digestive", "消化系統"),
    ("urinary", "泌尿生殖系統"),
)
SYSTEM_KEYS = tuple(key for key, _label in SYSTEMS)

# ── 問卷：欄位 → 系統 ──────────────────────────────────────────────
# 不歸任何系統（只計入問卷整體）：other_chronic、other_cancer、other_disease、surgery_history
QUESTIONNAIRE_FIELD_SYSTEMS = {
    "neuro": ("other_nerve",),
    "endocrine": ("diabetes",),
    "cardio": ("cardiovascular_disease", "heart_disease", "heart_valve_insufficiency"),
    "immune": ("autoimmune_disease", "spleen_enlarged"),
    "respiratory": ("lung_tuberculosis", "lung_asthma", "lung_inflammation", "lung_covid19"),
    "digestive": (
        "stomach_ulcer", "stomach_reflux", "intestine_inflammation", "intestine_disease",
        "chronic_hepatitis", "liver_cirrhosis", "liver_disease",
        "gallbladder_stone", "gallbladder_inflammation",
    ),
    "urinary": (
        "kidney_disease", "kidney_stone", "hemodialysis",
        "bladder_stone", "bladder_inflammation",
        "uterine_inflammation", "uterine_tumor", "uterine_syndrome",
    ),
}

# ── 面診：分區的臟腑名稱（zones.py 的 ZONE_INFO[...]['organ']）→ 系統 ──
FACE_ORGAN_SYSTEMS = {
    "首面": ("neuro",),
    "心、情志": ("neuro", "cardio"),
    "心": ("cardio",),
    "心腎之交": ("cardio", "urinary"),
    "咽喉": ("respiratory",),
    "肺": ("respiratory",),
    "氣管": ("respiratory",),
    "胸": ("respiratory",),
    "乳房(胸)": ("respiratory",),
    "脾": ("digestive", "immune"),
    "胃": ("digestive",),
    "小腸": ("digestive",),
    "大腸": ("digestive",),
    "十二指腸": ("digestive",),
    "升結腸": ("digestive",),
    "橫結腸": ("digestive",),
    "降結腸": ("digestive",),
    "肝": ("digestive",),
    "膽": ("digestive",),
    "胰": ("digestive", "endocrine"),
    "淋巴": ("immune",),
    "腎": ("urinary",),
    "腎、疲勞酸痛": ("urinary",),
    "膀胱": ("urinary",),
    "膀胱、胞宮": ("urinary",),
    "子宮、攝護腺": ("urinary",),
    "卵巢": ("urinary",),
}
# 來源文件沒有標臟腑（organ 為「—」）的區域，改用區域代號判斷
FACE_ZONE_SYSTEMS = {
    "temple_L": ("neuro",),
    "temple_R": ("neuro",),
}

# ── BFS：象限說明文字「臟-系統-部位」的「系統」欄位 → 系統 ──
BFS_SYSTEM_LABELS = {
    "腦神經系統": "neuro",
    "內分泌系統": "endocrine",
    "心血管系統": "cardio",
    "免疫系統": "immune",
    "呼吸系統": "respiratory",
    "消化系統": "digestive",
    "泌尿生殖系統": "urinary",
}
# 同一個象限裡的器官另外屬於其他系統時，用部位文字補上
# （bfs1 左下「胰腺和脾臟」：胰腺屬內分泌、脾臟屬免疫）
BFS_PART_KEYWORDS = (
    ("胰腺", "endocrine"),
    ("脾臟", "immune"),
)
_BFS_CONFIG = Path(__file__).resolve().parent / "bfs" / "data" / "templates_config.json"


@lru_cache(maxsize=1)
def _bfs_templates():
    with open(_BFS_CONFIG, encoding="utf-8") as f:
        return json.load(f)


def bfs_quadrant_systems(template_key):
    """回傳 {象限: {系統, ...}}；模板不存在時回傳空 dict。"""
    template = _bfs_templates().get(template_key) or {}
    result = {}
    for quadrant, caption in template.items():
        if quadrant == "coords_file":
            continue
        parts = caption.split("-", 2)
        systems = set()
        if len(parts) == 3 and parts[1] in BFS_SYSTEM_LABELS:
            systems.add(BFS_SYSTEM_LABELS[parts[1]])
        for keyword, system in BFS_PART_KEYWORDS:
            if keyword in caption:
                systems.add(system)
        result[quadrant] = systems
    return result


# ── 經絡儀：12 經絡 → 系統 ──────────────────────────────────────
# [待老師確認] 神經←心經（心藏神）、膀胱（沿脊柱兩側）；內分泌←腎經、三焦；免疫←脾經（西醫的脾臟）
MERIDIAN_SYSTEMS = {
    "肺經": ("respiratory",),
    "大腸": ("digestive",),
    "胃經": ("digestive",),
    "脾經": ("digestive", "immune"),
    "小腸": ("digestive",),
    "肝經": ("digestive",),
    "膽經": ("digestive",),
    "心經": ("cardio", "neuro"),
    "心包": ("cardio",),
    "三焦": ("endocrine",),
    "腎經": ("urinary", "endocrine"),
    "膀胱": ("urinary", "neuro"),
}
