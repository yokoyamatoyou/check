"""
管理者画面
高セキュリティ・AIモデル一元管理
"""
import streamlit as st
import pandas as pd
import plotly.express as px
from src.auth.identity_platform import AuthManager
from src.utils.security_utils import require_admin, require_mfa
from src.admin.tenant_admin import TenantAdmin
from src.admin.model_manager import ModelManager
from src.admin.usage_analytics import UsageAnalytics

# --- DIコンテナ --- #
auth_manager = AuthManager()
tenant_admin = TenantAdmin()
model_manager = ModelManager()
analytics = UsageAnalytics()

# --- ページ設定と認証 --- #
st.set_page_config(page_title="管理者ダッシュボード", page_icon="⚙️", layout="wide")
if not auth_manager.check_authentication():
    st.stop()

# --- 管理者ページ本体 --- #
@require_admin
@require_mfa
def admin_dashboard():
    st.title("⚙️ 管理者ダッシュボード")
    
    tab1, tab2, tab3, tab4 = st.tabs(["📊 概要", "🤖 AIモデル管理", "👥 テナント管理", "🔐 セキュリティ"])

    with tab1:
        render_overview()
    with tab2:
        render_model_management()
    with tab3:
        render_tenant_management()
    with tab4:
        render_security_settings()

def render_overview():
    st.header("システム概要")
    overview_data = analytics.get_system_overview()

    if not overview_data:
        st.warning("統計データを取得できませんでした。")
        return

    col1, col2, col3 = st.columns(3)
    col1.metric("アクティブテナント数", overview_data.get("active_tenants", 0))
    col2.metric("総ユーザー数", overview_data.get("total_users", 0))
    col3.metric("総ドキュメント数", overview_data.get("total_docs", 0))

    st.divider()
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("プラン別テナント数")
        plan_df = pd.DataFrame.from_dict(overview_data.get("by_plan", {}), orient="index", columns=["数"])
        st.dataframe(plan_df, use_container_width=True)
    with c2:
        st.subheader("ステータス別テナント数")
        status_df = pd.DataFrame.from_dict(overview_data.get("by_status", {}), orient="index", columns=["数"])
        st.dataframe(status_df, use_container_width=True)

    st.subheader("テナント別利用状況")
    tenant_usage_df = pd.DataFrame(analytics.get_tenant_usage_summary())
    st.dataframe(tenant_usage_df, use_container_width=True, hide_index=True)

def render_model_management():
    # ... (実装済み)
    pass

def render_tenant_management():
    # ... (実装済み)
    pass

def render_security_settings():
    # ... (UIのみ)
    pass

# --- 実行 --- #
admin_dashboard()