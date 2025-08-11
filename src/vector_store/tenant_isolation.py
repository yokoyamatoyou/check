"""
テナント別Vector Store管理モジュール

VertexManagerをラップし、テナントIDに基づいてリソースを分離する。
"""
import logging
from typing import List, Dict, Any, Optional
from src.vector_store.vertex_manager import VertexManager
from src.core.embedding_client import EmbeddingClient

class TenantVectorStore:
    """
    テナントごとに独立したベクトルストアを提供するクラス
    """
    def __init__(self, tenant_id: str, project_id: str, location: str, gcs_bucket_name: str):
        self.logger = logging.getLogger(__name__)
        if not all([tenant_id, project_id, location, gcs_bucket_name]):
            raise ValueError("tenant_id, project_id, location, and gcs_bucket_name are required.")
        
        self.tenant_id = tenant_id
        self.project_id = project_id
        self.location = location
        self.gcs_bucket_name = gcs_bucket_name

        # リソース名のプレフィックスをテナントIDに基づいて設定
        # Vertex AIのリソース名は小文字、数字、ハイフンのみ許容
        self.resource_prefix = f"rag-system-{self.tenant_id.lower().replace('_', '-')}"
        self.index_name = f"{self.resource_prefix}-index"
        self.endpoint_name = f"{self.resource_prefix}-endpoint"
        self.deployed_index_id = f"{self.resource_prefix}-deployed"
        self.gcs_bucket_uri = f"gs://{self.gcs_bucket_name}/{self.tenant_id}/"

        self.manager = VertexManager(project_id, location)
        self.embedding_client = EmbeddingClient()
        self.dimensions = self.embedding_client.primary_dimensions

        # 初期化時にインデックスとエンドポイントを準備
        self._setup_vector_search()

    def _setup_vector_search(self):
        """Vector Searchのインデックスとエンドポイントを準備する"""
        self.logger.info(f"Setting up Vector Search for tenant: {self.tenant_id}")
        index = self.manager.get_or_create_index(self.index_name, self.dimensions, self.gcs_bucket_uri)
        endpoint = self.manager.get_or_create_index_endpoint(self.endpoint_name)

        if index and endpoint:
            self.manager.deploy_index(endpoint, index, self.deployed_index_id)
            self.index = index
            self.endpoint = endpoint
            self.logger.info(f"Vector Search setup complete for tenant: {self.tenant_id}")
        else:
            self.index = None
            self.endpoint = None
            self.logger.error(f"Vector Search setup failed for tenant: {self.tenant_id}")

    def upsert(self, chunks: List[Dict[str, Any]]) -> bool:
        """
        チャンクデータをVector Searchにアップサートする
        
        Args:
            chunks: チャンク情報のリスト。各要素は id, embedding を含む必要がある。
        """
        if not self.index:
            self.logger.error("Index is not available. Cannot upsert data.")
            return False

        datapoints = [
            {"id": chunk["id"], "embedding": chunk["embedding"]}
            for chunk in chunks if "id" in chunk and "embedding" in chunk
        ]

        if not datapoints:
            self.logger.warning("No valid datapoints to upsert.")
            return False

        # Vector SearchではGCS経由でデータを更新するため、ここではその処理を模倣
        return self.manager.upsert_data(self.index, datapoints)

    def search(self, query: str, num_neighbors: int = 10) -> List[Dict[str, Any]]:
        """
        クエリをベクトル化し、類似ベクトルを検索する
        """
        if not self.endpoint:
            self.logger.error("Index Endpoint is not available. Cannot perform search.")
            return []

        query_embedding = self.embedding_client.get_embedding(query)
        
        search_results = self.manager.search(
            endpoint=self.endpoint,
            deployed_index_id=self.deployed_index_id,
            queries=[query_embedding],
            num_neighbors=num_neighbors
        )

        # 結果をパースして返す
        results = []
        if search_results:
            for neighbor in search_results[0]: # クエリは1つなので最初の結果を取得
                results.append({
                    "id": neighbor.id,
                    "distance": neighbor.distance
                })
        
        return results
