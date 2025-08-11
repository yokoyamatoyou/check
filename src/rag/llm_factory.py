"""
LLMファクトリーモジュール

設定に応じて、複数のLLMプロバイダーのクライアントを初期化し、
指定されたモデルのインスタンスを返す役割を担う。
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
import logging
import os

# 実際のSDK
from openai import OpenAI
import httpx
# from google.cloud import aiplatform
# import anthropic

# --- LLM Client Wrapper Interfaces ---

class BaseLLM(ABC):
    """
    すべてのLLMラッパーの抽象基底クラス
    """
    def __init__(self, api_key: Optional[str] = None, **kwargs):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.api_key = api_key
        if not self.api_key:
            raise ValueError(f"API key for {self.__class__.__name__} is not provided.")
        self.client = self._initialize_client()

    @abstractmethod
    def _initialize_client(self) -> Any:
        """各SDKのクライアントを初期化する"""
        pass

    @abstractmethod
    def invoke(self, messages: List[Dict[str, str]], **kwargs) -> str:
        """プロンプトを実行し、テキスト応答を返す"""
        pass

# --- Concrete LLM Wrappers ---

class OpenAIWrapper(BaseLLM):
    """OpenAIモデル用ラッパー"""
    def _initialize_client(self) -> Any:
        self.logger.info("Initializing OpenAI client with explicit proxy override.")
        # 環境プロキシを無効化して安定化（httpxの推奨）
        http_client = httpx.Client(trust_env=False)
        return OpenAI(api_key=self.api_key, http_client=http_client)

    def invoke(self, messages: List[Dict[str, str]], **kwargs) -> str:
        model = kwargs.get("model", "gpt-4.1-mini")
        self.logger.info(f"Invoking OpenAI model: {model}")
        try:
            response = self.client.chat.completions.create(
                model=model,
                messages=messages,
                max_tokens=kwargs.get("max_tokens", 1024),
                temperature=kwargs.get("temperature", 0.7),
            )
            return response.choices[0].message.content
        except Exception as e:
            self.logger.error(f"OpenAI API call failed: {e}")
            return f"エラー: OpenAI APIの呼び出しに失敗しました。({e})"

class GoogleWrapper(BaseLLM):
    """Google (Vertex AI) モデル用ラッパー (モック)"""
    def _initialize_client(self) -> Any:
        self.logger.info("Initializing Google Vertex AI client (mock).")
        return "MockGoogleClient"

    def invoke(self, messages: List[Dict[str, str]], **kwargs) -> str:
        model = kwargs.get("model", "gemini-2.5-flash")
        return f"[Mock Google Response for {model}]"

class AnthropicWrapper(BaseLLM):
    """Anthropicモデル用ラッパー (モック)"""
    def _initialize_client(self) -> Any:
        self.logger.info("Initializing Anthropic client (mock).")
        return "MockAnthropicClient"

    def invoke(self, messages: List[Dict[str, str]], **kwargs) -> str:
        model = kwargs.get("model", "sonnet-4")
        return f"[Mock Anthropic Response for {model}]"

# --- LLM Factory ---

class LLMFactory:
    """
    LLMモデルのインスタンスを生成するファクトリークラス
    """
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.logger = logging.getLogger(__name__)
        self._providers = {
            "openai": OpenAIWrapper,
            "google": GoogleWrapper,
            "anthropic": AnthropicWrapper
        }
        self._model_to_provider = {
            # OpenAI
            'gpt-4.1': 'openai',
            'gpt-4.1-mini': 'openai',
            'gpt-4.1-nano': 'openai',
            # Google
            'gemini-2.5-pro': 'google',
            'gemini-2.5-flash': 'google',
            # Anthropic
            'opus-4.1': 'anthropic',
            'sonnet-4': 'anthropic',
        }
        self.logger.info("LLMFactory initialized.")

    def get_model(self, model_name: str, **kwargs) -> Optional[BaseLLM]:
        """
        指定されたモデル名に対応するLLMクライアントのインスタンスを返す
        """
        provider_name = self._model_to_provider.get(model_name.lower())
        if not provider_name:
            self.logger.error(f"No provider found for model: {model_name}")
            return None

        provider_class = self._providers.get(provider_name)
        if not provider_class:
            self.logger.error(f"Provider class not found for: {provider_name}")
            return None

        try:
            # 環境変数からAPIキーを取得
            api_key = os.getenv(f"{provider_name.upper()}_API_KEY")
            if not api_key:
                self.logger.warning(f"{provider_name.upper()}_API_KEY not found in environment variables.")
            
            self.logger.info(f"Creating instance for model '{model_name}' using provider '{provider_name}'")
            return provider_class(api_key=api_key)
        except Exception as e:
            self.logger.error(f"Failed to create instance for model {model_name}: {e}")
            return None