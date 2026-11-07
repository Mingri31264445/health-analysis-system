"""
面診分析服務
把照片交給獨立環境(Python 3.11)的面診程式分析，再把結果整理成可存進資料庫的 dict。
"""

import json
import logging
import os
import shutil
import subprocess
import tempfile
import threading
from pathlib import Path

from django.conf import settings
from PIL import Image, ImageOps

logger = logging.getLogger(__name__)

RESULT_IMAGES = ['preprocessed', 'face_mesh', 'spots_boxes', 'spots_circles', 'skin_mask']

# 一次只跑一個分析，避免多人同時上傳把 CPU 吃滿
_analysis_lock = threading.Lock()


class FaceEngineUnavailable(Exception):
    """面診環境沒有設定，或檔案不齊全"""


class FaceAnalysisError(Exception):
    """分析失敗（照片無法辨識、逾時、程式錯誤）；訊息可以直接顯示給使用者"""


def _engine_paths():
    base = settings.FACE_ENGINE_DIR
    if not base:
        raise FaceEngineUnavailable('尚未設定 FACE_ENGINE_DIR。')
    paths = {
        'python': base / '.venv' / 'Scripts' / 'python.exe',
        'script': base / 'face_backend.py',
        'weights': base / 'skin_best.pt',
    }
    missing = [name for name, path in paths.items() if not path.is_file()]
    if missing:
        raise FaceEngineUnavailable(f'面診環境缺少檔案：{", ".join(missing)}')
    return paths


def is_available():
    try:
        _engine_paths()
    except FaceEngineUnavailable:
        return False
    return True


def _prepare_input(image_path, destination):
    """轉正（依照片的拍攝方向）並縮圖，長邊不超過上限，存成 JPG。回傳 (寬, 高)。"""
    with Image.open(image_path) as image:
        image = ImageOps.exif_transpose(image).convert('RGB')
        image.thumbnail((settings.FACE_MAX_IMAGE_SIDE, settings.FACE_MAX_IMAGE_SIDE))
        image.save(destination, 'JPEG', quality=95)
        return image.size


def _read_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def analyze_front_image(image_path, result_dir):
    """分析一張正面照。

    image_path:上傳的原始照片路徑
    result_dir:結果圖要存放的資料夾(Path)，不存在會自動建立
    回傳可以直接存進 FaceDiagnosis.analysis_report 的 dict。
    失敗時丟 FaceEngineUnavailable 或 FaceAnalysisError。
    """
    paths = _engine_paths()
    result_dir = Path(result_dir)

    with _analysis_lock:
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            tmp = Path(tmp)
            input_dir = tmp / 'in'
            output_dir = tmp / 'out'
            input_dir.mkdir()

            try:
                width, height = _prepare_input(image_path, input_dir / 'front.jpg')
            except OSError as error:
                raise FaceAnalysisError('無法讀取這張照片，請確認檔案是正常的圖片。') from error

            command = [
                str(paths['python']), str(paths['script']),
                '--input', str(input_dir),
                '--weights', str(paths['weights']),
                '--output', str(output_dir),
                '--conf', str(settings.FACE_CONFIDENCE),
                '--recursive',
            ]
            env = {**os.environ, 'PYTHONUTF8': '1', 'PYTHONIOENCODING': 'utf-8'}
            env.pop('VIRTUAL_ENV', None)  # 避免帶入專案自己的虛擬環境

            try:
                process = subprocess.run(
                    command,
                    cwd=str(paths['script'].parent),
                    env=env,
                    capture_output=True,
                    text=True,
                    encoding='utf-8',
                    errors='replace',
                    timeout=settings.FACE_TIMEOUT_SECONDS,
                )
            except subprocess.TimeoutExpired as error:
                raise FaceAnalysisError('分析逾時，請稍後再試，或換一張較小的照片。') from error

            status_file = output_dir / 'batch_status.json'
            if not status_file.is_file():
                logger.error('面診程式沒有產生結果，stderr：%s', process.stderr[-500:])
                raise FaceAnalysisError('分析程式沒有產生結果，請聯絡管理員。')

            status = _read_json(status_file)[0]
            if status['status'] != 'ok':
                raise FaceAnalysisError(status.get('error') or '分析失敗，請換一張照片。')

            detail_dir = output_dir / 'front.jpg'
            report = _read_json(detail_dir / 'detections.json')

            result_dir.mkdir(parents=True, exist_ok=True)
            saved_images = {}
            for name in RESULT_IMAGES:
                source = detail_dir / f'{name}.png'
                if source.is_file():
                    shutil.copy2(source, result_dir / f'{name}.png')
                    saved_images[name] = f'{name}.png'

    detections = [
        {
            'class': item['class'],
            'confidence': round(item['confidence'], 3),
            'box': item['xyxy'],
        }
        for item in report['detections']
    ]
    class_counts = {}
    for item in detections:
        class_counts[item['class']] = class_counts.get(item['class'], 0) + 1

    return {
        'engine': 'MediaPipe + YOLO',
        'confidence_threshold': report['confidence'],
        'image_size': [width, height],
        'total': len(detections),
        'class_counts': class_counts,
        'detections': detections,
        'images': saved_images,
        'note': '低信心候選結果，需人工確認，不作為診斷依據。',
    }