"""
OCR処理を行うパーサー
AIエージェントへの指示：
1. Google Cloud Vision APIとEasyOCRの両方をサポート
2. 画像の前処理（ノイズ除去、コントラスト調整）を実装
3. 日本語と英語の混在文書に対応
4. テーブル構造の認識と保持
"""
from typing import List, Dict, Any
import cv2
import numpy as np
from google.cloud import vision
import easyocr
from .base_parser import BaseParser

class OCRParser(BaseParser):
    def __init__(self, use_cloud_vision: bool = True):
        """
        Parameters:
            use_cloud_vision: Cloud Vision APIを使用するか
        """
        super().__init__()
        self.use_cloud_vision = use_cloud_vision
        
        if use_cloud_vision:
            self.vision_client = vision.ImageAnnotatorClient()
        else:
            self.reader = easyocr.Reader(['ja', 'en'])
    
    def parse(self, image_path: str, **kwargs) -> List[Dict[str, Any]]:
        """
        画像からテキストを抽出
        
        処理フロー:
        1. 画像の前処理（ノイズ除去、二値化）
        2. OCR実行
        3. レイアウト解析
        4. テキストのチャンク化
        """
        image = cv2.imread(image_path)
        if image is None:
            self.logger.error(f"画像の読み込みに失敗しました: {image_path}")
            return []

        preprocessed_image = self.preprocess_image(image)

        if self.use_cloud_vision:
            # Cloud Vision API
            _, encoded_image = cv2.imencode('.png', preprocessed_image)
            image_content = encoded_image.tobytes()
            vision_image = vision.Image(content=image_content)
            response = self.vision_client.document_text_detection(image=vision_image)
            full_text = response.full_text_annotation.text
            # TODO: レイアウト情報の保持とチャンク化
            return [{
                "content": full_text,
                "metadata": {"source_file": image_path, "ocr_engine": "Google Cloud Vision"},
                "type": "text",
                "page": 1
            }]
        else:
            # EasyOCR
            results = self.reader.readtext(preprocessed_image)
            extracted_text = []
            for (bbox, text, prob) in results:
                if prob > Config.OCR_CONFIDENCE_THRESHOLD:
                    extracted_text.append(text)
            full_text = "\n".join(extracted_text)
            # TODO: レイアウト情報の保持とチャンク化
            return [{
                "content": full_text,
                "metadata": {"source_file": image_path, "ocr_engine": "EasyOCR"},
                "type": "text",
                "page": 1
            }]
    
    def preprocess_image(self, image: np.ndarray) -> np.ndarray:
        """画像の前処理"""
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        # ノイズ除去 (メディアンフィルタ)
        denoised = cv2.medianBlur(gray, 3)
        # コントラスト調整 (CLAHE)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
        enhanced = clahe.apply(denoised)
        # 二値化 (大津の二値化)
        _, binary = cv2.threshold(enhanced, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        return binary
    
    def detect_tables(self, image: np.ndarray) -> List[Dict]:
        """テーブル構造の検出"""
        # TODO: 輪郭検出によるテーブル認識
        # TODO: セル分割
        pass
