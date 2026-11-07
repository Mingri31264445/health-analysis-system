"""所有門檻值集中在這裡，方便調整與在報告中說明。

注意：以下數值是「初始值」，需要用你們實際拍攝的照片校正，
不是經過驗證的標準。
"""

# 處理前先把長邊縮到這個大小（避免大圖太慢；不做去雜訊，避免抹掉小痘痘）
MAX_SIDE = 1280

# --- 白平衡 ---
WB_GAIN_MIN = 0.6      # 單一通道增益下限，避免過度校正
WB_GAIN_MAX = 1.7      # 單一通道增益上限
WB_TRIM_LOW = 20       # 計算平均時排除過暗像素（0-255）
WB_TRIM_HIGH = 235     # 計算平均時排除過亮像素

# --- 品質檢查 ---
Q_MIN_FACE_WIDTH_PX = 200      # 臉寬（像素）低於此值解析度太低
Q_MIN_FACE_WIDTH_RATIO = 0.30  # 臉寬佔整張圖比例太小代表距離太遠
Q_BRIGHT_MIN = 70              # 臉部平均亮度（灰階）低於此值太暗
Q_BRIGHT_MAX = 215             # 高於此值太亮
Q_OVEREXPOSED_RATIO = 0.05     # 臉部像素 >=250 的比例超過此值視為過曝
Q_BLUR_MIN = 30.0              # 臉部 Laplacian 變異數（正規化後）低於此值視為模糊
Q_BLUR_REF_WIDTH = 256         # 計算模糊度前，臉部裁切統一縮放到的寬度
Q_YAW_RATIO_MIN = 0.75         # 鼻尖到兩側臉緣的距離比，偏離 1 太多代表側臉
Q_YAW_RATIO_MAX = 1.33

# --- 區域色彩統計 ---
STAT_MIN_PIXELS = 50           # 區域有效像素少於此值就不統計
STAT_DARK = 28                 # 排除過暗像素（例如眼睛遮罩、頭髮陰影）
STAT_BRIGHT = 250              # 排除過亮像素（反光、過曝）

# --- 病灶偵測 ---
# 單一偵測框佔整張照片面積超過此比例，視為無效（真正的痘痘只佔臉的一小塊）。
# 目前 best.pt 是用「裁切小圖、整張圖就是一顆病灶」的資料訓練的，
# 對整張臉會回傳一個幾乎覆蓋全圖的框，必須擋掉。
LESION_MAX_AREA_RATIO = 0.25

# --- 橋接方案：痘痘候選位置 ---
CAND_K = 2.0               # 門檻 = 中位數 + K * 標準差（越大越嚴格，候選越少）
CAND_RED_MIN = 4.0         # 「比周圍更紅」的最低門檻（Lab a* 單位）
CAND_DARK_MIN = 8.0        # 「比周圍更暗」的最低門檻（Lab L* 單位）
CAND_MIN_AREA_PX = 8       # 候選最小面積（像素）
CAND_MIN_SIZE_RATIO = 0.008  # 候選邊長下限 = 臉寬 * 此比例（平方後和上面取大者）
CAND_MAX_SIZE_RATIO = 0.10   # 候選邊長上限 = 臉寬 * 此比例
CAND_MAX = 60              # 最多保留幾個候選
CAND_CROP_PAD = 3.0        # 裁切邊長 = 候選邊長 * 此倍率（含周圍皮膚）
CAND_CROP_MIN = 48         # 裁切邊長下限（像素）
CAND_CLS_CONF = 0.25       # 分類信心低於此值，類別標為 Unclassified
CAND_MAX_ASPECT = 3.0           # 候選框長寬比上限
CAND_RED_MAX_SIDE = 0.14        # 紅點：框邊長上限（臉寬的比例）
CAND_RED_MIN_COMPACT = 0.35     # 紅點：面積/框面積 下限（越小越不規則）
CAND_RED_EDGE = 0.012           # 紅點：離排除區域/臉緣的最小距離（臉寬的比例）
CAND_DARK_MAX_SIDE = 0.05       # 暗點（黑頭）：框邊長上限，黑頭很小
CAND_DARK_MIN_COMPACT = 0.45
CAND_DARK_EDGE = 0.04           # 暗點離眼、嘴、鼻孔、臉緣要夠遠，避免把陰影當黑頭
