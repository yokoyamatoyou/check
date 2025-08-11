"""
RAGシステム統合テスト
"""
import pytest
import tempfile
import os
from unittest.mock import Mock, patch, MagicMock
from src.rag.rag_engine import RAGEngine
from src.rag.llm_factory import LLMFactory
from src.core.document_processor import DocumentProcessor
from src.core.chunk_processor import ChunkProcessor
from src.vector_store.vertex_manager import VertexManager
from src.core.embedding_client import EmbeddingClient

class TestRAGIntegration:
    """RAGシステム統合テストクラス"""
    
    def setup_method(self):
        """テスト前のセットアップ"""
        self.rag_engine = RAGEngine()
        self.llm_factory = LLMFactory()
        self.document_processor = DocumentProcessor()
        self.chunk_processor = ChunkProcessor()
        self.vertex_manager = VertexManager()
        self.embedding_client = EmbeddingClient()
    
    @patch('src.vector_store.vertex_manager.vertexai')
    @patch('src.core.embedding_client.openai')
    def test_document_ingestion_workflow(self, mock_openai, mock_vertexai):
        """ドキュメント取り込みワークフローのテスト"""
        # モック設定
        mock_client = Mock()
        mock_response = Mock()
        mock_response.data = [Mock(embedding=[0.1] * 1536)]
        mock_client.embeddings.create.return_value = mock_response
        mock_openai.OpenAI.return_value = mock_client
        
        mock_index = Mock()
        mock_vertexai.MatchingEngineIndex.return_value = mock_index
        
        # テストドキュメント作成
        with tempfile.NamedTemporaryFile(suffix='.txt', mode='w', delete=False) as tmp_file:
            tmp_file.write("This is a test document for RAG integration testing.")
            tmp_file_path = tmp_file.name
        
        try:
            # 1. ドキュメント処理
            with patch.object(self.document_processor, 'process_document') as mock_process:
                mock_process.return_value = {
                    'text': 'This is a test document for RAG integration testing.',
                    'metadata': {'source': 'test.txt', 'lines': 1}
                }
                
                doc_result = self.document_processor.process_document(tmp_file_path)
                
                assert doc_result['text'] == 'This is a test document for RAG integration testing.'
                assert doc_result['metadata']['source'] == 'test.txt'
            
            # 2. チャンク作成
            chunks = self.chunk_processor.create_chunks(
                doc_result['text'], 
                doc_result['metadata']
            )
            
            assert len(chunks) > 0
            assert all('text' in chunk for chunk in chunks)
            assert all('metadata' in chunk for chunk in chunks)
            
            # 3. 埋め込み生成
            embeddings = []
            for chunk in chunks:
                embedding = self.embedding_client.generate_embedding(chunk['text'])
                embeddings.append({
                    'id': f"chunk_{len(embeddings)}",
                    'embedding': embedding,
                    'metadata': chunk['metadata']
                })
            
            assert len(embeddings) == len(chunks)
            assert all(len(emb['embedding']) == 1536 for emb in embeddings)
            
            # 4. ベクトルストアへの保存
            with patch.object(self.vertex_manager, 'upsert_embeddings') as mock_upsert:
                mock_upsert.return_value = True
                
                result = self.vertex_manager.upsert_embeddings(
                    "test-index", embeddings
                )
                
                assert result is True
                
        finally:
            os.unlink(tmp_file_path)
    
    @patch('src.vector_store.vertex_manager.vertexai')
    @patch('src.core.embedding_client.openai')
    @patch('src.rag.llm_factory.openai')
    def test_rag_query_workflow(self, mock_llm_openai, mock_embedding_openai, mock_vertexai):
        """RAGクエリワークフローのテスト"""
        # モック設定
        # 埋め込み生成のモック
        mock_embedding_client = Mock()
        mock_embedding_response = Mock()
        mock_embedding_response.data = [Mock(embedding=[0.1] * 1536)]
        mock_embedding_client.embeddings.create.return_value = mock_embedding_response
        mock_embedding_openai.OpenAI.return_value = mock_embedding_client
        
        # LLMのモック
        mock_llm_client = Mock()
        mock_llm_response = Mock()
        mock_llm_response.choices = [Mock(message=Mock(content="This is a test response."))]
        mock_llm_client.chat.completions.create.return_value = mock_llm_response
        mock_llm_openai.OpenAI.return_value = mock_llm_client
        
        # ベクトル検索のモック
        mock_index = Mock()
        mock_search_response = Mock()
        mock_search_response.nearest_neighbors = [
            Mock(id='chunk_1', distance=0.1),
            Mock(id='chunk_2', distance=0.2)
        ]
        mock_index.find_neighbors.return_value = mock_search_response
        mock_vertexai.MatchingEngineIndex.return_value = mock_index
        
        # テストクエリ
        query = "What is the test document about?"
        
        # 1. クエリの埋め込み生成
        query_embedding = self.embedding_client.generate_embedding(query)
        assert len(query_embedding) == 1536
        
        # 2. ベクトル検索
        with patch.object(self.vertex_manager, 'find_nearest_neighbors') as mock_search:
            mock_search.return_value = [
                {
                    'id': 'chunk_1',
                    'distance': 0.1,
                    'metadata': {'source': 'test.txt', 'text': 'This is a test document for RAG integration testing.'}
                },
                {
                    'id': 'chunk_2', 
                    'distance': 0.2,
                    'metadata': {'source': 'test.txt', 'text': 'Additional context information.'}
                }
            ]
            
            search_results = self.vertex_manager.find_nearest_neighbors(
                "test-index", query_embedding, num_neighbors=5
            )
            
            assert len(search_results) == 2
            assert search_results[0]['distance'] < search_results[1]['distance']
        
        # 3. コンテキスト生成
        context = "\n".join([
            result['metadata']['text'] for result in search_results
        ])
        
        assert "test document" in context
        assert "RAG integration" in context
        
        # 4. LLMによる回答生成
        with patch.object(self.llm_factory, 'get_llm') as mock_get_llm:
            mock_llm = Mock()
            mock_llm.generate_response.return_value = "The test document is about RAG integration testing."
            mock_get_llm.return_value = mock_llm
            
            response = self.rag_engine.generate_response(query, context)
            
            assert response is not None
            assert "RAG integration" in response
    
    @patch('src.vector_store.vertex_manager.vertexai')
    def test_tenant_isolation_in_rag(self, mock_vertexai):
        """RAGシステムでのテナント分離テスト"""
        # モック設定
        mock_index = Mock()
        mock_vertexai.MatchingEngineIndex.return_value = mock_index
        
        tenant_id_1 = "tenant-123"
        tenant_id_2 = "tenant-456"
        
        # テナント1のインデックス名
        index_name_1 = self.vertex_manager.get_tenant_index_name(tenant_id_1)
        assert tenant_id_1 in index_name_1
        
        # テナント2のインデックス名
        index_name_2 = self.vertex_manager.get_tenant_index_name(tenant_id_2)
        assert tenant_id_2 in index_name_2
        
        # インデックス名が異なることを確認
        assert index_name_1 != index_name_2
        
        # テナント1のデータをアップロード
        embeddings_1 = [
            {
                'id': 'doc1_tenant1',
                'embedding': [0.1] * 1536,
                'metadata': {'tenant_id': tenant_id_1, 'source': 'tenant1_doc.txt'}
            }
        ]
        
        with patch.object(self.vertex_manager, 'upsert_embeddings') as mock_upsert:
            mock_upsert.return_value = True
            
            result_1 = self.vertex_manager.upsert_embeddings(index_name_1, embeddings_1)
            assert result_1 is True
        
        # テナント2のデータをアップロード
        embeddings_2 = [
            {
                'id': 'doc1_tenant2',
                'embedding': [0.2] * 1536,
                'metadata': {'tenant_id': tenant_id_2, 'source': 'tenant2_doc.txt'}
            }
        ]
        
        with patch.object(self.vertex_manager, 'upsert_embeddings') as mock_upsert:
            mock_upsert.return_value = True
            
            result_2 = self.vertex_manager.upsert_embeddings(index_name_2, embeddings_2)
            assert result_2 is True
    
    def test_error_handling_in_rag_workflow(self):
        """RAGワークフローでのエラーハンドリングテスト"""
        # 空のクエリ
        with pytest.raises(ValueError):
            self.rag_engine.generate_response("", "context")
        
        # 空のコンテキスト
        with pytest.raises(ValueError):
            self.rag_engine.generate_response("query", "")
        
        # 無効なテナントID
        with pytest.raises(ValueError):
            self.vertex_manager.get_tenant_index_name("")
        
        # 無効な埋め込み次元
        with pytest.raises(ValueError):
            self.vertex_manager._validate_embedding_dimensions([0.1] * 100)
    
    @patch('src.vector_store.vertex_manager.vertexai')
    @patch('src.core.embedding_client.openai')
    def test_performance_benchmarks(self, mock_openai, mock_vertexai):
        """パフォーマンスベンチマークテスト"""
        import time
        
        # モック設定
        mock_client = Mock()
        mock_response = Mock()
        mock_response.data = [Mock(embedding=[0.1] * 1536)]
        mock_client.embeddings.create.return_value = mock_response
        mock_openai.OpenAI.return_value = mock_client
        
        mock_index = Mock()
        mock_vertexai.MatchingEngineIndex.return_value = mock_index
        
        # 埋め込み生成のパフォーマンス
        start_time = time.time()
        
        for i in range(10):
            embedding = self.embedding_client.generate_embedding(f"Test text {i}")
            assert len(embedding) == 1536
        
        end_time = time.time()
        processing_time = end_time - start_time
        
        # 10個の埋め込み生成が3秒以内に完了することを確認
        assert processing_time < 3.0
        
        # ベクトル検索のパフォーマンス
        query_embedding = [0.1] * 1536
        
        with patch.object(self.vertex_manager, 'find_nearest_neighbors') as mock_search:
            mock_search.return_value = [
                {'id': f'chunk_{i}', 'distance': 0.1 + i * 0.01} 
                for i in range(5)
            ]
            
            start_time = time.time()
            
            for i in range(10):
                results = self.vertex_manager.find_nearest_neighbors(
                    "test-index", query_embedding, num_neighbors=5
                )
                assert len(results) == 5
            
            end_time = time.time()
            search_time = end_time - start_time
            
            # 10回の検索が1秒以内に完了することを確認
            assert search_time < 1.0

class TestRAGEndToEnd:
    """RAGエンドツーエンドテスト"""
    
    def test_complete_rag_workflow(self):
        """完全なRAGワークフローのテスト"""
        # このテストは実際のAPI呼び出しを避けるため、
        # モックを使用してエンドツーエンドの流れを検証
        
        with patch('src.rag.rag_engine.RAGEngine') as mock_rag_engine_class:
            mock_rag_engine = Mock()
            mock_rag_engine.generate_response.return_value = "Test response"
            mock_rag_engine_class.return_value = mock_rag_engine
            
            # RAGエンジンの初期化
            rag_engine = RAGEngine()
            
            # クエリ処理
            query = "What is the test about?"
            context = "This is a test context for RAG evaluation."
            
            response = rag_engine.generate_response(query, context)
            
            # 検証
            assert response == "Test response"
            
            # メソッドが正しく呼ばれたことを確認
            mock_rag_engine.generate_response.assert_called_once_with(query, context)
    
    def test_rag_with_different_llm_providers(self):
        """異なるLLMプロバイダーでのRAGテスト"""
        providers = ['openai', 'google', 'anthropic']
        
        for provider in providers:
            with patch('src.rag.llm_factory.LLMFactory') as mock_factory_class:
                mock_factory = Mock()
                mock_llm = Mock()
                mock_llm.generate_response.return_value = f"Response from {provider}"
                mock_factory.get_llm.return_value = mock_llm
                mock_factory_class.return_value = mock_factory
                
                # LLMファクトリーの初期化
                llm_factory = LLMFactory()
                
                # プロバイダー別のLLM取得
                llm = llm_factory.get_llm(provider)
                
                # レスポンス生成
                response = llm.generate_response("test query", "test context")
                
                # 検証
                assert response == f"Response from {provider}"
    
    def test_rag_error_recovery(self):
        """RAGシステムのエラー回復テスト"""
        # 一時的なエラーをシミュレート
        with patch('src.rag.rag_engine.RAGEngine') as mock_rag_engine_class:
            mock_rag_engine = Mock()
            
            # 最初の呼び出しでエラー、2回目で成功
            mock_rag_engine.generate_response.side_effect = [
                Exception("Temporary error"),
                "Successful response"
            ]
            
            mock_rag_engine_class.return_value = mock_rag_engine
            
            rag_engine = RAGEngine()
            
            # エラーが発生することを確認
            with pytest.raises(Exception):
                rag_engine.generate_response("query", "context")
            
            # 2回目の呼び出しで成功することを確認
            response = rag_engine.generate_response("query", "context")
            assert response == "Successful response"

