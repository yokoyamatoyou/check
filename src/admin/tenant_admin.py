"""
テナント管理モジュール (管理者向け)
"""
from src.auth.tenant_manager import TenantManager
from typing import List, Dict, Optional
import logging

class TenantAdmin:
    """
    テナント管理クラス
    """
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.tenant_manager = TenantManager()

    def create_tenant(self, tenant_name: str, admin_email: str, plan: str) -> Dict:
        """
        新規テナント作成
        """
        self.logger.info(f"Attempting to create tenant: {tenant_name}")
        return self.tenant_manager.create_tenant(tenant_name, admin_email, plan)

    def list_tenants(self, status: str = "すべて", plan: str = "すべて", search: str = "") -> List[Dict]:
        """
        テナント一覧をフィルタリングして取得
        """
        try:
            all_tenants = self.tenant_manager.list_tenants()
            
            # サーバーサイドでのフィルタリング
            if status != "すべて":
                all_tenants = [t for t in all_tenants if t.get("status") == status]
            
            if plan != "すべて":
                all_tenants = [t for t in all_tenants if t.get("plan") == plan]

            if search:
                search_lower = search.lower()
                all_tenants = [t for t in all_tenants if search_lower in t.get("name", "").lower() or search_lower in t.get("admin_email", "").lower()]

            return all_tenants
        except Exception as e:
            self.logger.error(f"Failed to list tenants: {e}")
            return []

    def suspend_tenant(self, tenant_id: str) -> bool:
        """
        テナントを一時停止
        """
        self.logger.info(f"Suspending tenant: {tenant_id}")
        return self.tenant_manager.update_tenant_status(tenant_id, "suspended")

    def activate_tenant(self, tenant_id: str) -> bool:
        """
        テナントを有効化
        """
        self.logger.info(f"Activating tenant: {tenant_id}")
        return self.tenant_manager.update_tenant_status(tenant_id, "active")

    def delete_tenant(self, tenant_id: str) -> bool:
        """
        テナントを削除（論理削除）
        """
        self.logger.warning(f"Deleting tenant (logical): {tenant_id}")
        return self.tenant_manager.update_tenant_status(tenant_id, "deleted")