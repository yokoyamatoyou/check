
import pytest
from unittest.mock import patch, MagicMock
from src.admin.tenant_admin import TenantAdmin

@pytest.fixture
def mock_tenant_manager():
    """TenantManagerをモック化するフィクスチャ"""
    with patch('src.admin.tenant_admin.TenantManager') as mock_manager_class:
        mock_instance = MagicMock()
        mock_manager_class.return_value = mock_instance
        yield mock_instance

@pytest.fixture
def tenant_admin(mock_tenant_manager):
    """テスト用のTenantAdminインスタンスを返す"""
    return TenantAdmin()

class TestTenantAdmin:

    def test_create_tenant(self, tenant_admin, mock_tenant_manager):
        """テナント作成がTenantManagerに正しく委譲されるか"""
        tenant_admin.create_tenant("NewCo", "ceo@newco.com", "enterprise")
        mock_tenant_manager.create_tenant.assert_called_once_with("NewCo", "ceo@newco.com", "enterprise")

    def test_list_tenants_no_filter(self, tenant_admin, mock_tenant_manager):
        """フィルタなしでテナント一覧が取得されるか"""
        mock_tenant_manager.list_tenants.return_value = [{"name": "A"}, {"name": "B"}]
        tenants = tenant_admin.list_tenants()
        assert len(tenants) == 2
        mock_tenant_manager.list_tenants.assert_called_once()

    def test_list_tenants_with_filters(self, tenant_admin, mock_tenant_manager):
        """複数のフィルタが正しく適用されるか"""
        mock_tenants = [
            {"name": "Tenant A", "admin_email": "a@test.com", "plan": "pro", "status": "active"},
            {"name": "Tenant B", "admin_email": "b@test.com", "plan": "free", "status": "suspended"},
            {"name": "Tenant C", "admin_email": "c@test.com", "plan": "pro", "status": "active"},
            {"name": "Search Me", "admin_email": "d@test.com", "plan": "pro", "status": "active"},
        ]
        mock_tenant_manager.list_tenants.return_value = mock_tenants

        # ステータスとプランでフィルタ
        filtered = tenant_admin.list_tenants(status="active", plan="pro")
        assert len(filtered) == 3

        # さらに検索キーワードでフィルタ
        filtered = tenant_admin.list_tenants(status="active", plan="pro", search="Search")
        assert len(filtered) == 1
        assert filtered[0]["name"] == "Search Me"

    def test_suspend_tenant(self, tenant_admin, mock_tenant_manager):
        """テナントの一時停止"""
        tenant_admin.suspend_tenant("tenant123")
        mock_tenant_manager.update_tenant_status.assert_called_once_with("tenant123", "suspended")

    def test_activate_tenant(self, tenant_admin, mock_tenant_manager):
        """テナントの有効化"""
        tenant_admin.activate_tenant("tenant123")
        mock_tenant_manager.update_tenant_status.assert_called_once_with("tenant123", "active")

    def test_delete_tenant(self, tenant_admin, mock_tenant_manager):
        """テナントの削除"""
        tenant_admin.delete_tenant("tenant123")
        mock_tenant_manager.update_tenant_status.assert_called_once_with("tenant123", "deleted")
