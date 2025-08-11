""""
統合OCR処理モジュール
OpenAI Vision, EasyOCR, Tesseractを協調させてリッチなメタデータを生成する
"""
from typing import List, Dict, Any, Optional
import cv2
import numpy as np
import easyocr
import pytesseract
from PIL import Image
import logging
import hashlib
import os
import concurrent.futures
import time
import openai
import base64
import json

class UnifiedOCRProcessor:
    """
    統合OCRプロセッサー
    - OpenAI Vision API (GPT-5mini) を主軸に、EasyOCRとTesseractでメタデータを補強する
    """
    
    def __init__(self, 
                 languages: List[str] = ['ja', 'en'],
                 enable_caching: bool = True,
                 max_workers: int = 3):
        """
        Args:
            languages: 対応言語リスト
            enable_caching: キャッシュ機能の有効化
            max_workers: 並列処理の最大ワーカー数
        """
        self.logger = logging.getLogger(__name__)
        self.languages = languages
        self.enable_caching = enable_caching
        self.max_workers = max_workers
        self.openai_client = None
        
        # キャッシュディレクトリの作成
        if enable_caching:
            self.cache_dir = "./ocr_cache"
            os.makedirs(self.cache_dir, exist_ok=True)
        
        # OpenAI クライアント初期化
        try:
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                raise ValueError("OPENAI_API_KEY environment variable not set.")
            self.openai_client = openai.OpenAI(api_key=api_key)
            self.logger.info("OpenAI client initialized")
        except Exception as e:
            self.logger.warning(f"OpenAI client unavailable: {e}")
        
        # EasyOCR初期化
        try:
            self.easy_reader = easyocr.Reader(languages)
            self.logger.info("EasyOCR initialized")
        except Exception as e:
            self.logger.warning(f"EasyOCR unavailable: {e}")
            self.easy_reader = None

    def process_image(self, image_path: str) -> Dict[str, Any]:
        """
        画像からテキストとリッチなメタデータを抽出（統合処理）
        """
        # キャッシュチェック
        if self.enable_caching:
            cache_key = self._generate_cache_key(image_path)
            cached_result = self._get_cached_result(cache_key)
            if cached_result:
                self.logger.info(f"Using cached OCR result for {image_path}")
                return cached_result

        # 画像読み込み
        image_for_ocr = cv2.imread(image_path)
        if image_for_ocr is None:
            raise ValueError(f"Failed to load image: {image_path}")

        base_result = {}
        supplemental_metadata = {}

        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # 主エンジン (OpenAI) を実行
            future_openai = executor.submit(self._process_with_openai_vision, image_path)
            
            # 補助エンジン (EasyOCR, Tesseract) を実行
            future_easyocr = executor.submit(self._ocr_with_easyocr, image_for_ocr) if self.easy_reader else None
            future_tesseract = executor.submit(self._ocr_with_tesseract, image_for_ocr)

            # OpenAIの結果を取得 (最優先)
            try:
                base_result = future_openai.result(timeout=60) # OpenAIは時間がかかる可能性
            except Exception as e:
                self.logger.error(f"OpenAI Vision processing failed critically: {e}")
                base_result = {"text": "", "confidence": 0.0, "method": "openai_vision_failed", "metadata": {}}

            # 補助エンジンの結果を収集
            try:
                easyocr_result = future_easyocr.result(timeout=30) if future_easyocr else None
                if easyocr_result:
                    supplemental_metadata.update(easyocr_result['metadata'])
            except Exception as e:
                self.logger.warning(f"EasyOCR failed to provide supplemental data: {e}")

            try:
                tesseract_result = future_tesseract.result(timeout=30)
                if tesseract_result:
                    supplemental_metadata.update(tesseract_result['metadata'])
            except Exception as e:
                self.logger.warning(f"Tesseract failed to provide supplemental data: {e}")

        # 結果を統合
        final_result = base_result
        final_result['metadata'].update(supplemental_metadata)

        # キャッシュに保存
        if self.enable_caching:
            self._cache_result(cache_key, final_result)
        
        return final_result

    def _process_with_openai_vision(self, image_path: str) -> Dict[str, Any]:
        """OpenAI Vision API (GPT-5mini) による画像解析と創造的メタデータ生成"""
        self.logger.info(f"Processing with OpenAI Vision: {image_path}")
        
        try:
            with open(image_path, "rb") as image_file:
                base64_image = base64.b64encode(image_file.read()).decode('utf-8')

            response = self.openai_client.chat.completions.create(
                model="gpt-5-mini",
                response_format={"type": "json_object"},
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": """この画像から以下の情報を抽出し、指定されたJSON形式で返してください。
                                1. `extracted_text`: 画像に含まれるすべてのテキストを、元のレイアウトや段落を尊重して正確に書き起こしてください。
                                2. `summary`: 画像の視覚的な内容を2〜3文で要約してください。
                                3. `creative_tags`: 抽出したテキストと画像の内容から連想される、検索精度向上に役立つキーワードやタグを10〜15個、創造的に生成してください。
                                4. `image_category`: この画像が属するカテゴリを推定してください（例: ドキュメント、風景、人物、図表など）。
                                """
                            },
                            {
                                "type": "image_url",
                                "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}
                            }
                        ]
                    }
                ],
                max_tokens=2048,
            )

            response_data = json.loads(response.choices[0].message.content)
            
            return {
                "text": response_data.get("extracted_text", ""),
                "confidence": 0.95, # 高信頼度と仮定
                "method": "openai_vision",
                "metadata": {
                    "summary": response_data.get("summary", ""),
                    "tags": response_data.get("creative_tags", []),
                    "category": response_data.get("image_category", "unknown"),
                    "model": "gpt-5-mini"
                }
            }

        except Exception as e:
            self.logger.error(f"OpenAI Vision processing failed: {e}")
            # 失敗した場合でも、後続の処理のために空の構造を返す
            return {"text": "", "confidence": 0.0, "method": "openai_vision_failed", "metadata": {"error": str(e)}}

    def _generate_cache_key(self, image_path: str) -> str:
        """キャッシュキーの生成"""
        file_hash = hashlib.md5()
        with open(image_path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b""):
                file_hash.update(chunk)
        return file_hash.hexdigest()
    
    def _get_cached_result(self, cache_key: str) -> Optional[Dict[str, Any]]:
        if not self.enable_caching: return None
        cache_file = os.path.join(self.cache_dir, f"{cache_key}.json")
        if os.path.exists(cache_file):
            try:
                with open(cache_file, 'r', encoding='utf-8') as f: return json.load(f)
            except Exception as e: self.logger.warning(f"Failed to load cache: {e}")
        return None
    
    def _cache_result(self, cache_key: str, result: Dict[str, Any]) -> None:
        if not self.enable_caching: return
        cache_file = os.path.join(self.cache_dir, f"{cache_key}.json")
        try:
            with open(cache_file, 'w', encoding='utf-8') as f: json.dump(result, f, ensure_ascii=False, indent=2)
        except Exception as e: self.logger.warning(f"Failed to save cache: {e}")
    
    def _ocr_with_easyocr(self, image: np.ndarray) -> Optional[Dict[str, Any]]:
        """EasyOCRによる補助的メタデータ抽出"""
        try:
            results = self.easy_reader.readtext(image)
            if not results: return None
            return {
                "metadata": {
                    "easyocr_bbox_list": [item[0] for item in results]
                }
            }
        except Exception as e:
            self.logger.error(f"EasyOCR failed: {e}")
            return None
    
    def _ocr_with_tesseract(self, image: np.ndarray) -> Dict[str, Any]:
        """Tesseractによる補助的メタデータ抽出"""
        try:
            data = pytesseract.image_to_data(image, lang='+'.join(['jpn' if l == 'ja' else l for l in self.languages]), output_type=pytesseract.Output.DICT)
            num_words = len([w for w in data['text'] if w.strip()])
            return {
                "metadata": {
                    "tesseract_word_count": num_words
                }
            }
        except Exception as e:
            self.logger.error(f"Tesseract failed: {e}")
            return {"metadata": {"tesseract_error": str(e)}}
"
from typing import List, Dict, Any, Optional
import cv2
import numpy as np
from google.cloud import vision
import easyocr
import pytesseract
from PIL import Image
import logging
import hashlib
import os
from functools import lru_cache
import concurrent.futures
import time

class UnifiedOCRProcessor:
    """
    統合OCRプロセッサー
    - Cloud Vision API
    - EasyOCR
    - Tesseract
    を状況に応じて使い分け
    """
    
    def __init__(self, 
                 prefer_cloud: bool = True,
                 languages: List[str] = ['ja', 'en'],
                 confidence_threshold: float = 0.8,
                 enable_caching: bool = True,
                 max_workers: int = 3):
        """
        Args:
            prefer_cloud: Cloud Vision APIを優先使用
            languages: 対応言語リスト
            confidence_threshold: 信頼度閾値
            enable_caching: キャッシュ機能の有効化
            max_workers: 並列処理の最大ワーカー数
        """
        self.logger = logging.getLogger(__name__)
        self.prefer_cloud = prefer_cloud
        self.languages = languages
        self.confidence_threshold = confidence_threshold
        self.enable_caching = enable_caching
        self.max_workers = max_workers
        
        # キャッシュディレクトリの作成
        if enable_caching:
            self.cache_dir = "./ocr_cache"
            os.makedirs(self.cache_dir, exist_ok=True)
        
        # Cloud Vision クライアント初期化
        if prefer_cloud:
            try:
                self.vision_client = vision.ImageAnnotatorClient()
                self.logger.info("Cloud Vision API initialized")
            except Exception as e:
                self.logger.warning(f"Cloud Vision unavailable: {e}")
                self.vision_client = None
        
        # EasyOCR初期化
        try:
            self.easy_reader = easyocr.Reader(languages)
            self.logger.info("EasyOCR initialized")
        except Exception as e:
            self.logger.warning(f"EasyOCR unavailable: {e}")
            self.easy_reader = None
    
    def process_image(self, 
                     image_path: str,
                     preprocess: bool = True,
                     detect_layout: bool = True) -> Dict[str, Any]:
        """
        画像からテキストを抽出（統合処理）
        
        Returns:
            {
                "text": str,              # 抽出テキスト
                "confidence": float,      # 信頼度スコア
                "layout": Dict,          # レイアウト情報
                "method": str,           # 使用したOCR手法
                "metadata": Dict         # その他メタデータ
            }
        """
        # キャッシュチェック
        if self.enable_caching:
            cache_key = self._generate_cache_key(image_path, preprocess, detect_layout)
            cached_result = self._get_cached_result(cache_key)
            if cached_result:
                self.logger.info(f"Using cached OCR result for {image_path}")
                return cached_result
        
        # 画像読み込み
        image = cv2.imread(image_path)
        if image is None:
            raise ValueError(f"Failed to load image: {image_path}")
        
        # 前処理
        if preprocess:
            image = self._preprocess_image(image)
        
        # レイアウト検出
        layout_info = {}
        if detect_layout:
            layout_info = self._detect_layout(image)
        
        # OCR実行（優先順位に従って）
        result = None
        
        # 並列処理でOCRを実行
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {}
            
            # 1. Cloud Vision API
            if self.prefer_cloud and self.vision_client:
                futures['cloud_vision'] = executor.submit(self._ocr_with_cloud_vision, image_path)
            
            # 2. EasyOCR
            if self.easy_reader:
                futures['easyocr'] = executor.submit(self._ocr_with_easyocr, image)
            
            # 3. Tesseract（フォールバック）
            futures['tesseract'] = executor.submit(self._ocr_with_tesseract, image)
            
            # 結果の取得と評価
            for method, future in futures.items():
                try:
                    ocr_result = future.result(timeout=30)  # 30秒タイムアウト
                    if ocr_result and ocr_result.get('confidence', 0) >= self.confidence_threshold:
                        result = ocr_result
                        result['method'] = method
                        result['layout'] = layout_info
                        break
                except concurrent.futures.TimeoutError:
                    self.logger.warning(f"OCR method {method} timed out")
                except Exception as e:
                    self.logger.error(f"OCR method {method} failed: {e}")
        
        # フォールバック: 最高信頼度の結果を使用
        if not result:
            results = []
            for method, future in futures.items():
                try:
                    ocr_result = future.result(timeout=5)
                    if ocr_result:
                        ocr_result['method'] = method
                        results.append(ocr_result)
                except:
                    continue
            
            if results:
                result = max(results, key=lambda x: x.get('confidence', 0))
                result['layout'] = layout_info
            else:
                result = {
                    "text": "",
                    "confidence": 0.0,
                    "method": "none",
                    "layout": layout_info,
                    "metadata": {"error": "All OCR methods failed"}
                }
        
        # キャッシュに保存
        if self.enable_caching:
            self._cache_result(cache_key, result)
        
        return result
    
    def _generate_cache_key(self, image_path: str, preprocess: bool, detect_layout: bool) -> str:
        """キャッシュキーの生成"""
        file_hash = hashlib.md5()
        with open(image_path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b""):
                file_hash.update(chunk)
        
        key_data = f"{file_hash.hexdigest()}_{preprocess}_{detect_layout}_{self.confidence_threshold}"
        return hashlib.sha256(key_data.encode()).hexdigest()
    
    def _get_cached_result(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """キャッシュから結果を取得"""
        if not self.enable_caching:
            return None
        
        cache_file = os.path.join(self.cache_dir, f"{cache_key}.json")
        if os.path.exists(cache_file):
            try:
                import json
                with open(cache_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                self.logger.warning(f"Failed to load cache: {e}")
        
        return None
    
    def _cache_result(self, cache_key: str, result: Dict[str, Any]) -> None:
        """結果をキャッシュに保存"""
        if not self.enable_caching:
            return
        
        cache_file = os.path.join(self.cache_dir, f"{cache_key}.json")
        try:
            import json
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
        except Exception as e:
            self.logger.warning(f"Failed to save cache: {e}")
    
    def _preprocess_image(self, image: np.ndarray) -> np.ndarray:
        """
        画像前処理（最適化版）
        - ノイズ除去
        - コントラスト調整
        - 二値化
        """
        # グレースケール変換
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # ノイズ除去（高速化）
        denoised = cv2.fastNlMeansDenoising(gray, None, 10, 7, 21)
        
        # コントラスト調整（CLAHE）
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
        enhanced = clahe.apply(denoised)
        
        # 適応的二値化
        binary = cv2.adaptiveThreshold(
            enhanced,
            255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY,
            11,
            2
        )
        
        return binary
    
    def _detect_layout(self, image: np.ndarray) -> Dict[str, Any]:
        """
        レイアウト解析
        - テーブル検出
        - カラム検出
        - 画像領域検出
        """
        layout = {
            "tables": [],
            "columns": [],
            "images": [],
            "text_blocks": []
        }
        
        # 輪郭検出によるブロック認識
        contours, _ = cv2.findContours(
            image,
            cv2.RETR_EXTERNAL,
            cv2.CHAIN_APPROX_SIMPLE
        )
        
        for contour in contours:
            x, y, w, h = cv2.boundingRect(contour)
            area = w * h
            
            # サイズと縦横比でブロックタイプを推定
            aspect_ratio = w / h if h > 0 else 0
            
            if area > 10000:  # 大きなブロック
                if 0.8 < aspect_ratio < 1.2:  # 正方形に近い
                    layout["images"].append({
                        "bbox": [x, y, w, h],
                        "confidence": 0.7
                    })
                elif aspect_ratio > 3:  # 横長
                    layout["tables"].append({
                        "bbox": [x, y, w, h],
                        "confidence": 0.6
                    })
                else:
                    layout["text_blocks"].append({
                        "bbox": [x, y, w, h],
                        "confidence": 0.8
                    })
        
        return layout
    
    def _ocr_with_cloud_vision(self, image_path: str) -> Optional[Dict[str, Any]]:
        """Cloud Vision API によるOCR"""
        try:
            with open(image_path, 'rb') as image_file:
                content = image_file.read()
            
            image = vision.Image(content=content)
            response = self.vision_client.document_text_detection(
                image=image,
                image_context={"language_hints": self.languages}
            )
            
            if response.error.message:
                self.logger.error(f"Cloud Vision error: {response.error.message}")
                return None
            
            text = response.full_text_annotation.text
            
            # 信頼度スコア計算
            confidence_scores = []
            for page in response.full_text_annotation.pages:
                for block in page.blocks:
                    confidence_scores.append(block.confidence)
            
            avg_confidence = np.mean(confidence_scores) if confidence_scores else 0
            
            return {
                "text": text,
                "confidence": avg_confidence,
                "metadata": {
                    "detected_languages": [
                        lang.language_code 
                        for lang in response.full_text_annotation.pages[0].property.detected_languages
                    ] if response.full_text_annotation.pages else []
                }
            }
            
        except Exception as e:
            self.logger.error(f"Cloud Vision OCR failed: {e}")
            return None
    
    def _ocr_with_easyocr(self, image: np.ndarray) -> Optional[Dict[str, Any]]:
        """EasyOCRによるOCR"""
        try:
            results = self.easy_reader.readtext(image)
            
            if not results:
                return None
            
            texts = []
            confidences = []
            
            for (bbox, text, confidence) in results:
                texts.append(text)
                confidences.append(confidence)
            
            full_text = ' '.join(texts)
            avg_confidence = np.mean(confidences) if confidences else 0
            
            return {
                "text": full_text,
                "confidence": avg_confidence,
                "metadata": {
                    "num_blocks": len(results),
                    "bbox_list": [bbox for bbox, _, _ in results]
                }
            }
            
        except Exception as e:
            self.logger.error(f"EasyOCR failed: {e}")
            return None
    
    def _ocr_with_tesseract(self, image: np.ndarray) -> Dict[str, Any]:
        """Tesseractによるフォールバック処理"""
        try:
            # 言語設定
            lang_str = '+'.join(['jpn' if l == 'ja' else l for l in self.languages])
            
            # OCR実行
            custom_config = r'--oem 3 --psm 6'
            text = pytesseract.image_to_string(
                image,
                lang=lang_str,
                config=custom_config
            )
            
            # データ詳細取得
            data = pytesseract.image_to_data(
                image,
                lang=lang_str,
                output_type=pytesseract.Output.DICT
            )
            
            # 信頼度計算
            confidences = [
                int(conf) for conf in data['conf'] 
                if int(conf) > 0
            ]
            avg_confidence = np.mean(confidences) / 100 if confidences else 0
            
            return {
                "text": text.strip(),
                "confidence": avg_confidence,
                "metadata": {
                    "num_words": len([w for w in data['text'] if w.strip()])
                }
            }
            
        except Exception as e:
            self.logger.error(f"Tesseract failed: {e}")
            return {
                "text": "",
                "confidence": 0.0,
                "metadata": {"error": str(e)}
            }