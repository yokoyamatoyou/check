"""
RAGエンジンモジュール
"""
from typing import List, Dict, Any, Optional
import logging
import hashlib
import json
import os
import time
import pickle
from functools import lru_cache
import concurrent.futures
from google.cloud import storage
from rank_bm25 import BM25Okapi

from src.rag.llm_factory import LLMFactory
from src.vector_store.tenant_isolation import TenantVectorStore
from src.core.document_manager import DocumentManager

class RAGEngine:
    """
    RAGのコアロジックを処理するエンジン
    """

    def __init__(self, tenant_id: str, enable_caching: bool = True):
        self.logger = logging.getLogger(__name__)
        self.tenant_id = tenant_id
        self.enable_caching = enable_caching
        
        self.doc_manager = DocumentManager(tenant_id)
        self.vector_store = self.doc_manager.vector_store
        self.llm_factory = LLMFactory()
        self.storage_client = storage.Client()
        self.gcs_bucket_name = os.getenv("GCS_BUCKET_NAME_FOR_VECTOR_SEARCH")
        self.bm25_index_path = f"bm25_indices/{self.tenant_id}/index.pkl"
        self.bm25_index_data = None # BM25インデックスのキャッシュ

        if enable_caching:
            self.cache_dir = f"./rag_cache_{tenant_id}"
            os.makedirs(self.cache_dir, exist_ok=True)

    def _load_bm25_index(self):
        """GCSからBM25インデックスを読み込み、キャッシュする"""
        if self.bm25_index_data:
            return # 既に読み込み済み
        try:
            self.logger.info(f"Loading BM25 index from {self.bm25_index_path}")
            bucket = self.storage_client.bucket(self.gcs_bucket_name)
            blob = bucket.blob(self.bm25_index_path)
            if not blob.exists():
                self.logger.warning("BM25 index not found.")
                self.bm25_index_data = {"bm25": None, "chunk_ids": []}
                return
            
            with blob.open("rb") as f:
                self.bm25_index_data = pickle.load(f)
            self.logger.info("BM25 index loaded successfully.")
        except Exception as e:
            self.logger.error(f"Failed to load BM25 index: {e}", exc_info=True)
            self.bm25_index_data = {"bm25": None, "chunk_ids": []}

    def _hybrid_search(self, query: str, top_k=5, vector_weight=0.7, bm25_weight=0.3) -> List[str]:
        """ベクトル検索とBM25検索を並行して実行し、結果を統合する"""
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            future_vector = executor.submit(self._parallel_vector_search, query)
            future_bm25 = executor.submit(self._bm25_search, query, top_k * 2)

            vector_results = future_vector.result()
            bm25_results = future_bm25.result()

        return self._fuse_results(vector_results, bm25_results, top_k, vector_weight, bm25_weight)

    def _bm25_search(self, query: str, top_k: int) -> List[Dict[str, Any]]:
        if not self.bm25_index_data or not self.bm25_index_data["bm25"]:
            return []
        
        # TODO: 日本語の場合はMeCab等での分かち書きが必要
        tokenized_query = query.split()
        bm25 = self.bm25_index_data["bm25"]
        chunk_ids = self.bm25_index_data["chunk_ids"]
        
        doc_scores = bm25.get_scores(tokenized_query)
        
        scored_chunks = sorted(zip(chunk_ids, doc_scores), key=lambda x: x[1], reverse=True)
        
        return [{"id": chunk_id, "score": score} for chunk_id, score in scored_chunks[:top_k]]

    def _fuse_results(self, vector_results, bm25_results, top_k, vector_weight, bm25_weight) -> List[str]:
        scores = {}
        
        def normalize(results):
            max_score = max(res["score"] for res in results) if results else 1
            if max_score == 0: max_score = 1 # ゼロ除算を避ける
            for res in results:
                res["score"] /= max_score
            return results

        vector_results = normalize(vector_results)
        bm25_results = normalize(bm25_results)

        for res in vector_results:
            scores[res["id"]] = scores.get(res["id"], 0) + res["score"] * vector_weight
        
        for res in bm25_results:
            scores[res["id"]] = scores.get(res["id"], 0) + res["score"] * bm25_weight

        sorted_chunks = sorted(scores.items(), key=lambda item: item[1], reverse=True)
        return [chunk_id for chunk_id, _ in sorted_chunks[:top_k]]

    def query(self, user_query: str, llm_model_name: str = "gpt-5-mini") -> Dict[str, Any]:
        """
        ユーザーの質問に対してRAGを実行する（ハイブリッド検索版）
        """
        start_time = time.time()
        self.logger.info(f"Executing RAG query for tenant {self.tenant_id}: '{user_query[:50]}...'")

        # キャッシュチェック
        if self.enable_caching:
            cache_key = self._generate_cache_key(user_query, llm_model_name)
            cached_result = self._get_cached_result(cache_key)
            if cached_result:
                self.logger.info(f"Using cached RAG result for query: {user_query[:30]}...")
                cached_result['metadata']['response_time'] = time.time() - start_time
                return cached_result

        # 1. BM25インデックスをロード
        self._load_bm25_index()

        # 2. ハイブリッド検索で関連チャンクのIDを取得
        retrieved_chunk_ids = self._hybrid_search(user_query)
        self.logger.info(f"Retrieved {len(retrieved_chunk_ids)} chunks from hybrid search.")

        if not retrieved_chunk_ids:
            return {"answer": "関連する情報が見つかりませんでした。", "context": [], "metadata": {"response_time": time.time() - start_time}}

        # 3. IDからチャンクの内容を取得（並列処理）
        retrieved_chunks = self._parallel_chunk_retrieval(retrieved_chunk_ids)
        context_str = self._construct_context(retrieved_chunks)

        # 4. LLMへのプロンプトを作成
        prompt_messages = self._construct_prompt_messages(user_query, context_str)

        # 5. LLMに問い合わせ
        llm = self.llm_factory.get_model(llm_model_name)
        answer = llm.invoke(prompt_messages)

        result = {
            "answer": answer,
            "context": retrieved_chunks,
            "metadata": {
                "retrieved_chunk_ids": retrieved_chunk_ids,
                "llm_model_used": llm_model_name,
                "response_time": time.time() - start_time,
            }
        }

        # 6. キャッシュに保存
        if self.enable_caching:
            self._cache_result(cache_key, result)

        return result

    def _parallel_vector_search(self, query: str) -> List[Dict[str, Any]]:
        """並列処理によるベクトル検索"""
        try:
            # 複数の検索戦略を並列実行
            with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                futures = {
                    executor.submit(self.vector_store.search, query, 5): "default",
                    executor.submit(self.vector_store.search, query, 3): "focused",
                    executor.submit(self.vector_store.search, query, 7): "broad"
                }
                
                results = []
                for future in concurrent.futures.as_completed(futures, timeout=10):
                    try:
                        search_result = future.result()
                        results.extend(search_result)
                    except Exception as e:
                        self.logger.warning(f"Vector search failed: {e}")
                
                # 重複除去とスコアによるソート
                unique_results = self._deduplicate_results(results)
                return unique_results[:5]  # 上位5件を返す
                
        except Exception as e:
            self.logger.error(f"Parallel vector search failed: {e}")
            return self.vector_store.search(query, num_neighbors=5)

    def _parallel_chunk_retrieval(self, chunk_ids: List[str]) -> List[Dict[str, Any]]:
        """並列処理によるチャンク取得"""
        if not chunk_ids:
            return []
        
        try:
            with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                # チャンクIDをバッチに分割
                batch_size = max(1, len(chunk_ids) // self.max_workers)
                batches = [chunk_ids[i:i + batch_size] for i in range(0, len(chunk_ids), batch_size)]
                
                futures = [executor.submit(self.doc_manager.get_chunks_by_ids, batch) for batch in batches]
                
                all_chunks = []
                for future in concurrent.futures.as_completed(futures, timeout=15):
                    try:
                        chunks = future.result()
                        all_chunks.extend(chunks)
                    except Exception as e:
                        self.logger.warning(f"Chunk retrieval failed: {e}")
                
                return all_chunks
                
        except Exception as e:
            self.logger.error(f"Parallel chunk retrieval failed: {e}")
            return self.doc_manager.get_chunks_by_ids(chunk_ids)

    def _deduplicate_results(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """検索結果の重複除去"""
        seen_ids = set()
        unique_results = []
        
        for result in results:
            if result.get("id") not in seen_ids:
                seen_ids.add(result.get("id"))
                unique_results.append(result)
        
        # スコアでソート
        return sorted(unique_results, key=lambda x: x.get("score", 0), reverse=True)

    def _generate_cache_key(self, query: str, model_name: str) -> str:
        """キャッシュキーの生成"""
        key_data = f"{self.tenant_id}_{query}_{model_name}"
        return hashlib.sha256(key_data.encode()).hexdigest()

    def _get_cached_result(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """キャッシュから結果を取得"""
        if not self.enable_caching:
            return None
        
        cache_file = os.path.join(self.cache_dir, f"{cache_key}.json")
        if os.path.exists(cache_file):
            try:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                self.logger.warning(f"Failed to load cache: {e}")
        
        return None

    def _cache_result(self, cache_key: str, result: Dict[str, Any]) -> None:
        """結果をキャッシュに保存"""
        if not self.enable_caching:
            return
        
        cache_file = os.path.join(self.cache_dir, f"{cache_key}.json")
        try:
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
        except Exception as e:
            self.logger.warning(f"Failed to save cache: {e}")

    def _construct_context(self, chunks: List[Dict[str, Any]]) -> str:
        """検索結果のチャンクからLLMに渡すコンテキスト文字列を構築する（最適化版）"""
        if not chunks:
            return ""
        
        context_lines = []
        for i, chunk in enumerate(chunks[:5]):  # 最大5チャンクまで
            file_name = chunk["metadata"].get("file_name", "不明なファイル")
            chunk_num = chunk["metadata"].get("chunk_number", "?")
            confidence = chunk["metadata"].get("confidence", 0)
            
            context_lines.append(f"--- ファイル名: {file_name} (チャンク {chunk_num}, 信頼度: {confidence:.2f}) ---")
            context_lines.append(chunk["text"][:1000])  # 最大1000文字まで
        
        return "\n\n".join(context_lines)

    def _construct_prompt_messages(self, query: str, context: str) -> List[Dict[str, str]]:
        """LLMに渡す最終的なプロンプトメッセージリストを構築する（最適化版）"""
        system_prompt = f"""
        あなたは優秀なAIアシスタントです。
        以下の参考情報に基づいて、ユーザーの質問に日本語で回答してください。
        
        回答のガイドライン:
        1. 参考情報に含まれる事実のみに基づいて回答する
        2. 推測や一般的な知識で補完しない
        3. 参考情報に答えがない場合は、その旨を明確に伝える
        4. 回答は簡潔で分かりやすくする
        5. 必要に応じて参考情報の出典を明記する
        """
        
        user_prompt = f"""
        --- 参考情報 ---
        {context}
        
        --- 質問 ---
        {query}
        """

        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]