from .base_parser import BaseParser
from typing import Dict, Any

class TextParser(BaseParser):
    """
    テキストファイル（.txt, .mdなど）用のパーサー
    """
    def parse(self, file_path: str) -> Dict[str, Any]:
        """
        テキストファイルを読み込み、内容とメタデータを返す
        """
        with open(file_path, 'r', encoding='utf-8') as f:
            text = f.read()
        
        return {
            "text": text,
            "metadata": {
                "file_type": "text"
            }
        }