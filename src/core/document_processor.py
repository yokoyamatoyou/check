import os
from typing import Dict, Any, Type
from src.parsers.base_parser import BaseParser
from src.parsers.text_parser import TextParser
from src.parsers.pdf_parser import PdfParser
from src.parsers.word_parser import WordParser
from src.parsers.image_parser import ImageParser
import logging

class DocumentProcessor:
    """
    ファイル拡張子に基づいて適切なパーサーを選択し、
    ドキュメント処理を実行するパイプライン。
    """
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.parsers: Dict[str, Type[BaseParser]] = {
            ".txt": TextParser,
            ".md": TextParser,
            ".pdf": PdfParser,
            ".docx": WordParser,
            ".png": ImageParser,
            ".jpg": ImageParser,
            ".jpeg": ImageParser,
        }
        self.logger.info(f"DocumentProcessor initialized with {len(self.parsers)} parsers.")

    def process_document(self, file_path: str) -> Dict[str, Any]:
        """
        指定されたファイルを処理する。

        Args:
            file_path: 処理対象のファイルパス。

        Returns:
            パースされたテキストとメタデータを含む辞書。

        Raises:
            ValueError: サポートされていないファイル拡張子の場合。
        """
        if not os.path.exists(file_path):
            self.logger.error(f"File not found: {file_path}")
            raise FileNotFoundError(f"指定されたファイルが見つかりません: {file_path}")

        _, extension = os.path.splitext(file_path)
        extension = extension.lower()

        parser_class = self.parsers.get(extension)

        if not parser_class:
            self.logger.warning(f"No parser found for extension: {extension}")
            raise ValueError(f"サポートされていないファイル拡張子です: {extension}")

        try:
            self.logger.info(f"Processing '{file_path}' with {parser_class.__name__}...")
            parser_instance = parser_class()
            result = parser_instance.parse(file_path)
            self.logger.info(f"Successfully processed '{file_path}'.")
            return result
        except Exception as e:
            self.logger.error(f"Failed to process '{file_path}': {e}", exc_info=True)
            raise

# 使用例
if __name__ == '__main__':
    # このスクリプトを直接実行した場合のテストコード
    logging.basicConfig(level=logging.INFO)
    
    # ダミーファイルを作成してテスト
    test_files_dir = "test_documents"
    os.makedirs(test_files_dir, exist_ok=True)

    # 1. テキストファイル
    txt_path = os.path.join(test_files_dir, "test.txt")
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write("これはテキストファイルのテストです。")

    # 2. PDF (PyMuPDFがないと作成できないため、ここではダミーパスのみ)
    # pdf_path = os.path.join(test_files_dir, "test.pdf")

    processor = DocumentProcessor()
    
    try:
        # テキストファイルの処理
        print(f"\n--- Processing {txt_path} ---")
        txt_result = processor.process_document(txt_path)
        print("Text:", txt_result["text"])
        print("Metadata:", txt_result["metadata"])

        # サポートされていないファイルのテスト
        print("\n--- Processing unsupported file ---")
        unsupported_path = os.path.join(test_files_dir, "test.xyz")
        with open(unsupported_path, "w") as f:
            f.write("test")
        processor.process_document(unsupported_path)

    except (ValueError, FileNotFoundError) as e:
        print(f"Error: {e}")
    finally:
        # クリーンアップ
        import shutil
        shutil.rmtree(test_files_dir)
        print(f"\nCleaned up {test_files_dir}.")
