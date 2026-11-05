"""
經絡儀 PDF 解析器
從經絡儀報告 PDF 擷取數值
"""

import pdfplumber
import re
import sys

MERIDIANS = ['肺經','心包','心經','小腸','三焦','大腸','脾經','肝經','腎經','膀胱','膽經','胃經']

def _parse_summary(text: str) -> dict:
    """擷取整合分析摘要; PDF 沒有這一區時回傳空 dict"""
    summary = {}

    m = re.search(r'能量組成\(E\.C\.I\.\):\s*([\d.]+)', text)
    if m:
        summary['eci'] = float(m.group(1))

    m = re.search(r'身體能量:\s*([\d.]+)\s*\(\s*([\d.]+)\s*-\s*([\d.]+)\s*\)\s*(.+)', text)
    if m:
        summary['body_energy'] = {
            'value': float(m.group(1)),
            'range': [float(m.group(2)), float(m.group(3))],
            'summary': m.group(4).strip(),
        }

    # (key, 標題, 分子標籤, 分母標籤, 分子鍵, 分母鍵)
    ratio_items = [
        ('mental_ratio', '精神狀態比值', '上', '下', 'upper', 'lower'),
        ('bilateral', '左右肌骨系統', '左', '右', 'left', 'right'),
        ('metabolism', '新陳代謝功能', '陰', '陽', 'yin', 'yang'),
        ('autonomic', '自律神經平衡度', '高', '低', 'high', 'low'),
    ]
    for key, title, a, b, a_key, b_key in ratio_items:
        pattern = (
            rf'{title}:\s*{a}\s*([\d.]+)\s*/\s*{b}\s*([\d.]+)\s*=\s*([\d.]+)'
            r'\s*\(\s*([\d.]+)\s*-\s*([\d.]+)\s*\)\s*(.+)'
        )
        m = re.search(pattern, text)
        if m:
            summary[key] = {
                a_key: float(m.group(1)), b_key: float(m.group(2)),
                'ratio': float(m.group(3)),
                'range': [float(m.group(4)), float(m.group(5))],
                'summary': m.group(6).strip(),
            }
    return summary

def _parse_thresholds(lines: list[str]) -> dict:
    """從『正常 注意 警告』那行之後，連續抓純數字的行"""
    start = next(i for i, l in enumerate(lines) if '正常' in l and '警告' in l)
    values = []
    for l in lines[start + 1:]:
        if re.fullmatch(r'\d+(?:\.\d+)?', l.strip()):
            values.append(float(l))
        else:
            break

    if len(values) == 5:
        return dict(zip(['過高值', '高值', '均值', '低值', '過低值'], values))
    if len(values) == 3:  # 紅色警告線超出圖表範圍時，只會畫高/均/低
        return {'過高值': None, '高值': values[0], '均值': values[1],
                '低值': values[2], '過低值': None}
    raise ValueError(f'閾值數量異常：{values}')

def parse_meridian_pdf(pdf_path: str) -> dict:
    with pdfplumber.open(pdf_path) as pdf:
        page_texts = [(p.extract_text() or '') for p in pdf.pages]
    lines = page_texts[0].split('\n')        # 第 1 頁：個人資料、數值、閾值
    full_text = '\n'.join(page_texts)         # 全部頁：摘要用關鍵字搜尋

    result = {}

    info_line = lines[5]
    result['編號']    = re.search(r'編號:\s*(\S+)', info_line).group(1)
    result['姓名']    = re.search(r'姓名:\s*(\S+)', info_line).group(1)
    result['性別']    = re.search(r'性別:\s*(\S+)', info_line).group(1)
    result['生日']    = re.search(r'生日:\s*([\d/]+)', info_line).group(1)
    result['年齡']    = float(re.search(r'\(([\d.]+)\)', info_line).group(1))
    # 測量日期同時含日期與 12 小時制時間
    # 三個 group 分別為 日期 / 上午下午 / 時:分:秒，組回成一個字串供上層轉 datetime
    dt_match = re.search(r'測量日期:\s*([\d/]+)\s*:\s*([上下]午)\s*([\d:]+)', lines[4])
    result['測量日期'] = f'{dt_match.group(1)} {dt_match.group(2)} {dt_match.group(3)}'

    NUM = r'\d+(?:\.\d+)?'
    left_org  = re.findall(NUM, lines[9])
    left_cmp  = re.findall(NUM, lines[11])
    right_org = re.findall(NUM, lines[12])
    right_cmp = re.findall(NUM, lines[14])

    result['經絡'] = {}
    for i, meridian in enumerate(MERIDIANS):
        result['經絡'][meridian] = {
            '左側_org': float(left_org[i]),
            '左側_cmp': float(left_cmp[i]),
            '右側_org': float(right_org[i]),
            '右側_cmp': float(right_cmp[i]),
        }

    result['門檻值'] = _parse_thresholds(lines)
    result['摘要分析'] = _parse_summary(full_text)
    return result


def save_meridian_result(instance, data: dict):
    from core.models.meridian import MeridianReading

    thresholds = data['門檻值']
    instance.threshold_toohigh = thresholds['過高值']
    instance.threshold_high    = thresholds['高值']
    instance.threshold_average = thresholds['均值']
    instance.threshold_low     = thresholds['低值']
    instance.threshold_toolow  = thresholds['過低值']
    instance.summary_analysis = data['摘要分析']
    instance.save()

    readings = [
        MeridianReading(
            meridian_test=instance,
            meridian=meridian,
            left_org=values['左側_org'],
            left_cmp=values['左側_cmp'],
            right_org=values['右側_org'],
            right_cmp=values['右側_cmp'],
        )
        for meridian, values in data['經絡'].items()
    ]
    MeridianReading.objects.bulk_create(readings)


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("使用方式: py parse_meridian.py <PDF路徑>")
        print("範例:    py parse_meridian.py xxx.pdf")
        sys.exit(1)

    PDF_PATH = sys.argv[1]
    print(f"解析中：{PDF_PATH}")
    data = parse_meridian_pdf(PDF_PATH)
    print(data)