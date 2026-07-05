"""
經絡儀 PDF 解析器
從經絡儀報告 PDF 擷取數值
"""

import pdfplumber
import re
import sys

MERIDIANS = ['肺經','心包','心經','小腸','三焦','大腸','脾經','肝經','腎經','膀胱','膽經','胃經']


def parse_meridian_pdf(pdf_path: str) -> dict:
    with pdfplumber.open(pdf_path) as pdf:
        lines = pdf.pages[0].extract_text().split('\n')

    result = {}

    info_line = lines[5]
    result['編號']    = re.search(r'編號:\s*(\S+)', info_line).group(1)
    result['姓名']    = re.search(r'姓名:\s*(\S+)', info_line).group(1)
    result['性別']    = re.search(r'性別:\s*(\S+)', info_line).group(1)
    result['生日']    = re.search(r'生日:\s*([\d/]+)', info_line).group(1)
    result['年齡']    = float(re.search(r'\(([\d.]+)\)', info_line).group(1))
    result['測量日期'] = re.search(r'測量日期:\s*([\d/]+)', lines[4]).group(1)

    left_org  = re.findall(r'[\d.]+', lines[9])
    left_cmp  = re.findall(r'[\d.]+', lines[11])
    right_org = re.findall(r'[\d.]+', lines[12])
    right_cmp = re.findall(r'[\d.]+', lines[14])

    result['經絡'] = {}
    for i, meridian in enumerate(MERIDIANS):
        result['經絡'][meridian] = {
            '左側_org': float(left_org[i]),
            '左側_cmp': float(left_cmp[i]),
            '右側_org': float(right_org[i]),
            '右側_cmp': float(right_cmp[i]),
        }

    thresholds = [float(lines[i]) for i in range(17, 22)]
    result['門檻值'] = {
        '過高值': thresholds[0],
        '高值':   thresholds[1],
        '均值':   thresholds[2],
        '低值':   thresholds[3],
        '過低值': thresholds[4],
    }

    return result


def save_meridian_result(instance, data: dict):
    from core.models.meridian import MeridianReading

    thresholds = data['門檻值']
    instance.threshold_toohigh = thresholds['過高值']
    instance.threshold_high    = thresholds['高值']
    instance.threshold_average = thresholds['均值']
    instance.threshold_low     = thresholds['低值']
    instance.threshold_toolow  = thresholds['過低值']
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