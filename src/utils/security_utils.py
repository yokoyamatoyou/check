
"""
セキュリティ関連のユーティリティ関数
"""
import streamlit as st
from functools import wraps

def require_admin(func):
    """
    管理者権限を要求するデコレータ
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        user = st.session_state.get("user")
        if not user or user.get("role") != "admin":
            st.error("管理者権限が必要です")
            st.stop()
            return
        return func(*args, **kwargs)
    return wrapper

def require_mfa(func):
    """
    MFAを要求するデコレータ
    MFAが検証済みかチェックする
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        user = st.session_state.get("user")
        # 管理者ロールで、MFAが有効なユーザーの場合のみチェック
        if user and user.get("role") == "admin" and user.get("mfa_enabled"):
            if not st.session_state.get("mfa_verified"):
                st.warning("MFA認証が必要です。サイドバーから認証を完了してください。")
                st.stop()
                return # st.stop()の後に処理を続行しない
        return func(*args, **kwargs)
    return wrapper
