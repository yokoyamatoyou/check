import pytest
from unittest.mock import patch, MagicMock
from src.rag.rag_engine import RAGEngine

@pytest.fixture
def mock_dependencies():
    """RAGEngineの依存関係をモック化するフィクスチャ"""
    # Python 3.10+ の構文に修正
    with patch('src.rag.rag_engine.DocumentManager') as mock_doc_manager_class, \
         patch('src.rag.rag_engine.LLMFactory') as mock_llm_factory_class:
        
        mock_doc_manager = MagicMock()
        mock_vector_store = MagicMock()
        mock_doc_manager.vector_store = mock_vector_store
        mock_doc_manager_class.return_value = mock_doc_manager

        mock_llm_factory = MagicMock()
        mock_llm_model = MagicMock()
        mock_llm_factory.get_model.return_value = mock_llm_model
        mock_llm_factory_class.return_value = mock_llm_factory

        yield {
            "doc_manager": mock_doc_manager,
            "vector_store": mock_vector_store,
            "llm_factory": mock_llm_factory,
            "llm_model": mock_llm_model
        }

@pytest.fixture
def rag_engine(mock_dependencies):
    """テスト用のRAGEngineインスタンスを返す"""
    return RAGEngine(tenant_id="test_tenant")

def test_query_success(rag_engine, mock_dependencies):
    """正常なRAGクエリが成功することをテストする"""
    mock_dependencies["vector_store"].search.return_value = [{"id": "chunk1"}, {"id": "chunk2"}]
    mock_dependencies["doc_manager"].get_chunks_by_ids.return_value = [
        {"text": "chunk one text", "metadata": {"file_name": "doc1.pdf", "chunk_number": 1}},
        {"text": "chunk two text", "metadata": {"file_name": "doc2.txt", "chunk_number": 5}}
    ]
    mock_dependencies["llm_model"].invoke.return_value = "This is the final answer."

    result = rag_engine.query("What is RAG?")

    assert result["answer"] == "This is the final answer."
    assert len(result["context"]) == 2
    mock_dependencies["vector_store"].search.assert_called_once_with(query="What is RAG?", num_neighbors=5)
    mock_dependencies["doc_manager"].get_chunks_by_ids.assert_called_once_with(["chunk1", "chunk2"])
    mock_dependencies["llm_model"].invoke.assert_called_once()

def test_query_no_retrieved_chunks(rag_engine, mock_dependencies):
    """ベクトル検索でチャンクが見つからなかった場合の動作をテストする"""
    mock_dependencies["vector_store"].search.return_value = []
    result = rag_engine.query("An obscure query")
    assert result["answer"] == "関連する情報が見つかりませんでした。"
    assert not result["context"]
    mock_dependencies["doc_manager"].get_chunks_by_ids.assert_not_called()

def test_query_llm_initialization_fails(rag_engine, mock_dependencies):
    """LLMの初期化に失敗した場合の動作をテストする"""
    mock_dependencies["vector_store"].search.return_value = [{"id": "chunk1"}]
    mock_dependencies["doc_manager"].get_chunks_by_ids.return_value = [{"text": "some text", "metadata": {}}]
    mock_dependencies["llm_factory"].get_model.return_value = None
    result = rag_engine.query("A valid query")
    assert result["answer"] == "LLMの初期化に失敗しました。"
    mock_dependencies["llm_model"].invoke.assert_not_called()