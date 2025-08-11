"""
マルチテナント管理モジュール
Firestoreを利用してテナント情報を管理する
"""
from typing import Dict, List, Optional, Any
from google.cloud import firestore
import uuid
from datetime import datetime
import logging

class TenantManager:
    """
    マルチテナント管理クラス (Firestore版)
    """
    
    def __init__(self):
        self.db = firestore.Client()
        self.logger = logging.getLogger(__name__)
        self.collection_name = "tenants"

    def create_tenant(self, 
                     tenant_name: str,
                     admin_email: str,
                     plan: str = "free") -> Dict:
        """
        新規テナント作成
        """
        tenant_id = str(uuid.uuid4())
        
        tenant_data = {
            "tenant_id": tenant_id,
            "name": tenant_name,
            "admin_email": admin_email,
            "plan": plan,
            "status": "active",
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "settings": {
                "max_documents": self._get_plan_limit(plan, "documents"),
                "max_users": self._get_plan_limit(plan, "users"),
                "max_api_calls": self._get_plan_limit(plan, "api_calls"),
                "enabled_models": self._get_plan_models(plan)
            },
            "usage": {
                "documents": 0,
                "users": 1,
                "api_calls": 0,
                "storage_gb": 0
            }
        }
        
        self.db.collection(self.collection_name).document(tenant_id).set(tenant_data)
        self.logger.info(f"Tenant created in Firestore: {tenant_id}")
        
        # TODO: Vector Searchインデックス作成やGCSバケット作成のトリガー
        
        return tenant_data
    
    def get_tenant(self, tenant_id: str) -> Optional[Dict]:
        """テナント情報取得"""
        doc = self.db.collection(self.collection_name).document(tenant_id).get()
        return doc.to_dict() if doc.exists else None

    def list_tenants(self) -> List[Dict]:
        """全テナントの一覧を取得"""
        tenants = []
        docs = self.db.collection(self.collection_name).stream()
        for doc in docs:
            tenants.append(doc.to_dict())
        return tenants

    def update_tenant_status(self, tenant_id: str, status: str) -> bool:
        """テナントのステータスを更新"""
        if status not in ["active", "suspended", "deleted"]:
            self.logger.error(f"Invalid status: {status}")
            return False
        try:
            self.db.collection(self.collection_name).document(tenant_id).update({
                "status": status,
                "updated_at": datetime.utcnow()
            })
            self.logger.info(f"Tenant {tenant_id} status updated to {status}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to update tenant status for {tenant_id}: {e}")
            return False

    def _get_plan_limit(self, plan: str, resource: str) -> int:
        # ... (内容は同じなので省略)
        pass

    def _get_plan_models(self, plan: str) -> List[str]:
        # ... (内容は同じなので省略)
        pass
