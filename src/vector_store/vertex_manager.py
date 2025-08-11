"""
Vertex AI Vector Search 管理モジュール
"""
from typing import List, Dict, Any, Optional
import logging
from google.cloud import aiplatform
from google.api_core import exceptions

class VertexManager:
    """
    Vertex AI Vector Searchを管理するクラス
    - インデックスの作成、取得
    - データポイントのアップサート
    - ベクトル検索の実行
    """

    def __init__(self, project_id: str, location: str):
        """
        Args:
            project_id: GCPプロジェクトID
            location: リージョン
        """
        self.logger = logging.getLogger(__name__)
        self.project_id = project_id
        self.location = location
        aiplatform.init(project=project_id, location=location)
        self.logger.info(f"VertexManager initialized for project '{project_id}' in '{location}'.")

    def get_or_create_index(self, index_name: str, dimensions: int, gcs_bucket_uri: str) -> Optional[aiplatform.MatchingEngineIndex]:
        """
        指定された名前のインデックスを取得、なければ作成する。
        """
        try:
            # 既存のインデックスを検索
            indexes = aiplatform.MatchingEngineIndex.list(filter=f'display_name="{index_name}"')
            if indexes:
                index = indexes[0]
                self.logger.info(f"Found existing index: {index.resource_name}")
                return index
            
            # インデックスが存在しない場合は作成
            self.logger.info(f"No existing index found. Creating new index '{index_name}'...")
            index = aiplatform.MatchingEngineIndex.create_tree_ah_index(
                display_name=index_name,
                contents_delta_uri=gcs_bucket_uri, # チャンクデータを保存するGCSパス
                dimensions=dimensions,
                approximate_neighbors_count=150,
                distance_measure_type="DOT_PRODUCT_DISTANCE",
                leaf_node_embedding_count=500,
                leaf_nodes_to_search_percent=7,
            )
            self.logger.info(f"Successfully created index: {index.resource_name}")
            return index
        except Exception as e:
            self.logger.error(f"Failed to get or create index '{index_name}': {e}", exc_info=True)
            return None

    def get_or_create_index_endpoint(self, endpoint_name: str) -> Optional[aiplatform.MatchingEngineIndexEndpoint]:
        """
        指定された名前のインデックスエンドポイントを取得、なければ作成する。
        """
        try:
            endpoints = aiplatform.MatchingEngineIndexEndpoint.list(filter=f'display_name="{endpoint_name}"')
            if endpoints:
                endpoint = endpoints[0]
                self.logger.info(f"Found existing index endpoint: {endpoint.resource_name}")
                return endpoint

            self.logger.info(f"Creating new index endpoint '{endpoint_name}'...")
            endpoint = aiplatform.MatchingEngineIndexEndpoint.create(
                display_name=endpoint_name,
                public_endpoint_enabled=True, # 外部からのアクセスを許可
            )
            self.logger.info(f"Successfully created index endpoint: {endpoint.resource_name}")
            return endpoint
        except Exception as e:
            self.logger.error(f"Failed to get or create index endpoint '{endpoint_name}': {e}", exc_info=True)
            return None

    def deploy_index(self, endpoint: aiplatform.MatchingEngineIndexEndpoint, index: aiplatform.MatchingEngineIndex, deployed_index_id: str) -> Optional[aiplatform.MatchingEngineIndexEndpoint]:
        """
        インデックスをエンドポイントにデプロイする。
        """
        try:
            # すでにデプロイされているか確認
            if any(d.id == deployed_index_id for d in endpoint.deployed_indexes):
                self.logger.info(f"Index '{deployed_index_id}' is already deployed to endpoint '{endpoint.display_name}'.")
                return endpoint

            self.logger.info(f"Deploying index '{index.display_name}' to endpoint '{endpoint.display_name}'...")
            endpoint.deploy_index(
                index=index,
                deployed_index_id=deployed_index_id
            )
            self.logger.info("Index deployed successfully.")
            return endpoint
        except exceptions.FailedPrecondition as e:
             self.logger.warning(f"Deployment might be in progress or already exists: {e}")
             return endpoint # すでにデプロイ処理中か、完了している可能性が高い
        except Exception as e:
            self.logger.error(f"Failed to deploy index: {e}", exc_info=True)
            return None

    def upsert_data(self, index: aiplatform.MatchingEngineIndex, datapoints: List[Dict[str, Any]]):
        """
        データポイントをインデックスにアップサートする。
        Vector Searchでは、GCS上のファイルを更新し、インデックスを再構築（アップデート）することでデータを更新する。
        ここでは、そのためのファイルを作成する処理を模倣する。
        
        Args:
            datapoints: [{"id": str, "embedding": List[float]}]
        """
        # ここでは実際のGCSへのファイル書き込みは行わず、ロギングに留める。
        # 本番環境では、これらのデータポイントをJSONL形式でGCSにアップロードし、
        # index.update() を呼び出す必要がある。
        self.logger.info(f"Simulating upsert of {len(datapoints)} datapoints to GCS for index '{index.display_name}'.")
        # index.update(contents_delta_uri=NEW_GCS_PATH)
        return True

    def search(self, endpoint: aiplatform.MatchingEngineIndexEndpoint, deployed_index_id: str, queries: List[List[float]], num_neighbors: int = 10) -> List[Any]:
        """
        ベクトル検索を実行
        """
        try:
            response = endpoint.match(
                deployed_index_id=deployed_index_id,
                queries=queries,
                num_neighbors=num_neighbors
            )
            self.logger.info(f"Search completed successfully for {len(queries)} queries.")
            return response
        except Exception as e:
            self.logger.error(f"Failed to search: {e}", exc_info=True)
            return []