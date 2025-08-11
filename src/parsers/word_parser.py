from .base_parser import BaseParser
from typing import Dict, Any
import docx

class WordParser(BaseParser):
    """
    Wordファイル（.docx）用のパーサー
    """
    def parse(self, file_path: str) -> Dict[str, Any]:
        """
        Wordファイルを読み込み、テキストとメタデータを抽出する
        """
        doc = docx.Document(file_path)
        text = "\n".join([para.text for para in doc.paragraphs])
        
        core_properties = doc.core_properties
        metadata = {
            "file_type": "docx",
            "author": core_properties.author,
            "title": core_properties.title,
            "last_modified_by": core_properties.last_modified_by,
        }
        
        return {
            "text": text,
            "metadata": metadata
        }

