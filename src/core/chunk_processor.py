from typing import List, Dict, Any
import logging
import uuid
from src.core.embedding_client import EmbeddingClient

class ChunkProcessor:
    """
    テキストを意味のあるチャンクに分割し、ベクトル化してメタデータを付与するクラス。
    """
    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 200):
        """
        Args:
            chunk_size: 各チャンクの最大サイズ（文字数）。
            chunk_overlap: チャンク間のオーバーラップ（文字数）。
        """
        self.logger = logging.getLogger(__name__)
        if chunk_overlap >= chunk_size:
            raise ValueError("chunk_overlapはchunk_sizeより小さくする必要があります。")
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.embedding_client = EmbeddingClient()
        self.logger.info(f"ChunkProcessor initialized with chunk_size={chunk_size}, chunk_overlap={chunk_overlap}")

    def process_and_embed_chunks(self, text: str, metadata: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        テキストをチャンクに分割し、各チャンクをベクトル化してメタデータを付与する。

        Args:
            text: 分割対象のテキスト。
            metadata: ドキュメント全体のメタデータ。

        Returns:
            ベクトル化されたチャンク情報のリスト。
            各チャンクは以下の形式の辞書:
            {
                "id": str,            # チャンクの一意なID
                "text": str,          # チャンクのテキスト
                "embedding": List[float], # テキストのベクトル
                "metadata": Dict      # チャンクのメタデータ
            }
        """
        if not text:
            self.logger.warning("Input text is empty. No chunks will be created.")
            return []

        # 1. テキストをチャンクに分割
        text_chunks = self._recursive_split(text)
        if not text_chunks:
            return []

        # 2. チャンクをまとめてベクトル化
        self.logger.info(f"Embedding {len(text_chunks)} chunks...")
        embeddings = self.embedding_client.get_embeddings(text_chunks)
        self.logger.info("Embedding complete.")

        # 3. 各チャンクにID、メタデータ、ベクトルを付与
        processed_chunks = []
        doc_id = metadata.get("doc_id", str(uuid.uuid4()))

        for i, (chunk_text, embedding) in enumerate(zip(text_chunks, embeddings)):
            chunk_id = f"{doc_id}_{i}"
            chunk_metadata = metadata.copy()
            chunk_metadata.update({
                "chunk_id": chunk_id,
                "chunk_number": i + 1,
                "total_chunks": len(text_chunks),
            })
            
            processed_chunks.append({
                "id": chunk_id,
                "text": chunk_text,
                "embedding": embedding,
                "metadata": chunk_metadata
            })
            
        self.logger.info(f"Created and embedded {len(processed_chunks)} chunks.")
        return processed_chunks

    def _recursive_split(self, text: str) -> List[str]:
        """
        テキストを指定されたサイズとオーバーラップで分割する。
        """
        chunks = []
        start_index = 0
        while start_index < len(text):
            end_index = start_index + self.chunk_size
            chunks.append(text[start_index:end_index])
            start_index += self.chunk_size - self.chunk_overlap
            if start_index >= len(text):
                break
        return chunks