"""產生給人看的輸出圖。注意：OpenCV 內建字型不支援中文，圖上文字用英文。"""
import cv2
import numpy as np


def draw_points(img, points, radius=1):
    out = img.copy()
    for x, y in np.asarray(points).round().astype(int):
        cv2.circle(out, (int(x), int(y)), radius, (0, 255, 255), -1)
    return out


def apply_eye_mask(img, mask):
    out = img.copy()
    out[mask] = (20, 20, 20)
    return out


def side_by_side(left, right, left_title="before", right_title="after"):
    h = max(left.shape[0], right.shape[0])

    def pad(im):
        if im.shape[0] == h:
            return im
        return cv2.copyMakeBorder(im, 0, h - im.shape[0], 0, 0, cv2.BORDER_CONSTANT, value=(255, 255, 255))

    both = np.hstack([pad(left), pad(right)])
    cv2.putText(both, left_title, (10, 24), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 4, cv2.LINE_AA)
    cv2.putText(both, left_title, (10, 24), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 1, cv2.LINE_AA)
    x = left.shape[1] + 10
    cv2.putText(both, right_title, (x, 24), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 4, cv2.LINE_AA)
    cv2.putText(both, right_title, (x, 24), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 1, cv2.LINE_AA)
    return both


# ====================================================================
# 分區圖輸出：原圖 + 臟腑分區 + 異常圈起來 + 右側圖例（含中文）
# ====================================================================
import os

_FONT_CANDIDATES = [
    r"C:\Windows\Fonts\msjh.ttc", r"C:\Windows\Fonts\msjhbd.ttc",   # 微軟正黑體
    r"C:\Windows\Fonts\mingliu.ttc", r"C:\Windows\Fonts\simsun.ttc",
    "/System/Library/Fonts/PingFang.ttc",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
]


def find_cjk_font():
    for p in _FONT_CANDIDATES:
        if os.path.exists(p):
            return p
    return None


def _zone_color(i):
    # 固定的調色（HSV 色相均分），讓同一區域每次顏色一致
    hue = int((i * 47) % 180)
    c = cv2.cvtColor(np.uint8([[[hue, 150, 235]]]), cv2.COLOR_HSV2BGR)[0, 0]
    return tuple(int(v) for v in c)


def _smooth_mask_up(mask, s):
    """把低解析度的遮罩放大成平滑的高解析度遮罩（避免放大後邊界像階梯）。"""
    f = cv2.GaussianBlur(mask.astype(np.float32), (0, 0), 1.0)
    f = cv2.resize(f, None, fx=s, fy=s, interpolation=cv2.INTER_LINEAR)
    return (f > 0.5).astype(np.uint8)


def _draw_poly(img, pts, color, thickness, dashed, on=9, off=6):
    """畫封閉輪廓；dashed=True 時畫成虛線（沿輪廓每隔一段畫一段）。"""
    pts = pts.reshape(-1, 2).astype(np.float32)
    if len(pts) < 2:
        return
    if not dashed:
        cv2.polylines(img, [pts.round().astype(np.int32)], True, color, thickness, cv2.LINE_AA)
        return
    closed = np.vstack([pts, pts[:1]])
    seg = np.linalg.norm(np.diff(closed, axis=0), axis=1)
    total = float(seg.sum())
    if total < 1:
        return
    cum = np.concatenate([[0.0], np.cumsum(seg)])
    period = on + off
    for start in np.arange(0.0, total, period):
        end = min(start + on, total)
        ts = np.linspace(start, end, max(2, int((end - start) / 2) + 1))
        xs = np.interp(ts, cum, closed[:, 0]); ys = np.interp(ts, cum, closed[:, 1])
        cv2.polylines(img, [np.stack([xs, ys], 1).round().astype(np.int32)], False, color, thickness, cv2.LINE_AA)


def _place_labels(lm, zone_rows, scale):
    """為每個區域挑編號的位置：優先放在區域內離邊界最遠處；與其他編號重疊就換位置，
    實在放不下就放到旁邊並畫一條短線連回區域。回傳 {idx: (x, y, 需要連線的目標點或 None)}。"""
    items = []
    for r in zone_rows:
        m = (lm == r["idx"]).astype(np.uint8)
        n = int(m.sum())
        if n == 0:
            continue
        items.append((n, r["idx"], m))
    items.sort(key=lambda t: t[0])                      # 小區塊先挑位置
    placed, boxes = {}, []

    def box(x, y, text):
        w = 9 * len(text) + 6
        return (x - w // 2, y - 9, x + w // 2, y + 6)

    def free(b):
        return all(b[2] < o[0] or o[2] < b[0] or b[3] < o[1] or o[3] < b[1] for o in boxes)

    for n, idx, m in items:
        text = str(idx + 1)
        dist = cv2.distanceTransform(m, cv2.DIST_L2, 3)
        dmax = float(dist.max())
        ys, xs = np.where(dist >= max(1.0, 0.55 * dmax))
        if len(xs) == 0:                                # 很細的區塊：用所有像素
            ys, xs = np.where(m > 0)
        order = np.argsort(-dist[ys, xs])[::3][:80]
        cx, cy = int(xs.mean()), int(ys.mean())
        pick = None
        for k in order:
            x, y = int(xs[k]), int(ys[k])
            if free(box(x, y, text)):
                pick = (x, y, None)
                break
        if pick is None:
            gy, gx = np.where(m > 0)
            cx, cy = int(gx.mean()), int(gy.mean())
            for rad in (16, 24, 32, 42):
                for ang in range(0, 360, 30):
                    x = int(cx + rad * np.cos(np.radians(ang)))
                    y = int(cy + rad * np.sin(np.radians(ang)))
                    if free(box(x, y, text)):
                        pick = (x, y, (cx, cy))
                        break
                if pick:
                    break
        if pick is None:
            pick = (cx, cy, None)
        placed[idx] = [pick]
        boxes.append(box(pick[0], pick[1], text))
        # 區塊中間被別的區塊挖掉（例如 U 字形、環狀）時，兩邊各標一次，才看得出是同一區
        if pick[2] is None and len(xs) > 1:
            d1 = np.hypot(xs - pick[0], ys - pick[1])
            for k in order:
                x, y = int(xs[k]), int(ys[k])
                if np.hypot(x - pick[0], y - pick[1]) < 2.5 * max(dmax, 6):
                    continue
                mx, my = (x + pick[0]) // 2, (y + pick[1]) // 2
                if m[my, mx] == 0 and free(box(x, y, text)):       # 兩點連線中間不在區塊內 → 兩個分離的部分
                    placed[idx].append((x, y, None))
                    boxes.append(box(x, y, text))
                    break
    return placed


def render_zone_overview(img, zones, zone_rows, band_rows, lesions, eyes_mask=None,
                         target_height=1000, note=None, extra_lines=None, style="lines", show_bands=False):
    """回傳一張大圖：左邊是照片（分區 + 異常圈選），右邊是圖例表。

    zone_rows: [{'idx','name','lesions','rgb'(after) or None,'a','dashed'}]（依編號順序）
    style: "lines" = 不著色，只畫白色細實線的區塊邊界；"fill" = 半透明著色
    band_rows: [{'name','lesions'}]
    """
    from PIL import Image, ImageDraw, ImageFont

    h, w = img.shape[:2]
    s = max(1.0, target_height / h)
    base = cv2.resize(img, None, fx=s, fy=s, interpolation=cv2.INTER_CUBIC)
    if eyes_mask is not None:
        em = cv2.resize(eyes_mask.astype(np.uint8), None, fx=s, fy=s, interpolation=cv2.INTER_NEAREST) > 0
        base[em] = (20, 20, 20)

    if style == "fill":
        lm = cv2.resize(zones["label_map"].astype(np.int16), None, fx=s, fy=s, interpolation=cv2.INTER_NEAREST)
        overlay = base.copy()
        for i in range(int(lm.max()) + 1):
            overlay[lm == i] = _zone_color(i)
        out = cv2.addWeighted(base, 0.68, overlay, 0.32, 0)
        for name, m in zones["band_masks"].items():
            mm = cv2.resize(m.astype(np.uint8), None, fx=s, fy=s, interpolation=cv2.INTER_NEAREST)
            cnts, _ = cv2.findContours(mm, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            cv2.drawContours(out, cnts, -1, (255, 255, 255), 1, cv2.LINE_AA)
    else:
        out = base.copy()
        lm = cv2.resize(zones["label_map"].astype(np.int16), None, fx=s, fy=s, interpolation=cv2.INTER_NEAREST)
        dashed_idx = {r["idx"] for r in zone_rows if r.get("dashed")}
        order = sorted(range(len(zone_rows)), key=lambda i: i in dashed_idx, reverse=True)   # 先畫虛線，實線蓋在上面
        for i in order:
            m = zones["label_map"] == zone_rows[i]["idx"]
            if m.sum() < 8:
                continue
            up = _smooth_mask_up(m, s)
            cnts, _ = cv2.findContours(up, cv2.RETR_LIST, cv2.CHAIN_APPROX_NONE)
            for c in cnts:
                if len(c) < 12:
                    continue
                c = cv2.approxPolyDP(c, 1.2, True)
                dsh = False                                    # 一律實線
                _draw_poly(out, c, (255, 255, 255), 1, dsh)
        # 臉部外輪廓（白色細實線）
        face = np.any(list(zones["band_masks"].values()), axis=0)
        cnts, _ = cv2.findContours(_smooth_mask_up(face, s), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
        for c in cnts:
            _draw_poly(out, cv2.approxPolyDP(c, 1.5, True), (255, 255, 255), 1, False)

    # 橫帶標籤（預設不畫；橫帶的病灶統計仍保留在 JSON / CSV）
    for name, m in (zones["band_masks"].items() if show_bands else []):
        mm = cv2.resize(m.astype(np.uint8), None, fx=s, fy=s, interpolation=cv2.INTER_NEAREST)
        ys, xs = np.where(mm > 0)
        if len(xs):
            x0, yc = int(xs.min()), int(ys.mean())
            cv2.putText(out, name, (max(2, x0 - 34), yc), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 0, 0), 3, cv2.LINE_AA)
            cv2.putText(out, name, (max(2, x0 - 34), yc), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 1, cv2.LINE_AA)

    # 區域編號（避免互相重疊；放不下的放在旁邊並連一條短線）
    for idx, spots in _place_labels(lm, zone_rows, s).items():
        t = str(idx + 1)
        for (x, y, tgt) in spots:
            if tgt is not None:
                cv2.line(out, (x, y), tgt, (255, 255, 255), 1, cv2.LINE_AA)
            p = (x - 4 * len(t), y + 5)
            cv2.putText(out, t, p, cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 0), 3, cv2.LINE_AA)
            cv2.putText(out, t, p, cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 1, cv2.LINE_AA)

    # 異常圈起來（紅色圓圈，圍住偵測框）
    for d in lesions:
        x1, y1, x2, y2 = [v * s for v in d["box"]]
        c = (int((x1 + x2) / 2), int((y1 + y2) / 2))
        r = int(max(x2 - x1, y2 - y1) / 2 * 1.5) + 6
        cv2.circle(out, c, r, (255, 255, 255), 4, cv2.LINE_AA)
        cv2.circle(out, c, r, (0, 0, 255), 2, cv2.LINE_AA)

    if note:
        cv2.putText(out, note, (8, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 4, cv2.LINE_AA)
        cv2.putText(out, note, (8, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 215, 255), 1, cv2.LINE_AA)

    # ---------------- 圖例（PIL 才能畫中文）----------------
    font_path = find_cjk_font()
    row_h, legend_w = 24, 560
    n_rows = len(zone_rows) + (len(band_rows) + 2 if show_bands else 0) + 3 + len(extra_lines or [])
    legend_h = max(out.shape[0], n_rows * row_h + 20)
    canvas = Image.new("RGB", (out.shape[1] + legend_w, legend_h), (250, 250, 250))
    canvas.paste(Image.fromarray(cv2.cvtColor(out, cv2.COLOR_BGR2RGB)), (0, 0))
    dr = ImageDraw.Draw(canvas)
    f = ImageFont.truetype(font_path, 15) if font_path else ImageFont.load_default()
    fb = ImageFont.truetype(font_path, 16) if font_path else f
    x0 = out.shape[1] + 12
    y = 8
    head = ("#  區域                  病灶數   面色(校正後 RGB)" if font_path
            else "#  zone                  n   RGB(after WB)")
    dr.text((x0, y), head, fill=(0, 0, 0), font=fb)
    y += row_h
    for r in zone_rows:
        if style == "fill":
            col = _zone_color(r["idx"])
            dr.rectangle([x0, y + 3, x0 + 14, y + 17], fill=(col[2], col[1], col[0]))
        else:
            pass
        name = r["name"] if font_path else r["id"]
        dr.text((x0 + 20, y), f"{r['idx'] + 1:>2}  {name}", fill=(0, 0, 0), font=f)
        n = r["lesions"]
        dr.text((x0 + 250, y), str(n), fill=(200, 0, 0) if n else (150, 150, 150), font=f)
        if r["rgb"]:
            R, G, B = [int(round(v)) for v in r["rgb"]]
            dr.rectangle([x0 + 300, y + 3, x0 + 318, y + 17], fill=(R, G, B), outline=(120, 120, 120))
            dr.text((x0 + 326, y), f"{R},{G},{B}", fill=(60, 60, 60), font=f)
        else:
            dr.text((x0 + 300, y), "-", fill=(150, 150, 150), font=f)
        y += row_h
    if show_bands:
        y += 8
        dr.text((x0, y), "橫帶（C1~C6）病灶數" if font_path else "bands: lesions", fill=(0, 0, 0), font=fb)
        y += row_h
        for b in band_rows:
            dr.text((x0 + 20, y), f"{b['name']}", fill=(0, 0, 0), font=f)
            dr.text((x0 + 250, y), str(b["lesions"]), fill=(200, 0, 0) if b["lesions"] else (150, 150, 150), font=f)
            y += row_h
        y += 8
    for line in extra_lines or []:
        dr.text((x0, y), line, fill=(0, 0, 0), font=f)
        y += row_h
    return cv2.cvtColor(np.array(canvas), cv2.COLOR_RGB2BGR)
