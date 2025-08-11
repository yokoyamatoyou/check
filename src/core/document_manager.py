"""
ドキュメント管理モジュール

アップロードされたドキュメントの処理、状態管理、永続化を行う。
BM25インデックスの管理も担当。
"""
import streamlit as st
import os
import uuid
from datetime import datetime
import logging
from typing import List, Dict, Any, Optional
import pandas as pd
from google.cloud import firestore, storage
from google.api_core import exceptions
import openai
import json
import pickle
from rank_bm25 import BM25Okapi

from src.core.document_processor import DocumentProcessor
from src.core.chunk_processor import ChunkProcessor
from src.core.embedding_client import EmbeddingClient
from src.vector_store.tenant_isolation import TenantVectorStore

class DocumentManager:
    """
    ドキュメントのライフサイクルを管理するクラス
    """

    def __init__(self, tenant_id: str):
        self.logger = logging.getLogger(__name__)
        self.tenant_id = tenant_id
        
        self.gcp_project_id = os.getenv("GCP_PROJECT_ID")
        self.gcs_bucket_name = os.getenv("GCS_BUCKET_NAME_FOR_VECTOR_SEARCH")
        if not all([self.gcp_project_id, self.gcs_bucket_name]):
            raise ValueError("GCP設定の環境変数が不足しています。")

        self.processor = DocumentProcessor()
        self.chunker = ChunkProcessor()
        self.embedding_client = EmbeddingClient()
        self.vector_store = TenantVectorStore(tenant_id)
        self.openai_client = openai.OpenAI()
        self.storage_client = storage.Client()

        self.temp_dir = f"./temp_{self.tenant_id}"
        os.makedirs(self.temp_dir, exist_ok=True)

        self.db = firestore.Client()
        self.doc_collection_path = f"tenants/{self.tenant_id}/documents"
        self.chunk_collection_path = f"tenants/{self.tenant_id}/chunks"
        self.bm25_index_path = f"bm25_indices/{self.tenant_id}/index.pkl"

    def upload_and_process_documents(self, uploaded_files: List[st.runtime.uploaded_file_manager.UploadedFile]):
        for uploaded_file in uploaded_files:
            doc_id = str(uuid.uuid4())
            file_path = os.path.join(self.temp_dir, uploaded_file.name)
            with open(file_path, "wb") as f:
                f.write(uploaded_file.getbuffer())

            try:
                doc_metadata = {
                    "id": doc_id, "name": uploaded_file.name,
                    "size": round(uploaded_file.size / (1024*1024), 2),
                    "type": os.path.splitext(uploaded_file.name)[1],
                    "status": "処理中", "uploaded_at": datetime.utcnow(),
                }
                self.db.collection(self.doc_collection_path).document(doc_id).set(doc_metadata)

                parsed_data = self.processor.process_document(file_path)
                chunks = self.chunker.chunk_text(parsed_data['text'], parsed_data['metadata'])
                enriched_chunks = self._enrich_chunks_concurrently(chunks)

                chunk_texts = [chunk['text'] for chunk in enriched_chunks]
                vectors = self.embedding_client.get_embeddings(chunk_texts)
                for i, chunk in enumerate(enriched_chunks):
                    chunk['vector'] = vectors[i]

                self.vector_store.upsert(enriched_chunks)
                self._save_chunks_to_firestore(doc_id, enriched_chunks)
                self._update_doc_status(doc_id, "処理済み", {"chunk_count": len(enriched_chunks)})

            except Exception as e:
                self.logger.error(f"Failed to process document {doc_id}: {e}", exc_info=True)
                self._update_doc_status(doc_id, "エラー", {"error_message": str(e)})
            finally:
                if os.path.exists(file_path):
                    os.remove(file_path)
        
        # 全ファイルの処理が終わったらBM25インデックスを更新
        self._update_bm25_index()

    def _update_bm25_index(self):
        self.logger.info(f"Updating BM25 index for tenant {self.tenant_id}")
        try:
            all_chunks = self._get_all_chunks_for_tenant()
            if not all_chunks:
                self.logger.info("No chunks found for BM25 indexing.")
                return

            corpus = [chunk['text'] for chunk in all_chunks]
            # TODO: 日本語の場合はMeCab等での分かち書きを推奨
            tokenized_corpus = [doc.split() for doc in corpus]
            chunk_ids = [chunk['id'] for chunk in all_chunks]

            bm25 = BM25Okapi(tokenized_corpus)
            index_data = {"bm25": bm25, "chunk_ids": chunk_ids} 
            
            bucket = self.storage_client.bucket(self.gcs_bucket_name)
            blob = bucket.blob(self.bm25_index_path)
            with blob.open("wb") as f:
                pickle.dump(index_data, f)

            self.logger.info(f"Successfully updated BM25 index to {self.bm25_index_path}")
        except Exception as e:
            self.logger.error(f"Failed to update BM25 index: {e}", exc_info=True)

    def _get_all_chunks_for_tenant(self) -> List[Dict]:
        query = self.db.collection(self.chunk_collection_path).stream()
        return [chunk.to_dict() for chunk in query]

    def _enrich_chunks_concurrently(self, chunks: List[Dict]) -> List[Dict]:
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future_to_chunk = {executor.submit(self._get_rich_metadata_for_chunk, chunk['text']): chunk for chunk in chunks}
            for future in concurrent.futures.as_completed(future_to_chunk):
                chunk = future_to_chunk[future]
                try:
                    rich_metadata = future.result()
                    chunk['metadata'].update(rich_metadata)
                except Exception as exc:
                    self.logger.warning(f'Chunk enrichment generated an exception: {exc}')
        return chunks

    def _get_rich_metadata_for_chunk(self, text: str) -> Dict[str, Any]:
        try:
            response = self.openai_client.chat.completions.create(
                model="gpt-5-mini",
                messages=[
                    {"role": "system", "content": "You are a helpful assistant that analyzes text chunks and generates metadata."},
                    {"role": "user", "content": f"Analyze the following text and provide a brief summary and relevant keywords.\n\nText: \"\"{text}\"\"\n\nOutput format: JSON with keys 'chunk_summary' and 'chunk_keywords' (a list of strings)."}
                ],
                response_format={"type": "json_object"}
            )
            return json.loads(response.choices[0].message.content)
        except Exception as e:
            self.logger.error(f"Failed to get rich metadata for chunk: {e}")
            return {}

    def _save_chunks_to_firestore(self, doc_id: str, chunks: List[Dict]):
        batch = self.db.batch()
        for chunk in chunks:
            chunk_ref = self.db.collection(self.chunk_collection_path).document(chunk['id'])
            chunk_data_for_firestore = {k: v for k, v in chunk.items() if k != 'vector'}
            chunk_data_for_firestore['document_id'] = doc_id
            batch.set(chunk_ref, chunk_data_for_firestore)
        batch.commit()

    def get_all_documents(self, search: str = "", status_filter: str = "すべて") -> List[Dict[str, Any]]:
        try:
            query = self.db.collection(self.doc_collection_path).order_by("uploaded_at", direction=firestore.Query.DESCENDING)
            docs = [doc.to_dict() for doc in query.stream()]
            if search:
                docs = [d for d in docs if search.lower() in d.get("name", "").lower()]
            if status_filter != "すべて":
                docs = [d for d in docs if d.get("status") == status_filter]
            return docs
        except Exception as e:
            self.logger.error(f"Failed to get documents from Firestore: {e}")
            return []

    def _update_doc_status(self, doc_id: str, status: str, details: Dict = None):
        update_data = {"status": status, "updated_at": datetime.utcnow()}
        if details:
            update_data.update(details)
        self.db.collection(self.doc_collection_path).document(doc_id).update(update_data)

    def get_chunks_by_ids(self, chunk_ids: List[str]) -> List[Dict[str, Any]]:
        chunks = []
        for chunk_id in chunk_ids:
            try:
                doc = self.db.collection(self.chunk_collection_path).document(chunk_id).get()
                if doc.exists:
                    chunks.append(doc.to_dict())
            except Exception as e:
                self.logger.error(f"Failed to get chunk {chunk_id}: {e}")
        return chunks

    def get_dashboard_stats(self) -> Dict[str, Any]:
        docs = self.get_all_documents()
        if not docs:
            return {"total_docs": 0, "total_size_mb": 0, "by_type": pd.DataFrame(), "by_status": {}}
        df = pd.DataFrame(docs)
        return {
            "total_docs": len(df),
            "total_size_mb": df['size'].sum(),
            "by_type": df.groupby('type').size().reset_index(name='count'),
            "by_status": df['status'].value_counts().to_dict()
        }

    def get_document_details(self, doc_id: str) -> Optional[Dict[str, Any]]:
        try:
            doc = self.db.collection(self.doc_collection_path).document(doc_id).get()
            if not doc.exists: return None
            details = doc.to_dict()
            chunk_query = self.db.collection(self.chunk_collection_path).where("document_id", "==", doc_id).limit(1).stream()
            first_chunk = next(chunk_query, None)
            details['content_preview'] = first_chunk.to_dict().get('text', '') if first_chunk else "（プレビューなし）"
            return details
        except Exception as e:
            self.logger.error(f"Failed to get document details for {doc_id}: {e}")
            return None

    def delete_document(self, doc_id: str) -> bool:
        try:
            chunk_query = self.db.collection(self.chunk_collection_path).where("document_id", "==", doc_id).stream()
            chunk_ids = [chunk.id for chunk in chunk_query]
            if chunk_ids:
                self.vector_store.delete_vectors(chunk_ids)
                batch = self.db.batch()
                for chunk_id in chunk_ids:
                    batch.delete(self.db.collection(self.chunk_collection_path).document(chunk_id))
                batch.commit()
            self.db.collection(self.doc_collection_path).document(doc_id).delete()
            self.logger.info(f"Successfully deleted document {doc_id}")
            # BM25インデックスも更新
            self._update_bm25_index()
            return True
        except Exception as e:
            self.logger.error(f"Failed to delete document {doc_id}: {e}")
            st.error(f"ドキュメントの削除に失敗: {e}")
            return False

import streamlit as st
import os
import uuid
from datetime import datetime
import logging
from typing import List, Dict, Any, Optional
import pandas as pd
from google.cloud import firestore
from google.api_core import exceptions

from src.core.document_processor import DocumentProcessor
from src.core.chunk_processor import ChunkProcessor
from src.vector_store.tenant_isolation import TenantVectorStore

class DocumentManager:
    """
    ドキュメントのライフサイクルを管理するクラス
    """

    def __init__(self, tenant_id: str):
        self.logger = logging.getLogger(__name__)
        self.tenant_id = tenant_id
        
        # GCP設定
        self.gcp_project_id = os.getenv("GCP_PROJECT_ID")
        self.gcp_location = os.getenv("GCP_REGION", "asia-northeast1")
        self.gcs_bucket_name = os.getenv("GCS_BUCKET_NAME_FOR_VECTOR_SEARCH")

        if not all([self.gcp_project_id, self.gcs_bucket_name]):
            st.error("GCP設定の環境変数が不足しています。")
            st.stop()

        self.processor = DocumentProcessor()
        self.chunker = ChunkProcessor()
        self.vector_store = TenantVectorStore(tenant_id, self.gcp_project_id, self.gcp_location, self.gcs_bucket_name)
        
        self.temp_dir = f"./temp_{self.tenant_id}"
        os.makedirs(self.temp_dir, exist_ok=True)

        # Firestoreクライアント
        self.db = firestore.Client()
        self.doc_collection_path = f"tenants/{self.tenant_id}/documents"
        self.chunk_collection_path = f"tenants/{self.tenant_id}/chunks"

    def get_all_documents(self, search: str = "", status_filter: str = "すべて") -> List[Dict[str, Any]]:
        try:
            query = self.db.collection(self.doc_collection_path).order_by("uploaded_at", direction=firestore.Query.DESCENDING)
            docs = [doc.to_dict() for doc in query.stream()]
            # TODO: サーバーサイドでのフィルタリングを実装
            if search:
                docs = [d for d in docs if search.lower() in d.get("name", "").lower()]
            if status_filter != "すべて":
                docs = [d for d in docs if d.get("status") == status_filter]
            return docs
        except Exception as e:
            self.logger.error(f"Failed to get documents from Firestore: {e}")
            return []

    def upload_and_process_documents(self, uploaded_files: List[st.runtime.uploaded_file_manager.UploadedFile]):
        # ... (処理はほぼ同じだが、保存先をFirestoreに変更)
        pass

    def _update_doc_status(self, doc_id: str, status: str, details: Dict = None):
        """Firestoreのドキュメントステータスを更新"""
        update_data = {"status": status, "updated_at": datetime.utcnow()}
        if details:
            update_data.update(details)
        self.db.collection(self.doc_collection_path).document(doc_id).update(update_data)

    def get_chunks_by_ids(self, chunk_ids: List[str]) -> List[Dict[str, Any]]:
        """FirestoreからチャンクIDでチャンク情報を取得"""
        chunks = []
        for chunk_id in chunk_ids:
            try:
                doc = self.db.collection(self.chunk_collection_path).document(chunk_id).get()
                if doc.exists:
                    chunks.append(doc.to_dict())
            except Exception as e:
                self.logger.error(f"Failed to get chunk {chunk_id}: {e}")
        return chunks

    # ... (他のメソッドもFirestoreを使うように修正)
