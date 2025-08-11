
import pytest
from unittest.mock import patch, MagicMock
import os
from src.rag.llm_factory import LLMFactory, OpenAIWrapper, BaseLLM

# LLMFactoryのテスト
class TestLLMFactory:

    @pytest.fixture
    def factory(self):
        """LLMFactoryのインスタンスを返すフィクスチャ"""
        return LLMFactory()

    def test_initialization(self, factory):
        """ファクトリが正常に初期化されることをテストする"""
        assert factory is not None
        assert 'openai' in factory._providers
        assert 'gpt-4.1-mini' in factory._model_to_provider

    @patch.dict(os.environ, {"OPENAI_API_KEY": "test_key"})
    def test_get_model_success(self, factory):
        """有効なモデル名で正しいラッパーが返されることをテストする"""
        model_instance = factory.get_model('gpt-4.1-mini')
        assert model_instance is not None
        assert isinstance(model_instance, OpenAIWrapper)
        assert model_instance.api_key == "test_key"

    def test_get_model_unknown(self, factory):
        """不明なモデル名でNoneが返されることをテストする"""
        model_instance = factory.get_model('unknown-model')
        assert model_instance is None

    @patch.dict(os.environ, {}, clear=True)
    def test_get_model_no_api_key(self, factory):
        """APIキーがない場合にNoneが返されることをテストする"""
        # LLMFactoryのget_modelは例外をキャッチしてNoneを返すため、Noneであることを確認
        model_instance = factory.get_model('gpt-4.1-mini')
        assert model_instance is None

# OpenAIWrapperのテスト
class TestOpenAIWrapper:

    @patch('src.rag.llm_factory.OpenAI')
    def test_invoke_success(self, mock_openai_class):
        """invokeメソッドが正常に動作し、期待されるレスポンスを返すことをテストする"""
        # OpenAIクライアントとレスポンスをモック
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices[0].message.content = "Mocked OpenAI response"
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai_class.return_value = mock_client

        # ラッパーを初期化
        wrapper = OpenAIWrapper(api_key="test_key")
        
        # メッセージを作成してinvokeを呼び出し
        messages = [{"role": "user", "content": "Hello"}]
        response = wrapper.invoke(messages, model="gpt-4.1-mini")

        # アサーション
        mock_client.chat.completions.create.assert_called_once_with(
            model="gpt-4.1-mini",
            messages=messages,
            max_tokens=1024,       # デフォルト値
            temperature=0.7        # デフォルト値
        )
        assert response == "Mocked OpenAI response"

    @patch('src.rag.llm_factory.OpenAI')
    def test_invoke_api_error(self, mock_openai_class):
        """API呼び出しで例外が発生した場合にエラーメッセージを返すことをテストする"""
        # APIエラーをシミュレート
        mock_client = MagicMock()
        mock_client.chat.completions.create.side_effect = Exception("API connection error")
        mock_openai_class.return_value = mock_client

        wrapper = OpenAIWrapper(api_key="test_key")
        messages = [{"role": "user", "content": "Hello"}]
        response = wrapper.invoke(messages)

        assert "エラー: OpenAI APIの呼び出しに失敗しました。" in response
        assert "API connection error" in response
