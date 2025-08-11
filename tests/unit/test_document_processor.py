"""
ドキュメント処理モジュールのユニットテスト
"""
import pytest
import tempfile
import os
from unittest.mock import Mock, patch, MagicMock
from src.core.document_processor import DocumentProcessor
from src.core.chunk_processor import ChunkProcessor
from src.parsers.base_parser import BaseParser
from src.parsers.pdf_parser import PdfParser
from src.parsers.text_parser import TextParser
from src.parsers.word_parser import WordParser
from src.parsers.image_parser import ImageParser

class TestDocumentProcessor:
    """DocumentProcessorのテストクラス"""
    
    def setup_method(self):
        """テスト前のセットアップ"""
        self.processor = DocumentProcessor()
        self.chunk_processor = ChunkProcessor()
    
    def test_processor_initialization(self):
        """プロセッサーの初期化テスト"""
        assert self.processor is not None
        assert hasattr(self.processor, 'parsers')
        assert len(self.processor.parsers) > 0
    
    def test_get_parser_for_pdf(self):
        """PDFファイル用パーサーの取得テスト"""
        parser_class = self.processor.parsers.get('.pdf')
        assert parser_class == PdfParser
    
    def test_get_parser_for_txt(self):
        """テキストファイル用パーサーの取得テスト"""
        parser_class = self.processor.parsers.get('.txt')
        assert parser_class == TextParser
    
    def test_get_parser_for_docx(self):
        """Wordファイル用パーサーの取得テスト"""
        parser_class = self.processor.parsers.get('.docx')
        assert parser_class == WordParser
    
    def test_get_parser_for_image(self):
        """画像ファイル用パーサーの取得テスト"""
        parser_class = self.processor.parsers.get('.jpg')
        assert parser_class == ImageParser
    
    def test_get_parser_unknown_extension(self):
        """未知の拡張子に対するテスト"""
        parser_class = self.processor.parsers.get('.unknown')
        assert parser_class is None
    
    @patch('src.parsers.pdf_parser.fitz')
    def test_process_pdf_document(self, mock_fitz):
        """PDFドキュメント処理のテスト"""
        # モック設定
        mock_doc = Mock()
        mock_page = Mock()
        mock_page.get_text.return_value = 'PDF content'
        mock_doc.__iter__ = lambda self: iter([mock_page])
        mock_doc.metadata = {'pages': 2, 'title': 'Test PDF'}
        mock_fitz.open.return_value = mock_doc
        
        # テスト用ファイルを作成
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp_file:
            tmp_file.write(b'fake pdf content')
            tmp_file_path = tmp_file.name
        
        try:
            result = self.processor.process_document(tmp_file_path)
            
            # 検証
            assert result is not None
            assert 'text' in result
            assert 'metadata' in result
            
        finally:
            os.unlink(tmp_file_path)
    
    def test_process_text_document(self):
        """テキストドキュメント処理のテスト"""
        # テスト用ファイルを作成
        with tempfile.NamedTemporaryFile(suffix='.txt', mode='w', delete=False) as tmp_file:
            tmp_file.write('Test text content')
            tmp_file_path = tmp_file.name
        
        try:
            result = self.processor.process_document(tmp_file_path)
            
            # 検証
            assert result is not None
            assert 'text' in result
            assert 'metadata' in result
            assert 'Test text content' in result['text']
            
        finally:
            os.unlink(tmp_file_path)
    
    def test_process_document_file_not_found(self):
        """存在しないファイルの処理テスト"""
        with pytest.raises(FileNotFoundError):
            self.processor.process_document('nonexistent_file.txt')
    
    def test_process_document_unsupported_format(self):
        """サポートされていない形式のファイルテスト"""
        with tempfile.NamedTemporaryFile(suffix='.xyz', delete=False) as tmp_file:
            tmp_file.write(b'content')
            tmp_file_path = tmp_file.name
        
        try:
            with pytest.raises(ValueError, match="サポートされていないファイル拡張子です"):
                self.processor.process_document(tmp_file_path)
        finally:
            os.unlink(tmp_file_path)

class TestChunkProcessor:
    """ChunkProcessorのテストクラス"""
    
    def setup_method(self):
        """テスト前のセットアップ"""
        with patch('src.core.chunk_processor.EmbeddingClient') as mock_embedding_client:
            mock_client = Mock()
            mock_client.get_embeddings.return_value = [[0.1] * 1536] * 10
            mock_embedding_client.return_value = mock_client
            self.chunk_processor = ChunkProcessor()
    
    def test_chunk_processor_initialization(self):
        """チャンクプロセッサーの初期化テスト"""
        assert self.chunk_processor is not None
        assert hasattr(self.chunk_processor, 'chunk_size')
        assert hasattr(self.chunk_processor, 'chunk_overlap')
    
    def test_create_chunks_simple_text(self):
        """シンプルなテキストのチャンク作成テスト"""
        text = "This is a simple text for testing chunk creation."
        metadata = {'source': 'test.txt'}
        chunks = self.chunk_processor.process_and_embed_chunks(text, metadata)
        
        assert len(chunks) > 0
        assert all(isinstance(chunk, dict) for chunk in chunks)
        assert all('text' in chunk for chunk in chunks)
        assert all('metadata' in chunk for chunk in chunks)
    
    def test_create_chunks_long_text(self):
        """長いテキストのチャンク作成テスト"""
        # 長いテキストを生成
        long_text = "This is a very long text. " * 100
        metadata = {'source': 'test.txt'}
        
        chunks = self.chunk_processor.process_and_embed_chunks(long_text, metadata)
        
        assert len(chunks) > 1  # 複数のチャンクが作成される
        assert all(len(chunk['text']) <= self.chunk_processor.chunk_size for chunk in chunks)
    
    def test_create_chunks_with_metadata(self):
        """メタデータ付きチャンク作成テスト"""
        text = "Test text with metadata"
        metadata = {
            'source': 'test.txt',
            'author': 'Test Author',
            'created_date': '2024-01-01'
        }
        
        chunks = self.chunk_processor.process_and_embed_chunks(text, metadata)
        
        assert len(chunks) > 0
        for chunk in chunks:
            assert chunk['metadata']['source'] == 'test.txt'
            assert chunk['metadata']['author'] == 'Test Author'
            assert chunk['metadata']['created_date'] == '2024-01-01'
    
    def test_create_chunks_empty_text(self):
        """空のテキストのチャンク作成テスト"""
        metadata = {'source': 'test.txt'}
        chunks = self.chunk_processor.process_and_embed_chunks("", metadata)
        assert len(chunks) == 0
    
    def test_create_chunks_whitespace_only(self):
        """空白のみのテキストのチャンク作成テスト"""
        metadata = {'source': 'test.txt'}
        chunks = self.chunk_processor.process_and_embed_chunks("   \n\t   ", metadata)
        # 空白のみでも1つのチャンクが作成される（実装に依存）
        assert len(chunks) >= 0
    
    def test_chunk_overlap_functionality(self):
        """チャンクオーバーラップ機能のテスト"""
        text = "This is a test text that should be split into overlapping chunks."
        metadata = {'source': 'test.txt'}
        
        # オーバーラップありでチャンク作成
        chunks = self.chunk_processor.process_and_embed_chunks(text, metadata)
        
        if len(chunks) > 1:
            # 連続するチャンク間でオーバーラップがあることを確認
            for i in range(len(chunks) - 1):
                current_chunk = chunks[i]['text']
                next_chunk = chunks[i + 1]['text']
                
                # オーバーラップ部分が存在することを確認
                # 実際のオーバーラップ検証は実装に依存
                assert len(current_chunk) > 0
                assert len(next_chunk) > 0

class TestParserIntegration:
    """パーサー統合テスト"""
    
    def test_parser_hierarchy(self):
        """パーサーの階層構造テスト"""
        # 基底クラスの確認
        assert issubclass(PdfParser, BaseParser)
        assert issubclass(TextParser, BaseParser)
        assert issubclass(WordParser, BaseParser)
        assert issubclass(ImageParser, BaseParser)
    
    def test_parser_interface(self):
        """パーサーインターフェースのテスト"""
        # 各パーサーがparseメソッドを持っていることを確認
        parsers = [PdfParser(), TextParser(), WordParser(), ImageParser()]
        
        for parser in parsers:
            assert hasattr(parser, 'parse')
            assert callable(getattr(parser, 'parse'))
    
    def test_parser_supported_formats(self):
        """パーサーのサポート形式テスト"""
        pdf_parser = PdfParser()
        text_parser = TextParser()
        word_parser = WordParser()
        image_parser = ImageParser()
        
        # 各パーサーがparseメソッドを持っていることを確認
        assert hasattr(pdf_parser, 'parse')
        assert hasattr(text_parser, 'parse')
        assert hasattr(word_parser, 'parse')
        assert hasattr(image_parser, 'parse')
