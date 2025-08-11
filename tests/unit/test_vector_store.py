"""
ベクトルストア関連のユニットテスト
"""
import pytest
import numpy as np
from unittest.mock import Mock, patch, MagicMock
from src.vector_store.vertex_manager import VertexManager
from src.vector_store.tenant_isolation import TenantIsolation
from src.core.embedding_client import EmbeddingClient

class TestVertexManager:
    """VertexManagerのテストクラス"""
    
    def setup_method(self):
        """テスト前のセットアップ"""
        self.vertex_manager = VertexManager()
    
    def test_vertex_manager_initialization(self):
        """VertexManagerの初期化テスト"""
        assert self.vertex_manager is not None
        assert hasattr(self.vertex_manager, 'project_id')
        assert hasattr(self.vertex_manager, 'region')
    
    @patch('src.vector_store.vertex_manager.vertexai')
    def test_create_index(self, mock_vertexai):
        """インデックス作成のテスト"""
        # モック設定
        mock_index = Mock()
        mock_index.name = "projects/test-project/locations/test-location/indexes/test-index"
        mock_vertexai.MatchingEngineIndex.return_value = mock_index
        
        # テスト実行
        index_name = self.vertex_manager.create_index(
            display_name="test-index",
            dimensions=1536,
            approximate_neighbors_count=150
        )
        
        # 検証
        assert index_name is not None
        assert "test-index" in index_name
    
    @patch('src.vector_store.vertex_manager.vertexai')
    def test_upsert_embeddings(self, mock_vertexai):
        """埋め込みベクトルのアップロードテスト"""
        # モック設定
        mock_index = Mock()
        mock_vertexai.MatchingEngineIndex.return_value = mock_index
        
        # テストデータ
        embeddings = [
            {
                'id': 'doc1',
                'embedding': np.random.rand(1536).tolist(),
                'metadata': {'source': 'test.txt'}
            },
            {
                'id': 'doc2', 
                'embedding': np.random.rand(1536).tolist(),
                'metadata': {'source': 'test2.txt'}
            }
        ]
        
        # テスト実行
        result = self.vertex_manager.upsert_embeddings(
            index_name="test-index",
            embeddings=embeddings
        )
        
        # 検証
        assert result is True
    
    @patch('src.vector_store.vertex_manager.vertexai')
    def test_find_nearest_neighbors(self, mock_vertexai):
        """最近傍検索のテスト"""
        # モック設定
        mock_index = Mock()
        mock_response = Mock()
        mock_response.nearest_neighbors = [
            Mock(id='doc1', distance=0.1),
            Mock(id='doc2', distance=0.2)
        ]
        mock_index.find_neighbors.return_value = mock_response
        mock_vertexai.MatchingEngineIndex.return_value = mock_index
        
        # テストデータ
        query_embedding = np.random.rand(1536).tolist()
        
        # テスト実行
        results = self.vertex_manager.find_nearest_neighbors(
            index_name="test-index",
            query_embedding=query_embedding,
            num_neighbors=5
        )
        
        # 検証
        assert len(results) == 2
        assert results[0]['id'] == 'doc1'
        assert results[0]['distance'] == 0.1
    
    def test_validate_embedding_dimensions(self):
        """埋め込み次元数の検証テスト"""
        # 正常な次元数
        valid_embedding = np.random.rand(1536).tolist()
        assert self.vertex_manager._validate_embedding_dimensions(valid_embedding)
        
        # 不正な次元数
        invalid_embedding = np.random.rand(100).tolist()
        with pytest.raises(ValueError):
            self.vertex_manager._validate_embedding_dimensions(invalid_embedding)
    
    def test_validate_embedding_format(self):
        """埋め込みデータ形式の検証テスト"""
        # 正常な形式
        valid_embeddings = [
            {
                'id': 'doc1',
                'embedding': np.random.rand(1536).tolist(),
                'metadata': {'source': 'test.txt'}
            }
        ]
        assert self.vertex_manager._validate_embedding_format(valid_embeddings)
        
        # 不正な形式（idがない）
        invalid_embeddings = [
            {
                'embedding': np.random.rand(1536).tolist(),
                'metadata': {'source': 'test.txt'}
            }
        ]
        with pytest.raises(ValueError):
            self.vertex_manager._validate_embedding_format(invalid_embeddings)

class TestTenantIsolation:
    """TenantIsolationのテストクラス"""
    
    def setup_method(self):
        """テスト前のセットアップ"""
        self.tenant_isolation = TenantIsolation()
    
    def test_tenant_isolation_initialization(self):
        """TenantIsolationの初期化テスト"""
        assert self.tenant_isolation is not None
    
    def test_get_tenant_index_name(self):
        """テナント別インデックス名の生成テスト"""
        tenant_id = "test-tenant-123"
        index_name = self.tenant_isolation.get_tenant_index_name(tenant_id)
        
        assert index_name is not None
        assert tenant_id in index_name
        assert "index" in index_name
    
    def test_get_tenant_collection_name(self):
        """テナント別コレクション名の生成テスト"""
        tenant_id = "test-tenant-123"
        collection_name = self.tenant_isolation.get_tenant_collection_name(tenant_id)
        
        assert collection_name is not None
        assert tenant_id in collection_name
        assert "documents" in collection_name
    
    def test_validate_tenant_id(self):
        """テナントIDの検証テスト"""
        # 正常なテナントID
        valid_tenant_id = "tenant-123"
        assert self.tenant_isolation.validate_tenant_id(valid_tenant_id)
        
        # 不正なテナントID
        invalid_tenant_ids = ["", None, "tenant@123", "tenant 123"]
        for invalid_id in invalid_tenant_ids:
            with pytest.raises(ValueError):
                self.tenant_isolation.validate_tenant_id(invalid_id)
    
    def test_isolate_query_parameters(self):
        """クエリパラメータの分離テスト"""
        tenant_id = "test-tenant-123"
        base_params = {
            'query': 'test query',
            'limit': 10,
            'filter': 'category:test'
        }
        
        isolated_params = self.tenant_isolation.isolate_query_parameters(
            tenant_id, base_params
        )
        
        assert isolated_params['tenant_id'] == tenant_id
        assert isolated_params['query'] == 'test query'
        assert isolated_params['limit'] == 10
    
    def test_create_tenant_namespace(self):
        """テナント名前空間の作成テスト"""
        tenant_id = "test-tenant-123"
        namespace = self.tenant_isolation.create_tenant_namespace(tenant_id)
        
        assert namespace is not None
        assert tenant_id in namespace
        assert "rag-system" in namespace

class TestEmbeddingClient:
    """EmbeddingClientのテストクラス"""
    
    def setup_method(self):
        """テスト前のセットアップ"""
        self.embedding_client = EmbeddingClient()
    
    def test_embedding_client_initialization(self):
        """EmbeddingClientの初期化テスト"""
        assert self.embedding_client is not None
        assert hasattr(self.embedding_client, 'model_name')
    
    @patch('src.core.embedding_client.openai')
    def test_generate_embedding_openai(self, mock_openai):
        """OpenAI埋め込み生成のテスト"""
        # モック設定
        mock_client = Mock()
        mock_response = Mock()
        mock_response.data = [Mock(embedding=np.random.rand(1536).tolist())]
        mock_client.embeddings.create.return_value = mock_response
        mock_openai.OpenAI.return_value = mock_client
        
        # テスト実行
        text = "This is a test text for embedding generation."
        embedding = self.embedding_client.generate_embedding(text)
        
        # 検証
        assert embedding is not None
        assert len(embedding) == 1536
        assert all(isinstance(x, (int, float)) for x in embedding)
    
    @patch('src.core.embedding_client.genai')
    def test_generate_embedding_google(self, mock_genai):
        """Google埋め込み生成のテスト"""
        # モック設定
        mock_model = Mock()
        mock_model.embed_content.return_value.embedding = np.random.rand(1536).tolist()
        mock_genai.GenerativeModel.return_value = mock_model
        
        # テスト実行
        text = "This is a test text for Google embedding generation."
        embedding = self.embedding_client.generate_embedding(text, provider='google')
        
        # 検証
        assert embedding is not None
        assert len(embedding) == 1536
    
    def test_generate_embedding_empty_text(self):
        """空のテキストの埋め込み生成テスト"""
        with pytest.raises(ValueError):
            self.embedding_client.generate_embedding("")
    
    def test_generate_embedding_very_long_text(self):
        """非常に長いテキストの埋め込み生成テスト"""
        # 長いテキストを生成
        long_text = "This is a very long text. " * 1000
        
        # 長いテキストは自動的に分割されることを確認
        embedding = self.embedding_client.generate_embedding(long_text)
        
        assert embedding is not None
        assert len(embedding) == 1536
    
    def test_batch_generate_embeddings(self):
        """バッチ埋め込み生成のテスト"""
        texts = [
            "First test text",
            "Second test text", 
            "Third test text"
        ]
        
        # モックを使用してバッチ処理をテスト
        with patch.object(self.embedding_client, 'generate_embedding') as mock_generate:
            mock_generate.side_effect = [
                np.random.rand(1536).tolist(),
                np.random.rand(1536).tolist(),
                np.random.rand(1536).tolist()
            ]
            
            embeddings = self.embedding_client.batch_generate_embeddings(texts)
            
            assert len(embeddings) == 3
            assert all(len(emb) == 1536 for emb in embeddings)
    
    def test_normalize_embedding(self):
        """埋め込みベクトルの正規化テスト"""
        # テスト用の埋め込みベクトル
        embedding = [1.0, 2.0, 3.0, 4.0, 5.0]
        
        normalized = self.embedding_client.normalize_embedding(embedding)
        
        # 正規化後のベクトルの長さが1になることを確認
        magnitude = np.sqrt(sum(x**2 for x in normalized))
        assert abs(magnitude - 1.0) < 1e-6
    
    def test_calculate_similarity(self):
        """類似度計算のテスト"""
        embedding1 = [1.0, 0.0, 0.0]
        embedding2 = [0.0, 1.0, 0.0]
        embedding3 = [1.0, 0.0, 0.0]  # embedding1と同じ
        
        # 直交するベクトルの類似度は0
        similarity_orthogonal = self.embedding_client.calculate_similarity(
            embedding1, embedding2
        )
        assert abs(similarity_orthogonal) < 1e-6
        
        # 同じベクトルの類似度は1
        similarity_same = self.embedding_client.calculate_similarity(
            embedding1, embedding3
        )
        assert abs(similarity_same - 1.0) < 1e-6

class TestVectorStoreIntegration:
    """ベクトルストア統合テスト"""
    
    def test_end_to_end_workflow(self):
        """エンドツーエンドワークフローのテスト"""
        # 1. 埋め込み生成
        embedding_client = EmbeddingClient()
        text = "Test document content for vector storage."
        
        with patch.object(embedding_client, 'generate_embedding') as mock_generate:
            mock_generate.return_value = np.random.rand(1536).tolist()
            embedding = embedding_client.generate_embedding(text)
        
        # 2. テナント分離
        tenant_isolation = TenantIsolation()
        tenant_id = "test-tenant-123"
        index_name = tenant_isolation.get_tenant_index_name(tenant_id)
        
        # 3. ベクトルストア操作
        vertex_manager = VertexManager()
        
        with patch.object(vertex_manager, 'upsert_embeddings') as mock_upsert:
            mock_upsert.return_value = True
            
            # 埋め込みのアップロード
            embeddings = [{
                'id': 'doc1',
                'embedding': embedding,
                'metadata': {'source': 'test.txt', 'tenant_id': tenant_id}
            }]
            
            result = vertex_manager.upsert_embeddings(index_name, embeddings)
            assert result is True
        
        # 4. 検索テスト
        with patch.object(vertex_manager, 'find_nearest_neighbors') as mock_search:
            mock_search.return_value = [
                {'id': 'doc1', 'distance': 0.1, 'metadata': {'source': 'test.txt'}}
            ]
            
            results = vertex_manager.find_nearest_neighbors(
                index_name, embedding, num_neighbors=5
            )
            
            assert len(results) == 1
            assert results[0]['id'] == 'doc1'

