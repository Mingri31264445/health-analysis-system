"""依「面診分區圖」(C1~C7 橫帶 + 各臟腑小區塊)在照片上切分區域。

【做法】
圖上的每個位置，都先在「分區圖的座標」裡量好(見下方 ZONE)，
再用每張照片自己的臉部關鍵點，把它對應到那張照片上：
  - 水平:以雙眼外眼角距離 D 為單位，u = (x - 中線) / D。臉大一點、轉一點、歪一點都會跟著動。
  - 垂直:分區圖的橫線(C1~C6 的分界)對應到臉上的關鍵點列（髮際、眉上緣、眼下、鼻底、嘴線、下巴），
    每一帶內用線性內插。

【左右】以「畫面」的左右為準（跟分區圖一樣，從看圖的人角度）。
        _L = 畫面左側，_R = 畫面右側。注意這和之前 regions.py 的「受檢者左右」不同。

【重要】ZONES 的座標是從分區圖用眼睛量的近似值，不是醫學定義。
        位置要請指導老師或教授確認，確認後只要改這個檔案的數字即可。
"""
import cv2
import numpy as np

from .regions import FACE_OVAL, face_oval_polygon, polygon_mask

# 分區圖座標
# 分區圖（放大 2.2 倍的裁切圖）上量得的數值
CHART_MID_X = 630.0     # 臉的中線
CHART_D = 580.0         # 雙眼外眼角距離（左外眼角 340 → 右外眼角 920）
# 橫線位置：C1 頂 / C1|C2 / C2|C3 / C3|C4 / C4|C5 / C5|C6 / C6 底
CHART_ROWS = [40.0, 230.0, 390.0, 520.0, 595.0, 705.0, 980.0]
BAND_NAMES = ["C1", "C2", "C3", "C4", "C5", "C6"]
BAND_ZH = {"C1": "C1 頭部", "C2": "C2 眼睛", "C3": "C3 鼻腔上段", "C4": "C4 鼻腔下段",
           "C5": "C5 上唇", "C6": "C6 下唇/下巴"}
# 分區圖的 C3/C4 分界線不明顯（圖上沒畫線），這裡取在「肝」與「胃脾胃」之間，需確認


def _mirror(shape):
    """以中線左右翻轉一個形狀。"""
    kind, *v = shape
    if kind == "rect":
        x1, y1, x2, y2 = v
        return ("rect", 2 * CHART_MID_X - x2, y1, 2 * CHART_MID_X - x1, y2)
    cx, cy, rx, ry = v
    return ("ellipse", 2 * CHART_MID_X - cx, cy, rx, ry)


def _build_zone_table():
    """回傳 [(id, 臟腑名, 側別, 形狀)]；順序即優先順序（前面的先佔用像素）。"""
    Z = []

    def add(zid, organ, side, shape):
        Z.append((zid, organ, side, shape))

    def pair(zid, organ, left_shape):
        add(f"{zid}_L", organ, "L", left_shape)
        add(f"{zid}_R", organ, "R", _mirror(left_shape))

    # 1. 小而特殊的點/線（先處理，避免被大區塊吃掉)
    pair("breast", "乳房(胸)", ("ellipse", 545, 365, 30, 30))      # 內眼角綠點
    pair("duodenum_nose", "十二指腸", ("rect", 505, 515, 535, 570))  # 鼻翼綠線
    add("uterus", "子宮、攝護腺", "M", ("ellipse", 628, 638, 26, 24))  # 人中下端紅圈
    add("bladder", "膀胱", "M", ("ellipse", 618, 680, 16, 14))        # 唇上小紅圈
    add("asc_colon", "升結腸", "L", ("rect", 450, 596, 490, 700))     # 橘色方框左邊
    add("trans_colon", "橫結腸", "M", ("rect", 490, 590, 750, 614))   # 方框上邊
    add("desc_colon", "降結腸", "R", ("rect", 750, 606, 790, 706))    # 方框右邊
    add("duodenum_chin", "十二指腸", "M", ("rect", 545, 763, 695, 792))  # 下巴橘色橫線
    add("spleen_lip", "脾", "M", ("rect", 500, 682, 760, 705))        # 上唇
    add("stomach_lip", "胃", "M", ("rect", 500, 705, 760, 752))       # 下唇

    # 2. 中線一列（由上到下）
    cx1, cx2 = 585, 675
    add("head_face", "首面", "M", ("rect", cx1, 40, cx2, 135))
    add("throat", "咽喉", "M", ("rect", cx1, 135, cx2, 212))
    add("lung", "肺", "M", ("rect", cx1, 212, cx2, 262))
    add("trachea", "氣管", "M", ("rect", cx1, 262, cx2, 318))
    add("heart", "心", "M", ("rect", cx1, 318, cx2, 395))
    add("liver", "肝", "M", ("rect", cx1, 395, cx2, 520))
    add("spleen_nose", "脾", "M", ("rect", cx1, 520, cx2, 597))

    # 3. 左右成對的區塊（左邊量好，右邊自動鏡射)
    pair("gallbladder", "膽", ("rect", 510, 395, 585, 520))
    pair("stomach_nose", "胃", ("rect", 510, 520, 585, 597))
    pair("kidney_eye", "腎", ("rect", 350, 250, 540, 325))
    pair("heart_kidney", "心腎之交", ("rect", 350, 392, 505, 440))
    pair("ovary", "卵巢", ("rect", 235, 420, 345, 500))
    pair("small_intestine", "小腸", ("rect", 355, 520, 505, 597))
    pair("pancreas", "胰", ("rect", 330, 597, 450, 642))
    pair("large_intestine", "大腸", ("rect", 345, 642, 450, 690))
    pair("kidney_lip", "腎", ("rect", 330, 688, 450, 730))
    return Z


ZONE_TABLE = _build_zone_table()

#  補充分區（微體檢「臉部切分詳細說明」表）
# 分區圖只標了臉的中央，這一批依另一份文件（微体检 2.6.2 面诊舌诊开发，44 塊分區）補滿其餘的臉。
# 優先順序在分區圖那 39 區之後：分區圖已佔用的像素不會被搶走，只填補還沒被涵蓋的地方。
# 位置不是用分區圖座標，而是直接用這張臉的關鍵點定義（見 _extra_masks）。
# (id, 臟腑, 側別, 來源文件的部位名稱)
EXTRA_ZONES = [
    ("eyelid_up_L", "脾", "L", "上眼瞼"), ("eyelid_up_R", "脾", "R", "上眼瞼"),
    ("eyelid_low_L", "脾", "L", "下眼瞼"), ("eyelid_low_R", "脾", "R", "下眼瞼"),
    ("forehead", "心、情志", "M", "額頭"),
    ("temple_L", "—", "L", "太陽穴"), ("temple_R", "—", "R", "太陽穴"),
    ("eye_socket_L", "胸", "L", "眼窩"), ("eye_socket_R", "胸", "R", "眼窩"),
    ("nose_side_upper_L", "小腸", "L", "鼻端旁上方"), ("nose_side_upper_R", "小腸", "R", "鼻端旁上方"),
    ("cheek_under_L", "大腸", "L", "顴下"), ("cheek_under_R", "大腸", "R", "顴下"),
    ("cheek_side_L", "腎", "L", "顴下兩側"), ("cheek_side_R", "腎", "R", "顴下兩側"),
    ("philtrum", "膀胱、胞宮", "M", "人中"),
    ("chin", "腎、疲勞酸痛", "M", "下巴"),
    ("jaw_L", "淋巴", "L", "腮"), ("jaw_R", "淋巴", "R", "腮"),
]
# 以圖為主、文件為輔：文件裡「分區圖已經有」的位置（眉間、鼻根、鼻梁、鼻頭、鼻翼、人中、鼻梁側）不再重複加入，
# 只補分區圖沒有涵蓋的部位。
EXTRA_LABEL = {z[0]: z[3] for z in EXTRA_ZONES}

ZONE_IDS = [z[0] for z in ZONE_TABLE] + [z[0] for z in EXTRA_ZONES]
ZONE_INFO = {zid: {"organ": organ, "side": side, "source": "chart"} for zid, organ, side, _ in ZONE_TABLE}
ZONE_INFO.update({zid: {"organ": organ, "side": side, "source": "doc44"} for zid, organ, side, _ in EXTRA_ZONES})


def zone_display_name(zid):
    info = ZONE_INFO[zid]
    side = {"L": "(畫面左)", "R": "(畫面右)", "M": ""}[info["side"]]
    if zid in EXTRA_LABEL:                                # 補充分區：顯示部位名稱，臟腑放後面
        organ = info["organ"]
        return f"{EXTRA_LABEL[zid]}{side}" + (f"·{organ}" if organ != "—" else "")
    return f"{info['organ']}{side}"


#  臉部座標系
class FaceFrame:
    """用關鍵點建立這張臉自己的座標系：原點、水平軸、垂直軸、尺度 D、各橫線的位置。"""

    def __init__(self, points):
        P = np.asarray(points, dtype=np.float64)
        self.origin = P[168].copy()                      # 兩眼之間（鼻根）
        d = P[263] - P[33]                               # 受檢者右眼外角 → 左眼外角（畫面左 → 畫面右）
        self.D = float(np.linalg.norm(d))
        self.ex = d / self.D                             # 水平軸（朝畫面右）
        self.ey = np.array([-self.ex[1], self.ex[0]])    # 垂直軸（朝下）

        def w(idx):
            idx = np.atleast_1d(idx)
            return float(np.mean([(P[i] - self.origin) @ self.ey for i in idx]))

        r0 = w(10)                                        # 臉部輪廓最上緣
        r1 = w([70, 63, 105, 66, 107, 336, 296, 334, 293, 300])   # 眉毛上緣
        r2 = w([145, 153, 374, 380]) + 0.03 * self.D      # 下眼瞼再往下一點
        r4 = w(2)                                         # 鼻底
        r5 = w([13, 14])                                  # 嘴唇交界線
        r6 = w(152)                                       # 下巴底
        # C3|C4 分界：照分區圖比例落在 r2 與 r4 之間
        frac = (CHART_ROWS[3] - CHART_ROWS[2]) / (CHART_ROWS[4] - CHART_ROWS[2])
        r3 = r2 + frac * (r4 - r2)
        self.rows = np.array([r0, r1, r2, r3, r4, r5, r6])

        # 補充分區用的額外基準（單位：D 或與 rows 相同的垂直座標）
        self.P = P
        self.brow_up = r1
        self.brow_low = w([46, 53, 52, 65, 55, 276, 283, 282, 295, 285])   # 眉毛下緣
        self.eye_low = w([145, 153, 374, 380])                              # 下眼緣（未加量）
        self.nose_base = r4
        self.nose_mid = (self.eye_low + r4) / 2                             # 文件定義的「鼻中線」
        self.lip_top = w(0)                                                 # 上唇上緣
        self.lip_bot = w(17)                                                # 下唇下緣
        self.top = r0

        # 臉的「中線」：不是一條直線，而是通過鼻根、鼻尖、人中、嘴唇中心、下巴的折線
        # 臉稍微轉動時，鼻根（原點）和嘴巴不在同一條垂直線上，直接用原點當中線會讓左右不對稱。
        ids = [10, 168, 6, 4, 2, 0, 13, 14, 17, 152]
        rel = P[ids] - self.origin
        ws, us = rel @ self.ey, (rel @ self.ex) / self.D
        o = np.argsort(ws)
        self._mid_w, self._mid_u = ws[o], us[o]

    def mid_u(self, w_px):
        """臉中線在垂直位置 w_px（像素）處的水平位置（單位 D）。"""
        return np.interp(w_px, self._mid_w, self._mid_u)

    def u_of(self, idx):
        """關鍵點相對臉中線的水平位置（單位 D，畫面右為正）。"""
        rel = self.P[idx] - self.origin
        return float(rel @ self.ex) / self.D - float(self.mid_u(rel @ self.ey))

    def chart_to_image(self, x, y):
        u = (x - CHART_MID_X) / CHART_D
        w = np.interp(y, CHART_ROWS, self.rows)
        p = self.origin + u * self.D * self.ex + w * self.ey
        return p


# 器官輪廓（關鍵點編號）
LIP_UP = [61, 185, 40, 39, 37, 0, 267, 269, 270, 409, 291, 308, 415, 310, 311, 312, 13, 82, 81, 80, 191, 78]
LIP_LOW = [61, 146, 91, 181, 84, 17, 314, 405, 321, 375, 291, 308, 324, 318, 402, 317, 14, 87, 178, 88, 95, 78]
MOUTH_INNER = [78, 191, 80, 81, 82, 13, 312, 311, 310, 415, 308, 324, 318, 402, 317, 14, 87, 178, 88, 95]
NOSE_LOWER = [4, 45, 220, 115, 48, 64, 98, 97, 2, 326, 327, 294, 278, 344, 440, 275]   # 鼻頭+鼻翼的輪廓
# 這幾區直接用器官輪廓，不用矩形：嘴唇（上/下）、鼻（鼻頭 + 左右鼻翼，水平位置仍用分區圖的範圍切）
ORGAN_SHAPED = {"spleen_lip": LIP_UP, "stomach_lip": LIP_LOW,
                "spleen_nose": NOSE_LOWER, "stomach_nose_L": NOSE_LOWER, "stomach_nose_R": NOSE_LOWER}


def _frame_w(frame, idx):
    idx = np.atleast_1d(idx)
    return np.array([(frame.P[i] - frame.origin) @ frame.ey for i in idx])


def _curve(frame, ids, offset=0.0, pts=None):
    """通過一串關鍵點的曲線 w(u)；兩端往外延伸時保持水平。"""
    if pts is None:
        us = np.array([frame.u_of(i) for i in ids])
        ws = _frame_w(frame, ids) + offset
    else:
        us, ws = pts
    o = np.argsort(us)
    us, ws = us[o], ws[o]
    return lambda u: np.interp(u, us, ws)


def _row_curves(frame, u, oval_uw):
    """每一條「橫線」在這張臉上不是直線，而是順著眉毛、下眼瞼、鼻底、嘴線、下頷輪廓彎曲。

    回傳 dict：每個值是與 u 同形狀的陣列（每個像素所在水平位置上，這條線的垂直座標）。
    """
    D = frame.D
    c = {}
    c["top"] = np.full(u.shape, frame.top)
    c["brow_up"] = _curve(frame, [70, 63, 105, 66, 107, 336, 296, 334, 293, 300])(u)
    c["brow_low"] = _curve(frame, [46, 53, 52, 65, 55, 276, 283, 282, 295, 285])(u)
    lid = [33, 7, 163, 144, 145, 153, 154, 155, 133, 362, 382, 381, 380, 374, 373, 390, 249, 263]
    c["eye_low_raw"] = _curve(frame, lid)(u)
    c["eye_low"] = c["eye_low_raw"] + 0.03 * D
    c["nose_base"] = _curve(frame, [129, 98, 2, 327, 358])(u)
    mid_u = (frame.u_of(13) + frame.u_of(14)) / 2
    mid_w = float(_frame_w(frame, [13, 14]).mean())
    c["lip_line"] = _curve(frame, None, pts=(np.array([frame.u_of(61), mid_u, frame.u_of(291)]),
                                              np.array([_frame_w(frame, 61)[0], mid_w, _frame_w(frame, 291)[0]])))(u)
    c["lip_top"] = _curve(frame, [61, 0, 291])(u)
    c["lip_bot"] = _curve(frame, [61, 17, 291])(u)
    # 下頷輪廓：臉部輪廓下半部
    ou, ow = oval_uw
    low = ow > float(_frame_w(frame, [13, 14]).mean()) + 0.05 * D
    jaw = _curve(frame, None, pts=(ou[low], ow[low]))(u) if low.sum() >= 3 else np.full(u.shape, frame.rows[6])
    # 依分區圖的比例，C3|C4 分界落在下眼緣與鼻底之間
    frac = (CHART_ROWS[3] - CHART_ROWS[2]) / (CHART_ROWS[4] - CHART_ROWS[2])
    rows = [c["top"], c["brow_up"], c["eye_low"], None, c["nose_base"], c["lip_line"], jaw]
    gap = 0.02 * D
    for k in (1, 2):
        rows[k] = np.maximum(rows[k], rows[k - 1] + gap)
    rows[4] = np.maximum(rows[4], rows[2] + gap * 3)
    rows[3] = rows[2] + frac * (rows[4] - rows[2])
    rows[5] = np.maximum(rows[5], rows[4] + gap)
    rows[6] = np.maximum(rows[6], rows[5] + gap)
    c["rows"] = rows
    c["jaw"] = rows[6]
    return c


def _edge_profile(u, w, oval, D, bin_w=0.02):
    """臉部輪廓在每個高度的左右邊界（單位 D，距中線）。"""
    ou, ow = u[oval][::7] / 1.0, w[oval][::7] / D
    lo, hi = ow.min(), ow.max()
    nb = max(8, int((hi - lo) / bin_w))
    edges = np.linspace(lo, hi, nb + 1)
    idx = np.clip(np.digitize(ow, edges) - 1, 0, nb - 1)
    eR = np.full(nb, np.nan); eL = np.full(nb, np.nan)
    for b in range(nb):
        sel = idx == b
        if sel.any():
            eR[b] = ou[sel].max(); eL[b] = -ou[sel].min()
    cen = (edges[:-1] + edges[1:]) / 2
    ok = ~np.isnan(eR)
    eR = np.interp(cen, cen[ok], eR[ok]); eL = np.interp(cen, cen[ok], eL[ok])
    k = np.ones(5) / 5
    eR = np.convolve(np.pad(eR, 2, mode="edge"), k, mode="valid")
    eL = np.convolve(np.pad(eL, 2, mode="edge"), k, mode="valid")
    return cen, eL, eR


CHART_EDGE = 0.70        # 分區圖上臉的外緣（單位 D，距中線）；外側的區塊會被拉伸/壓縮到每個人自己的臉緣
CHART_INNER = 0.35       # 中線附近（器官位置）不拉伸，只有更外側才依臉寬調整


def _warp_to_chart(frame, shape, oval):
    """每個像素 → 分區圖座標 (cx, cy)。垂直方向順著五官曲線，水平方向外側依臉部輪廓縮放。"""
    h, w_ = shape[:2]
    yy, xx = np.mgrid[0:h, 0:w_].astype(np.float32)
    dx, dy = xx - frame.origin[0], yy - frame.origin[1]
    w = dx * frame.ey[0] + dy * frame.ey[1]
    u = (dx * frame.ex[0] + dy * frame.ex[1]) / frame.D - frame.mid_u(w)      # 相對臉中線
    D = frame.D
    cen, eL, eR = _edge_profile(u, w, oval, D)
    wn = w / D
    edge = np.where(u >= 0, np.interp(wn, cen, eR), np.interp(wn, cen, eL))
    edge = np.maximum(edge, CHART_INNER + 0.08)
    au = np.abs(u)
    uc = np.where(au <= CHART_INNER, u,
                  np.sign(u) * (CHART_INNER + (au - CHART_INNER) * (CHART_EDGE - CHART_INNER) / (edge - CHART_INNER)))
    cx = CHART_MID_X + uc * CHART_D

    # 下頷曲線用臉部輪廓的關鍵點（不是區域內的像素）
    rel = frame.P[FACE_OVAL] - frame.origin
    ow = rel @ frame.ey
    ou = (rel @ frame.ex) / D - frame.mid_u(ow)
    curves = _row_curves(frame, u, (ou, ow))
    R = curves["rows"]
    cy = np.full((h, w_), -1e4, dtype=np.float32)
    for k in range(6):
        m = (w >= R[k]) & (w < R[k + 1])
        t = (w - R[k]) / (R[k + 1] - R[k])
        cy[m] = (CHART_ROWS[k] + t * (CHART_ROWS[k + 1] - CHART_ROWS[k]))[m]
    cy[w >= R[6]] = 1e4
    return cx, cy, u, w, curves


# 補充分區（以關鍵點定義）
# 每一側用自己的關鍵點：畫面左 = 受檢者右眼；畫面右 = 受檢者左眼
_SIDE_LM = {
    "L": dict(sgn=-1, outer=33, inner=133, iris=468, wing=129, corner=61, brow_in=107,
              up=[246, 161, 160, 159, 158, 157, 173], low=[7, 163, 144, 145, 153, 154, 155],
              c_out=33, c_in=133),
    "R": dict(sgn=+1, outer=263, inner=362, iris=473, wing=358, corner=291, brow_in=336,
              up=[466, 388, 387, 386, 385, 384, 398], low=[249, 390, 373, 374, 380, 381, 382],
              c_out=263, c_in=362),
}


def _lid_polygon(frame, side, kind, thick):
    """眼瞼：眼睛輪廓往上（或往下）推 thick*D 所圍成的帶狀區。"""
    c = _SIDE_LM[side]
    ids = [c["c_out"]] + (c["up"] if kind == "up" else c["low"]) + [c["c_in"]]
    pts = frame.P[ids]
    shift = (-1 if kind == "up" else 1) * thick * frame.D * frame.ey
    poly = np.vstack([pts, (pts + shift)[::-1]])
    return poly.round().astype(np.int32)


def _extra_masks(frame, shape, oval, u, w, curves):
    """回傳 {zone_id: bool mask}（尚未互斥；順序之後再分配）。邊界線是彎曲的（見 _row_curves）。"""
    h, w_ = shape[:2]
    D = frame.D
    ub = np.mean([abs(frame.u_of(107)), abs(frame.u_of(336))])  # 兩眉內端
    r1 = curves["brow_up"]
    el = curves["eye_low_raw"]
    r4 = curves["nose_base"]
    rm = (el + r4) / 2                                           # 文件定義的「鼻中線」
    lt, lb = curves["lip_top"], curves["lip_bot"]
    M = {}

    def side_params(side):
        c = _SIDE_LM[side]
        uu = c["sgn"] * u                                         # 往臉外側為正
        return (uu, abs(frame.u_of(c["outer"])), abs(frame.u_of(c["inner"])),
                abs(frame.u_of(c["iris"])), abs(frame.u_of(c["wing"])))

    u_wing = (abs(frame.u_of(129)) + abs(frame.u_of(358))) / 2
    au = np.abs(u)
    for side in "LR":
        for kind, thick in (("up", 0.10), ("low", 0.07)):
            m = np.zeros((h, w_), np.uint8)
            cv2.fillPoly(m, [_lid_polygon(frame, side, kind, thick)], 1)
            M[f"eyelid_{kind}_{side}"] = m.astype(bool)
    M["forehead"] = w < r1
    for side in "LR":
        uu, u_out, u_in, u_pup, u_w = side_params(side)
        M[f"temple_{side}"] = (uu > u_out) & (w >= r1) & (w < el)
        M[f"eye_socket_{side}"] = (uu > 0) & (uu <= u_out) & (w >= r1) & (w < el + 0.03 * D)
        M[f"nose_side_upper_{side}"] = (uu > 0) & (uu <= u_out) & (w >= el) & (w < rm)
        # 顴下：鼻中線以下、鼻唇溝 45 度斜線以上，到外眼角垂直線
        M[f"cheek_under_{side}"] = ((uu > 0.5 * u_w) & (uu <= u_out) & (w >= rm) & (w < r4)      # 鼻底線以上
                                    & (w <= r4 - (uu - u_w) * D))
        M[f"cheek_side_{side}"] = (uu > u_out) & (w >= el) & (w < r4)
        M[f"jaw_{side}"] = (uu > 0) & (w >= r4)
    M["philtrum"] = (au <= 0.8 * u_wing) & (w >= r4) & (w < lt)      # 鼻底到上唇之間（分區圖只在這裡標了兩個小圈）
    M["chin"] = w >= lb
    return {zid: m & oval for zid, m in M.items()}


def _poly_from_ids(frame, ids, shape):
    m = np.zeros(shape[:2], np.uint8)
    cv2.fillPoly(m, [frame.P[ids].round().astype(np.int32)], 1)
    return m.astype(bool)


def _smooth_labels(label_map, sigma):
    """把區塊邊界磨圓：每個像素改成「附近最多的區塊」。空白與器官孔洞保持不動。"""
    labeled = label_map >= 0
    best = np.full(label_map.shape, -1.0, np.float32)
    arg = np.full(label_map.shape, -1, np.int16)
    for l in np.unique(label_map[labeled]):
        sc = cv2.GaussianBlur((label_map == l).astype(np.float32), (0, 0), sigma)
        upd = sc > best
        best[upd] = sc[upd]
        arg[upd] = l
    out = np.where(labeled, arg, -1).astype(np.int16)
    # 小而重要的區塊（例如膀胱）不能被磨掉：縮到原本 40% 以下就還原
    for l in np.unique(label_map[labeled]):
        before = label_map == l
        if (out == l).sum() < 0.4 * before.sum():
            out[before] = l
    return out


def _shape_mask(shp, cx, cy):
    kind, *v = shp
    if kind == "rect":
        x1, y1, x2, y2 = v
        return (cx >= x1) & (cx < x2) & (cy >= y1) & (cy < y2)
    ccx, ccy, rx, ry = v
    return ((cx - ccx) / rx) ** 2 + ((cy - ccy) / ry) ** 2 <= 1.0


# 對外介面
SMOOTH_SIGMA = 0.030     # 區塊邊界磨圓程度（單位：眼距 D）


def build_zones(points, shape, smooth=True, sigma=None):
    """依關鍵點建立所有區域（形狀順著這張臉的五官與輪廓）。

    作法：把每個像素換算成「分區圖座標」(cx, cy)，再判斷落在分區圖的哪個區塊——
      垂直方向的橫線順著眉毛、下眼瞼、鼻底、嘴線、下頷輪廓彎曲；
      水平方向在中線附近維持原比例，外側依這張臉的臉寬縮放；
      嘴唇用嘴唇輪廓；眼睛、口腔內部不屬於任何區塊（空洞）；最後把區塊邊界磨圓。

    回傳 dict:
      polygons   {zone_id: 輪廓}
      label_map  (H,W) int16;每個像素屬於哪個區域（索引對應 ZONE_IDS)，-1 = 無
      masks      {zone_id: bool mask}（區域彼此不重疊，且限制在臉部輪廓內）
      band_masks {C1..C6: bool mask}（彎曲的橫帶）
      band_of    {zone_id: 所屬橫帶}
    """
    from .regions import eye_contour_mask

    h, w_ = shape[:2]
    frame = FaceFrame(points)
    oval = polygon_mask(face_oval_polygon(points), shape)
    cx, cy, u, w, curves = _warp_to_chart(frame, shape, oval)

    holes = eye_contour_mask(points, shape, margin=0.04) | _poly_from_ids(frame, MOUTH_INNER, shape)
    label_map = np.full((h, w_), -1, dtype=np.int16)
    free = oval & ~holes

    chart_ids = [z[0] for z in ZONE_TABLE]
    order = chart_ids                                    # 沿用分區圖的優先順序（小點、線先佔位）
    table = {z[0]: z for z in ZONE_TABLE}
    for zid in order:
        if zid in ORGAN_SHAPED:
            m = _poly_from_ids(frame, ORGAN_SHAPED[zid], shape)
            if zid.endswith("_nose") or "_nose_" in zid:
                # 鼻：輪廓（鼻頭、鼻翼）再加上分區圖該區的矩形（輪廓上方到分區圖該區上緣之間的鼻梁部分），
                # 兩者聯集後，水平方向用分區圖該區的範圍切
                x1, y1, x2, y2 = table[zid][3][1:]
                m = (m | _shape_mask(table[zid][3], cx, cy)) & (cx >= x1) & (cx < x2)
        else:
            m = _shape_mask(table[zid][3], cx, cy)
        label_map[m & free & (label_map < 0)] = ZONE_IDS.index(zid)

    extra = _extra_masks(frame, shape, oval, u, w, curves)
    ex_order = [z[0] for z in EXTRA_ZONES]
    ex_order = [z for z in ex_order if z not in ("chin", "jaw_L", "jaw_R")] + ["chin", "jaw_L", "jaw_R"]
    for zid in ex_order:
        label_map[extra[zid] & free & (label_map < 0)] = ZONE_IDS.index(zid)

    # 最後仍沒有歸屬的縫隙（區塊之間的狹縫、斜線切出來的三角形）：併入最近的區塊，不留下沒有編號的空白
    gap = oval & ~holes & (label_map < 0)
    if gap.any():
        src = np.where(gap | holes | ~oval, 255, 0).astype(np.uint8)
        _, lab = cv2.distanceTransformWithLabels(src, cv2.DIST_L2, 3, labelType=cv2.DIST_LABEL_PIXEL)
        zero_vals = label_map.reshape(-1)[np.flatnonzero(src.reshape(-1) == 0)]
        filled = zero_vals[np.clip(lab - 1, 0, len(zero_vals) - 1)]
        label_map = np.where(gap, filled, label_map).astype(np.int16)

    if smooth:
        label_map = _smooth_labels(label_map, max(1.0, (SMOOTH_SIGMA if sigma is None else sigma) * frame.D))
    masks = {zid: label_map == i for i, zid in enumerate(ZONE_IDS)}

    polygons = {}
    for zid, m in masks.items():
        cnts, _ = cv2.findContours(m.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        polygons[zid] = max(cnts, key=cv2.contourArea).reshape(-1, 2) if cnts else np.zeros((0, 2), np.int32)

    # 橫帶（彎曲）：依分區圖座標的 cy 切
    band_masks = {}
    for k, name in enumerate(BAND_NAMES):
        band_masks[name] = oval & (cy >= CHART_ROWS[k]) & (cy < CHART_ROWS[k + 1])

    band_of = {}
    for zid in ZONE_IDS:
        m = masks[zid]
        if zid in table and zid not in ORGAN_SHAPED:
            shp = table[zid][3]
            cyc = (shp[2] + shp[4]) / 2 if shp[0] == "rect" else shp[2]
        elif m.any():
            cyc = float(np.median(cy[m]))
        else:
            cyc = CHART_ROWS[0]
        if zid in ORGAN_SHAPED and m.any():
            cyc = float(np.median(cy[m]))
        k = int(np.clip(np.searchsorted(CHART_ROWS, cyc, side="right") - 1, 0, len(BAND_NAMES) - 1))
        band_of[zid] = BAND_NAMES[k]

    return {"polygons": polygons, "label_map": label_map, "masks": masks,
            "band_masks": band_masks, "band_of": band_of, "frame": frame}


def assign_zone(box_xyxy, zones):
    """偵測框的中心點落在哪個區域；不在任何區域回傳 'none'。"""
    lm = zones["label_map"]
    h, w = lm.shape
    cx = int(np.clip(round((box_xyxy[0] + box_xyxy[2]) / 2), 0, w - 1))
    cy = int(np.clip(round((box_xyxy[1] + box_xyxy[3]) / 2), 0, h - 1))
    i = int(lm[cy, cx])
    return ZONE_IDS[i] if i >= 0 else "none"


def assign_band(box_xyxy, zones):
    """偵測框中心點落在哪一個橫帶(C1~C6);不在臉內回傳 'none'。"""
    cx = int(round((box_xyxy[0] + box_xyxy[2]) / 2))
    cy = int(round((box_xyxy[1] + box_xyxy[3]) / 2))
    for name, m in zones["band_masks"].items():
        h, w = m.shape
        if 0 <= cy < h and 0 <= cx < w and m[cy, cx]:
            return name
    return "none"
