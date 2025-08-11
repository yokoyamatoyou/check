from .base_parser import BaseParser
from typing import Dict, Any
import fitz  # PyMuPDF

class PdfParser(BaseParser):
    """
    PDFファイル用のパーサー
    """
    def parse(self, file_path: str) -> Dict[str, Any]:
        """
        PDFファイルを読み込み、テキストとメタデータを抽出する
        """
        doc = fitz.open(file_path)
        text = ""
        for page in doc:
            text += page.get_text()
            
        metadata = {
            "file_type": "pdf",
            "num_pages": doc.page_count,
            "author": doc.metadata.get("author"),
            "title": doc.metadata.get("title"),
        }
        
        return {
            "text": text,
            "metadata": metadata
        }
