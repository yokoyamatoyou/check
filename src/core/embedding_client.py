"""
テキスト埋め込み（Embedding）クライアントモジュール
"""
from typing import List, Dict, Any
import logging
import os
from openai import OpenAI

class EmbeddingClient:
    """
    テキストをベクトル化するためのクライアント
    """
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        if not self.openai_api_key:
            raise ValueError("OPENAI_API_KEY is not set in environment variables.")
        self.client = OpenAI(api_key=self.openai_api_key)
        # AGENT.mdの指定に基づき、モデル名と次元数を設定
        self.primary_model = "text-embedding-3-small"
        self.primary_dimensions = 1536
        self.logger.info(f"EmbeddingClient initialized with model: {self.primary_model}")

    def get_embedding(self, text: str) -> List[float]:
        """
        単一のテキストをベクトル化する

        Args:
            text: ベクトル化するテキスト

        Returns:
            ベクトルデータ
        """
        text = text.replace("\n", " ")
        try:
            response = self.client.embeddings.create(input=[text], model=self.primary_model)
            return response.data[0].embedding
        except Exception as e:
            self.logger.error(f"Failed to get embedding: {e}")
            raise

    def get_embeddings(self, texts: List[str]) -> List[List[float]]:
        """
        複数のテキストを一度にベクトル化する

        Args:
            texts: ベクトル化するテキストのリスト

        Returns:
            ベクトルデータのリスト
        """
        try:
            response = self.client.embeddings.create(input=texts, model=self.primary_model)
            return [data.embedding for data in response.data]
        except Exception as e:
            self.logger.error(f"Failed to get embeddings: {e}")
            raise
