
import pytest
from unittest.mock import patch, MagicMock
import pandas as pd
from src.admin.usage_analytics import UsageAnalytics

# モック用のテナントデータ
MOCK_TENANTS = [
    {"tenant_id": "t1", "name": "Tenant 1", "plan": "pro", "status": "active", "usage": {"users": 10, "documents": 100}},
    {"tenant_id": "t2", "name": "Tenant 2", "plan": "free", "status": "active", "usage": {"users": 5, "documents": 50}},
    {"tenant_id": "t3", "name": "Tenant 3", "plan": "pro", "status": "suspended", "usage": {"users": 20, "documents": 200}},
]

@pytest.fixture
def mock_firestore_client():
    """Firestoreクライアントをモック化し、ストリームを返すように設定する"""
    with patch('src.admin.usage_analytics.firestore.Client') as mock_client_class:
        mock_db = MagicMock()
        mock_collection = MagicMock()
        mock_stream = MagicMock()

        mock_client_class.return_value = mock_db
        mock_db.collection.return_value = mock_collection
        mock_collection.stream.return_value = mock_stream

        # to_dictを持つモックドキュメントのリストを作成
        mock_docs = []
        for data in MOCK_TENANTS:
            doc = MagicMock()
            doc.to_dict.return_value = data
            mock_docs.append(doc)
        
        # ストリームがモックドキュメントを返すように設定
        mock_stream.__iter__.return_value = iter(mock_docs)

        yield mock_db

@pytest.fixture
def usage_analytics(mock_firestore_client):
    """テスト用のUsageAnalyticsインスタンスを返す"""
    return UsageAnalytics()

class TestUsageAnalytics:

    def test_get_system_overview(self, usage_analytics):
        """システム概要の集計が正しいかテストする"""
        overview = usage_analytics.get_system_overview()

        assert overview["active_tenants"] == 2
        assert overview["total_users"] == 35 # 10 + 5 + 20
        assert overview["total_docs"] == 350 # 100 + 50 + 200
        assert overview["by_plan"] == {"pro": 2, "free": 1}
        assert overview["by_status"] == {"active": 2, "suspended": 1}

    def test_get_tenant_usage_summary(self, usage_analytics):
        """テナントごとの利用状況サマリーが正しいかテストする"""
        summary = usage_analytics.get_tenant_usage_summary()
        
        assert len(summary) == 3
        # Tenant 1のデータを確認
        tenant1_summary = next(s for s in summary if s["name"] == "Tenant 1")
        assert tenant1_summary["plan"] == "pro"
        assert tenant1_summary["documents"] == 100

    def test_get_system_overview_no_data(self, usage_analytics, mock_firestore_client):
        """データがない場合にシステム概要がデフォルト値を返すか"""
        # ストリームが空のリストを返すように再設定
        mock_firestore_client.collection.return_value.stream.return_value = []
        overview = usage_analytics.get_system_overview()
        assert overview["active_tenants"] == 0
        assert overview["total_users"] == 0
