"""
PDF/Word文書の解析
AIエージェントへの指示：
1. テキスト抽出可能なPDFと画像PDFを自動判別
2. 画像PDFの場合はOCRParserに委譲
3. Word文書の画像も抽出してOCR処理
4. 表やリストの構造を保持
"""
import pypdf
from docx import Document
from pdf2image import convert_from_path
import os
from typing import List, Dict, Any
from .base_parser import BaseParser
from .ocr_parser import OCRParser

class DocumentParser(BaseParser):
    def __init__(self):
        super().__init__()
        self.ocr_parser = OCRParser()
    
    def parse(self, file_path: str, **kwargs) -> List[Dict[str, Any]]:
        """
        PDF/Word文書を解析
        
        処理フロー:
        1. ファイル形式の判定
        2. テキスト抽出を試行
        3. 失敗した場合はOCR処理
        4. 画像の抽出と処理
        5. メタデータの抽出
        """
        file_ext = file_path.lower().split('.')[-1]
        
        if file_ext == 'pdf':
            return self._parse_pdf(file_path)
        elif file_ext in ['docx', 'doc']:
            return self._parse_word(file_path)
        else:
            raise ValueError(f"Unsupported file type: {file_ext}")
    
    def _parse_pdf(self, file_path: str) -> List[Dict[str, Any]]:
        """
        PDF解析
        - テキスト抽出を試行
        - 失敗時は画像変換してOCR
        """
        try:
            reader = pypdf.PdfReader(file_path)
            text_content = ""
            for page in reader.pages:
                text_content += page.extract_text() or ""

            if text_content.strip():
                # テキスト抽出に成功した場合
                return [{
                    "content": text_content,
                    "metadata": {"source_file": file_path, "file_type": "pdf"},
                    "type": "text",
                    "page": 1 # PDF全体として扱う
                }]
            else:
                # テキストが空の場合、画像PDFとしてOCR処理
                self.logger.info(f"PDFからテキストを抽出できませんでした。OCR処理を試行します: {file_path}")
                images = convert_from_path(file_path)
                all_chunks = []
                for i, image in enumerate(images):
                    # 一時ファイルに画像を保存
                    temp_image_path = f"/tmp/page_{i+1}.png"
                    image.save(temp_image_path, 'PNG')
                    
                    ocr_chunks = self.ocr_parser.parse(temp_image_path)
                    for chunk in ocr_chunks:
                        chunk["metadata"]["page"] = i + 1
                        chunk["metadata"]["source_file"] = file_path
                        all_chunks.append(chunk)
                    os.remove(temp_image_path) # 一時ファイルを削除
                return all_chunks
        except Exception as e:
            self.logger.error(f"PDF解析中にエラーが発生しました: {e}")
            return []
    
    def _parse_word(self, file_path: str) -> List[Dict[str, Any]]:
        """
        Word文書解析
        - テキストと画像を分離
        - 画像はOCR処理
        """
        try:
            doc = Document(file_path)
            full_text = []
            for paragraph in doc.paragraphs:
                full_text.append(paragraph.text)
            
            # TODO: 画像の抽出とOCR処理
            # TODO: 表構造の保持

            return [{
                "content": "\n".join(full_text),
                "metadata": {"source_file": file_path, "file_type": "docx"},
                "type": "text",
                "page": 1 # Word全体として扱う
            }]
        except Exception as e:
            self.logger.error(f"Word文書解析中にエラーが発生しました: {e}")
            return []
