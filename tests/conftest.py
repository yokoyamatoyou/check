"""
pytest設定ファイル
テスト環境でのStreamlit干渉を防ぐ
"""
import os
import sys
import pytest
from unittest.mock import patch, MagicMock

# テスト環境であることを示す環境変数を設定
os.environ['TESTING'] = 'true'
os.environ['STREAMLIT_SERVER_HEADLESS'] = 'true'

@pytest.fixture(autouse=True)
def mock_streamlit():
    """Streamlitの自動モック"""
    with patch.dict('os.environ', {
        'STREAMLIT_SERVER_HEADLESS': 'true',
        'STREAMLIT_SERVER_RUN_ON_SAVE': 'false',
        'STREAMLIT_SERVER_PORT': '8501',
        'STREAMLIT_SERVER_ADDRESS': 'localhost'
    }):
        yield

@pytest.fixture(autouse=True)
def disable_streamlit_logging():
    """Streamlitのログ出力を無効化"""
    import logging
    logging.getLogger('streamlit').setLevel(logging.ERROR)
    logging.getLogger('streamlit.runtime').setLevel(logging.ERROR)
    logging.getLogger('streamlit.runtime.scriptrunner').setLevel(logging.ERROR)

@pytest.fixture(autouse=True)
def mock_external_apis():
    """外部APIのモック"""
    # OpenAI
    try:
        with patch('openai.OpenAI') as mock_openai:
            mock_client = mock_openai.return_value
            mock_client.embeddings.create.return_value.data = [type('obj', (object,), {'embedding': [0.1] * 1536})()]
            mock_client.chat.completions.create.return_value.choices = [type('obj', (object,), {'message': type('obj', (object,), {'content': 'Test response'})()})()]
    except Exception:
        pass
    
    # Anthropic
    try:
        with patch('anthropic.Anthropic') as mock_anthropic:
            mock_client = mock_anthropic.return_value
            mock_client.messages.create.return_value.content = [type('obj', (object,), {'text': 'Test response'})()]
    except Exception:
        pass
    
    # Google Generative AI
    try:
        with patch('google.generativeai.GenerativeModel') as mock_genai:
            mock_model = mock_genai.return_value
            mock_model.generate_content.return_value.text = 'Test response'
            mock_model.embed_content.return_value.embedding = [0.1] * 1536
    except Exception:
        pass
    
    # Google Cloud
    try:
        with patch('google.cloud.firestore.Client') as mock_firestore, \
             patch('google.cloud.storage.Client') as mock_storage:
            pass
    except Exception:
        pass
    
    yield
