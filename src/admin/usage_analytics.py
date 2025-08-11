"""
利用統計モジュール
"""
import logging
from typing import Dict, Any, List
from google.cloud import firestore
import pandas as pd

class UsageAnalytics:
    """
    Firestoreから利用状況データを集計・分析するクラス
    """
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.db = firestore.Client()
        self.tenant_collection = "tenants"
        self.doc_collection_base = "documents"

    def get_system_overview(self) -> Dict[str, Any]:
        """
        システム全体の概要を取得する
        """
        try:
            tenants = self.db.collection(self.tenant_collection).stream()
            tenant_list = [t.to_dict() for t in tenants]
            
            if not tenant_list:
                return {"active_tenants": 0, "total_users": 0, "total_docs": 0}

            df = pd.DataFrame(tenant_list)
            
            active_tenants = df[df["status"] == "active"].shape[0]
            total_users = df["usage"].apply(lambda x: x.get("users", 0)).sum()
            total_docs = df["usage"].apply(lambda x: x.get("documents", 0)).sum()

            return {
                "active_tenants": active_tenants,
                "total_users": total_users,
                "total_docs": total_docs,
                "by_plan": df.groupby("plan")["tenant_id"].count().to_dict(),
                "by_status": df.groupby("status")["tenant_id"].count().to_dict(),
            }
        except Exception as e:
            self.logger.error(f"Failed to get system overview: {e}")
            return {}

    def get_tenant_usage_summary(self) -> List[Dict[str, Any]]:
        """
        テナントごとの利用状況サマリーを取得
        """
        try:
            tenants = self.db.collection(self.tenant_collection).stream()
            summary = []
            for tenant in tenants:
                t_data = tenant.to_dict()
                usage = t_data.get("usage", {})
                summary.append({
                    "name": t_data.get("name"),
                    "plan": t_data.get("plan"),
                    "documents": usage.get("documents", 0),
                    "api_calls": usage.get("api_calls", 0), # TODO: APIコール数を記録する仕組みが必要
                })
            return summary
        except Exception as e:
            self.logger.error(f"Failed to get tenant usage summary: {e}")
            return []