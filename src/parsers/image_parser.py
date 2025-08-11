from .base_parser import BaseParser
from typing import Dict, Any
from src.core.ocr_processor import UnifiedOCRProcessor

class ImageParser(BaseParser):
    """
    画像ファイル（.png, .jpgなど）用のパーサー
    """
    def __init__(self):
        self.ocr_processor = UnifiedOCRProcessor()

    def parse(self, file_path: str) -> Dict[str, Any]:
        """
        画像ファイルをOCR処理し、テキストとメタデータを抽出する
        """
        # 1. 共通メタデータを取得
        common_metadata = self.get_common_metadata(file_path)
        
        # 2. 画像固有の処理を実行
        ocr_result = self.ocr_processor.process_image(file_path)
        
        # 3. メタデータを統合
        # ocr_result['metadata'] には summary, tags, model などが含まれる
        final_metadata = common_metadata
        final_metadata.update(ocr_result.get("metadata", {}))
        
        # ファイルタイプやOCRメソッドなどの基本情報も追加
        final_metadata["file_type"] = "image"
        final_metadata["ocr_method"] = ocr_result.get("method")
        final_metadata["ocr_confidence"] = ocr_result.get("confidence")
        
        return {
            "text": ocr_result.get("text", ""),
            "metadata": final_metadata
        }