
セマンティックチャンキングとメタデータ生成
AIエージェントへの指示：
1. LangChainのSemanticChunkerを使用
2. チャンクごとにGPT-4o-miniでメタデータ生成
3. 重複検出のためのハッシュ計算
"
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_experimental.text_splitter import SemanticChunker
from langchain_openai import OpenAIEmbeddings
import hashlib
from typing import List, Dict
import openai
import os
import json
import logging
from src.config import Config

class ChunkProcessor:
    def __init__(self, use_semantic: bool = True):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.use_semantic = use_semantic
        
        if use_semantic:
            # セマンティックチャンカーの初期化
            embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
            self.splitter = SemanticChunker(
                embeddings=embeddings,
                breakpoint_threshold_type="percentile",
                breakpoint_threshold_amount=90
            )
        else:
            # 通常のテキスト分割
            self.splitter = RecursiveCharacterTextSplitter(
                chunk_size=1000,
                chunk_overlap=200,
                separators=["\n\n", "\n", "。", ".", " ", ""]
            )
    
    def process_chunks(self, text: str, source_metadata: Dict) -> List[Dict]:
        """
        テキストをチャンク化し、メタデータを生成
        
        Returns:
            List[Dict]: 各チャンクに以下を含む
            - content: チャンクテキスト
            - metadata: 自動生成されたメタデータ
            - embedding: ベクトル（後で生成）
            - hash: コンテンツハッシュ
        """
        if self.use_semantic:
            chunks = self.splitter.create_documents([text])
        else:
            chunks = self.splitter.create_documents([text])

        processed_chunks = []
        for i, chunk in enumerate(chunks):
            chunk_text = chunk.page_content
            chunk_hash = hashlib.sha256(chunk_text.encode('utf-8')).hexdigest()
            
            # メタデータ生成
            generated_metadata = self.generate_metadata(chunk_text)
            
            # 元のメタデータと結合
            combined_metadata = {**source_metadata, **generated_metadata}
            combined_metadata["chunk_id"] = f"{combined_metadata.get("source_file", "unknown")}_{chunk_hash}_{i}"

            processed_chunks.append({
                "content": chunk_text,
                "metadata": combined_metadata,
                "hash": chunk_hash
            })
        return processed_chunks
    
    def generate_metadata(self, chunk_text: str) -> Dict:
        """
        GPT-4o-miniを使用してメタデータを自動生成
        
        生成項目:
        - summary: 要約（50文字以内）
        - keywords: キーワード（最大5個）
        - category: カテゴリ分類
        - entities: 固有名詞の抽出
        - importance_score: 重要度スコア（1-10）
        """
        prompt = f"""
        以下のテキストから構造化されたメタデータを生成してください。
        
        テキスト: {chunk_text[:500]}
        
        JSON形式で以下を出力:
        - summary: 簡潔な要約
        - keywords: 主要キーワード（配列）
        - category: カテゴリ（技術文書/議事録/仕様書/その他）
        - entities: 固有名詞（人名、組織名、製品名等）
        - importance_score: 1-10の重要度
        """
        
        try:
            client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY")) # 環境変数からAPIキーを取得
            response = client.chat.completions.create(
                model="gpt-4o-mini", # または Config.METADATA_GENERATION_MODEL
                response_format={ "type": "json_object" },
                messages=[
                    {"role": "system", "content": "あなたはテキストから構造化されたメタデータを生成するアシスタントです。"},
                    {"role": "user", "content": prompt}
                ]
            )
            metadata = json.loads(response.choices[0].message.content)
            # バリデーション（簡易的な例）
            if not all(k in metadata for k in ["summary", "keywords", "category", "entities", "importance_score"]):
                raise ValueError("生成されたメタデータが不正です。")
            return metadata
        except Exception as e:
            self.logger.error(f"メタデータ生成中にエラーが発生しました: {e}")
            return {
                "summary": chunk_text[:50] + "...",
                "keywords": [],
                "category": "その他",
                "entities": [],
                "importance_score": 5
            }

