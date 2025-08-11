"""
設定管理モジュール
"""
import os
from typing import Dict, Any, Optional
import logging

class Config:
    """アプリケーション設定管理クラス"""
    
    # 基本設定
    APP_NAME = "Enterprise RAG System"
    VERSION = "1.0.0"
    DEBUG = os.getenv("DEBUG", "false").lower() == "true"
    
    # GCP設定
    GCP_PROJECT_ID = os.getenv("GCP_PROJECT_ID")
    GCP_REGION = os.getenv("GCP_REGION", "asia-northeast2")
    GCS_BUCKET_NAME = os.getenv("GCS_BUCKET_NAME_FOR_VECTOR_SEARCH")
    
    # パフォーマンス設定
    ENABLE_CACHING = os.getenv("ENABLE_CACHING", "true").lower() == "true"
    MAX_WORKERS = int(os.getenv("MAX_WORKERS", "3"))
    CACHE_TTL = int(os.getenv("CACHE_TTL", "3600"))  # 1時間
    
    # RAG設定
    VECTOR_DIMENSION = int(os.getenv("VECTOR_DIMENSION", "1536"))
    CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "1000"))
    CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "200"))
    MAX_CHUNKS_PER_QUERY = int(os.getenv("MAX_CHUNKS_PER_QUERY", "5"))
    
    # OCR設定
    OCR_PREFERRED = os.getenv("OCR_PREFERRED", "cloud_vision")
    OCR_FALLBACK = os.getenv("OCR_FALLBACK", "easyocr")
    OCR_CONFIDENCE_THRESHOLD = float(os.getenv("OCR_CONFIDENCE_THRESHOLD", "0.8"))
    
    # LLM設定
    DEFAULT_LLM_MODEL = os.getenv("DEFAULT_LLM_MODEL", "gpt-4o-mini")
    LLM_TIMEOUT = int(os.getenv("LLM_TIMEOUT", "30"))
    
    # セキュリティ設定
    ENABLE_MFA = os.getenv("ENABLE_MFA", "true").lower() == "true"
    SESSION_TIMEOUT = int(os.getenv("SESSION_TIMEOUT", "3600"))
    
    # ログ設定
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    ENABLE_STRUCTURED_LOGGING = os.getenv("ENABLE_STRUCTURED_LOGGING", "true").lower() == "true"
    
    # パフォーマンス最適化設定
    ENABLE_PARALLEL_PROCESSING = os.getenv("ENABLE_PARALLEL_PROCESSING", "true").lower() == "true"
    ENABLE_BATCH_PROCESSING = os.getenv("ENABLE_BATCH_PROCESSING", "true").lower() == "true"
    BATCH_SIZE = int(os.getenv("BATCH_SIZE", "10"))
    
    # キャッシュ設定
    CACHE_DIR = os.getenv("CACHE_DIR", "./cache")
    MAX_CACHE_SIZE = int(os.getenv("MAX_CACHE_SIZE", "1000"))  # MB
    
    # 監視設定
    ENABLE_METRICS = os.getenv("ENABLE_METRICS", "true").lower() == "true"
    METRICS_INTERVAL = int(os.getenv("METRICS_INTERVAL", "60"))  # 秒
    
    @classmethod
    def get_performance_config(cls) -> Dict[str, Any]:
        """パフォーマンス関連の設定を取得"""
        return {
            "enable_caching": cls.ENABLE_CACHING,
            "max_workers": cls.MAX_WORKERS,
            "cache_ttl": cls.CACHE_TTL,
            "enable_parallel_processing": cls.ENABLE_PARALLEL_PROCESSING,
            "enable_batch_processing": cls.ENABLE_BATCH_PROCESSING,
            "batch_size": cls.BATCH_SIZE,
            "max_chunks_per_query": cls.MAX_CHUNKS_PER_QUERY,
            "llm_timeout": cls.LLM_TIMEOUT
        }
    
    @classmethod
    def get_rag_config(cls) -> Dict[str, Any]:
        """RAG関連の設定を取得"""
        return {
            "vector_dimension": cls.VECTOR_DIMENSION,
            "chunk_size": cls.CHUNK_SIZE,
            "chunk_overlap": cls.CHUNK_OVERLAP,
            "max_chunks_per_query": cls.MAX_CHUNKS_PER_QUERY,
            "default_llm_model": cls.DEFAULT_LLM_MODEL
        }
    
    @classmethod
    def get_ocr_config(cls) -> Dict[str, Any]:
        """OCR関連の設定を取得"""
        return {
            "preferred": cls.OCR_PREFERRED,
            "fallback": cls.OCR_FALLBACK,
            "confidence_threshold": cls.OCR_CONFIDENCE_THRESHOLD
        }
    
    @classmethod
    def validate_config(cls) -> bool:
        """設定の妥当性を検証"""
        required_vars = [
            "GCP_PROJECT_ID",
            "GCS_BUCKET_NAME"
        ]
        
        missing_vars = []
        for var in required_vars:
            if not getattr(cls, var):
                missing_vars.append(var)
        
        if missing_vars:
            logging.error(f"Missing required environment variables: {missing_vars}")
            return False
        
        return True
    
    @classmethod
    def get_cache_config(cls) -> Dict[str, Any]:
        """キャッシュ関連の設定を取得"""
        return {
            "enable_caching": cls.ENABLE_CACHING,
            "cache_dir": cls.CACHE_DIR,
            "max_cache_size": cls.MAX_CACHE_SIZE,
            "cache_ttl": cls.CACHE_TTL
        }