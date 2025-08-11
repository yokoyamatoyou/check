
import pytest
from unittest.mock import patch, MagicMock
from src.auth.tenant_manager import TenantManager
from datetime import datetime

@pytest.fixture
def mock_firestore_client():
    """Firestoreクライアントをモック化するフィクスチャ"""
    with patch('src.auth.tenant_manager.firestore.Client') as mock_client_class:
        mock_db = MagicMock()
        mock_collection = MagicMock()
        mock_doc_ref = MagicMock() # ドキュメントリファレンス
        mock_doc_snapshot = MagicMock() # ドキュメントスナップショット (get()の結果)

        mock_client_class.return_value = mock_db
        mock_db.collection.return_value = mock_collection
        mock_collection.document.return_value = mock_doc_ref
        mock_doc_ref.get.return_value = mock_doc_snapshot # get()がスナップショットを返すように設定
        
        yield {
            "db": mock_db,
            "collection": mock_collection,
            "doc_ref": mock_doc_ref,
            "doc_snapshot": mock_doc_snapshot
        }

@pytest.fixture
def tenant_manager(mock_firestore_client):
    """テスト用のTenantManagerインスタンスを返す"""
    return TenantManager()

def test_create_tenant(tenant_manager, mock_firestore_client):
    """create_tenantが正しく動作することをテストする"""
    tenant_data = tenant_manager.create_tenant("Test Tenant", "admin@test.com", "pro")

    assert tenant_data["name"] == "Test Tenant"
    assert tenant_data["plan"] == "pro"
    mock_firestore_client["collection"].document.assert_called_with(tenant_data["tenant_id"])
    mock_firestore_client["doc_ref"].set.assert_called_once()

def test_get_tenant_exists(tenant_manager, mock_firestore_client):
    """存在するテナントIDでget_tenantを呼び出す場合"""
    mock_snapshot = mock_firestore_client["doc_snapshot"]
    mock_snapshot.exists = True
    mock_snapshot.to_dict.return_value = {"tenant_id": "test_id", "name": "Test Tenant"}

    tenant = tenant_manager.get_tenant("test_id")

    assert tenant is not None
    assert tenant["name"] == "Test Tenant"
    mock_firestore_client["collection"].document.assert_called_with("test_id")

def test_get_tenant_not_exists(tenant_manager, mock_firestore_client):
    """存在しないテナントIDでget_tenantを呼び出す場合"""
    mock_snapshot = mock_firestore_client["doc_snapshot"]
    mock_snapshot.exists = False

    tenant = tenant_manager.get_tenant("non_existent_id")

    assert tenant is None

def test_update_tenant_status_success(tenant_manager, mock_firestore_client):
    """テナントのステータス更新が成功することをテストする"""
    result = tenant_manager.update_tenant_status("test_id", "suspended")

    assert result is True
    mock_firestore_client["doc_ref"].update.assert_called_once()
    # updated_atが呼び出しに含まれていることを確認
    update_args = mock_firestore_client["doc_ref"].update.call_args[0][0]
    assert "status" in update_args
    assert update_args["status"] == "suspended"
    assert "updated_at" in update_args

def test_update_tenant_status_invalid(tenant_manager, mock_firestore_client):
    """無効なステータスで更新が失敗することをテストする"""
    result = tenant_manager.update_tenant_status("test_id", "invalid_status")

    assert result is False
    mock_firestore_client["doc_ref"].update.assert_not_called()
