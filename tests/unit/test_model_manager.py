
import pytest
from unittest.mock import patch, MagicMock
from src.admin.model_manager import ModelManager

@pytest.fixture
def mock_firestore_client():
    """Firestoreクライアントと関連オブジェクトをモック化する"""
    with patch('src.admin.model_manager.firestore.Client') as mock_client_class:
        mock_db = MagicMock()
        mock_doc_ref = MagicMock()
        mock_doc_snapshot = MagicMock()

        mock_client_class.return_value = mock_db
        mock_db.collection.return_value.document.return_value = mock_doc_ref
        mock_doc_ref.get.return_value = mock_doc_snapshot

        yield {
            "db": mock_db,
            "doc_ref": mock_doc_ref,
            "doc_snapshot": mock_doc_snapshot
        }

@pytest.fixture
def model_manager(mock_firestore_client):
    """テスト用のModelManagerインスタンスを返す"""
    return ModelManager()

class TestModelManager:

    def test_save_configuration(self, model_manager, mock_firestore_client):
        """設定の保存が正しく行われるかテストする"""
        mock_doc_ref = mock_firestore_client["doc_ref"]
        test_config = {"openai": {"api_key": "test_key"}}
        
        result = model_manager.save_configuration(test_config)

        assert result is True
        mock_doc_ref.set.assert_called_once_with(test_config, merge=True)

    def test_get_configuration_success(self, model_manager, mock_firestore_client):
        """設定の取得が成功するケースをテストする"""
        mock_snapshot = mock_firestore_client["doc_snapshot"]
        mock_snapshot.exists = True
        expected_config = {"google": {"project_id": "test_project"}}
        mock_snapshot.to_dict.return_value = expected_config

        config = model_manager.get_configuration()

        assert config == expected_config
        mock_firestore_client["doc_ref"].get.assert_called_once()

    def test_get_configuration_not_found(self, model_manager, mock_firestore_client):
        """設定ドキュメントが存在しないケースをテストする"""
        mock_snapshot = mock_firestore_client["doc_snapshot"]
        mock_snapshot.exists = False

        config = model_manager.get_configuration()

        assert config is None

    def test_save_configuration_failure(self, model_manager, mock_firestore_client):
        """設定の保存が失敗するケースをテストする"""
        mock_doc_ref = mock_firestore_client["doc_ref"]
        mock_doc_ref.set.side_effect = Exception("Firestore Error")
        test_config = {"openai": {"api_key": "test_key"}}

        result = model_manager.save_configuration(test_config)

        assert result is False

    def test_get_configuration_failure(self, model_manager, mock_firestore_client):
        """設定の取得が失敗するケースをテストする"""
        mock_doc_ref = mock_firestore_client["doc_ref"]
        mock_doc_ref.get.side_effect = Exception("Firestore Error")

        config = model_manager.get_configuration()

        assert config is None
