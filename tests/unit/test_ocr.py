
import pytest
from unittest.mock import patch, MagicMock
import numpy as np
from src.core.ocr_processor import UnifiedOCRProcessor

# テスト用のダミー画像を作成するフィクスチャ
@pytest.fixture
def dummy_image():
    """100x100の黒い画像を生成する"""
    return np.zeros((100, 100, 3), dtype=np.uint8)

# cv2.imreadをモック化し、ダミー画像パスを返すフィクスチャ
@pytest.fixture
def mock_image_load(dummy_image):
    """cv2.imreadをモック化し、常にダミー画像を返すようにする"""
    with patch('src.core.ocr_processor.cv2.imread') as mock_imread:
        mock_imread.return_value = dummy_image
        yield "dummy_path.png"

# OCRエンジン関連の依存関係をモック化するフィクスチャ
@pytest.fixture
def mock_ocr_engines():
    """全てのOCRエンジン（Cloud Vision, EasyOCR, Tesseract）をモック化する"""
    with patch('src.core.ocr_processor.vision.ImageAnnotatorClient') as mock_vision_client, \
         patch('src.core.ocr_processor.easyocr.Reader') as mock_easyocr_reader, \
         patch('src.core.ocr_processor.pytesseract') as mock_pytesseract:
        
        # モックの戻り値を設定
        mock_vision_client.return_value.document_text_detection.return_value = None
        mock_easyocr_reader.return_value.readtext.return_value = []
        mock_pytesseract.image_to_string.return_value = ""
        mock_pytesseract.image_to_data.return_value = {'conf': []}

        yield {
            "vision_client": mock_vision_client,
            "easyocr_reader": mock_easyocr_reader,
            "pytesseract": mock_pytesseract
        }

def test_unified_ocr_processor_initialization(mock_ocr_engines):
    """UnifiedOCRProcessorが正常に初期化されることをテストする"""
    processor = UnifiedOCRProcessor(prefer_cloud=True)
    assert processor is not None, "プロセッサが初期化に失敗しました。"
    assert processor.vision_client is not None, "Cloud Visionクライアントが初期化されていません。"
    assert processor.easy_reader is not None, "EasyOCRリーダーが初期化されていません。"

def test_process_image_uses_cloud_vision_when_preferred(mock_ocr_engines, mock_image_load):
    """prefer_cloud=Trueの場合、Cloud Vision APIが優先的に使用されることをテストする"""
    processor = UnifiedOCRProcessor(prefer_cloud=True, confidence_threshold=0.8)

    # 内部のOCRメソッドをモック化してフローを制御
    with patch.object(processor, '_ocr_with_cloud_vision') as mock_cv, \
         patch.object(processor, '_ocr_with_easyocr') as mock_easy, \
         patch.object(processor, '_ocr_with_tesseract') as mock_tess:
        
        # Cloud Visionの成功をシミュレート
        mock_cv.return_value = {"text": "cloud vision text", "confidence": 0.9, "metadata": {}}
        
        result = processor.process_image(mock_image_load)
        
        mock_cv.assert_called_once()
        mock_easy.assert_not_called()
        mock_tess.assert_not_called()
        assert result['method'] == 'cloud_vision'
        assert result['text'] == 'cloud vision text'

def test_process_image_falls_back_to_easyocr(mock_ocr_engines, mock_image_load):
    """Cloud Visionが失敗した場合、EasyOCRにフォールバックすることをテストする"""
    processor = UnifiedOCRProcessor(prefer_cloud=True, confidence_threshold=0.8)

    with patch.object(processor, '_ocr_with_cloud_vision') as mock_cv, \
         patch.object(processor, '_ocr_with_easyocr') as mock_easy, \
         patch.object(processor, '_ocr_with_tesseract') as mock_tess:
        
        # Cloud Visionの失敗とEasyOCRの成功をシミュレート
        mock_cv.return_value = None
        mock_easy.return_value = {"text": "easyocr text", "confidence": 0.9, "metadata": {}}

        result = processor.process_image(mock_image_load)

        mock_cv.assert_called_once()
        mock_easy.assert_called_once()
        mock_tess.assert_not_called()
        assert result['method'] == 'easyocr'
        assert result['text'] == 'easyocr text'

def test_process_image_falls_back_to_tesseract(mock_ocr_engines, mock_image_load):
    """Cloud VisionとEasyOCRの両方が失敗した場合、Tesseractにフォールバックすることをテストする"""
    processor = UnifiedOCRProcessor(prefer_cloud=True, confidence_threshold=0.8)

    with patch.object(processor, '_ocr_with_cloud_vision') as mock_cv, \
         patch.object(processor, '_ocr_with_easyocr') as mock_easy, \
         patch.object(processor, '_ocr_with_tesseract') as mock_tess:
        
        # 両方の失敗をシミュレート
        mock_cv.return_value = None
        mock_easy.return_value = None
        mock_tess.return_value = {"text": "tesseract text", "confidence": 0.9, "metadata": {}}

        result = processor.process_image(mock_image_load)

        mock_cv.assert_called_once()
        mock_easy.assert_called_once()
        mock_tess.assert_called_once()
        assert result['method'] == 'tesseract'
        assert result['text'] == 'tesseract text'

def test_process_image_uses_easyocr_when_not_preferred(mock_ocr_engines, mock_image_load):
    """prefer_cloud=Falseの場合、EasyOCRが優先的に使用されることをテストする"""
    processor = UnifiedOCRProcessor(prefer_cloud=False, confidence_threshold=0.8)

    with patch.object(processor, '_ocr_with_cloud_vision') as mock_cv, \
         patch.object(processor, '_ocr_with_easyocr') as mock_easy, \
         patch.object(processor, '_ocr_with_tesseract') as mock_tess:
        
        # EasyOCRの成功をシミュレート
        mock_easy.return_value = {"text": "easyocr text", "confidence": 0.9, "metadata": {}}
        mock_tess.return_value = {"text": "tesseract text", "confidence": 0.9, "metadata": {}}

        result = processor.process_image(mock_image_load)

        mock_cv.assert_not_called()
        mock_easy.assert_called_once()
        mock_tess.assert_not_called()
        assert result['method'] == 'easyocr'
        assert result['text'] == 'easyocr text'

