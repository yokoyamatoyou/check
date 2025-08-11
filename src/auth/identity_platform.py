"""
認証処理モジュール
Identity Platformとの連携
"""
import streamlit as st
from typing import Optional, Dict
# from google.cloud import identitytoolkit_v2

class AuthManager:
    """
    認証管理クラス
    - ログイン状態の管理
    - 認証情報の検証
    - MFA（多要素認証）の処理
    """
    
    def __init__(self):
        # self.client = identitytoolkit_v2.AuthenticationServiceClient()
        # セッション状態の初期化
        if 'user' not in st.session_state:
            st.session_state['user'] = None
        if 'mfa_verified' not in st.session_state:
            st.session_state['mfa_verified'] = False

    def check_authentication(self) -> bool:
        """
        ユーザーが認証済みかチェックする。MFA検証も含む。
        """
        if not st.session_state['user']:
            return self.show_login_form()

        user_info = self.get_current_user()
        if user_info and user_info.get("mfa_enabled") and not st.session_state['mfa_verified']:
            return self.show_mfa_form()
        
        return True

    def show_login_form(self) -> bool:
        """
        ログインフォームを表示する
        """
        st.sidebar.title("ログイン")
        email = st.sidebar.text_input("メールアドレス")
        password = st.sidebar.text_input("パスワード", type="password")

        if st.sidebar.button("ログイン"):
            user_info = self.dummy_authenticate(email, password)
            if user_info:
                st.session_state.user = user_info
                st.session_state.mfa_verified = False # ログイン時にMFA状態をリセット
                st.rerun()
            else:
                st.sidebar.error("メールアドレスまたはパスワードが正しくありません")
        return False

    def show_mfa_form(self) -> bool:
        """
        MFAコード入力フォームを表示する
        """
        st.sidebar.title("MFA認証")
        mfa_code = st.sidebar.text_input("認証コード", key="mfa_code_input")
        if st.sidebar.button("検証"):
            if self.verify_mfa_code(mfa_code):
                st.session_state.mfa_verified = True
                st.rerun()
            else:
                st.sidebar.error("認証コードが正しくありません")
        st.sidebar.info("管理者アカウントにはMFAが必要です。認証アプリのコードを入力してください。")
        return False

    def dummy_authenticate(self, email: str, password: str) -> Optional[Dict]:
        """
        ダミーの認証ロジック
        管理者ユーザーの場合はMFAを有効にする
        """
        if email == "admin@example.com" and password == "password":
            return {"email": email, "role": "admin", "mfa_enabled": True}
        if email == "user@example.com" and password == "password":
            return {"email": email, "role": "user", "mfa_enabled": False}
        return None

    def verify_mfa_code(self, code: str) -> bool:
        """
        ダミーのMFAコード検証ロジック
        """
        # 実際にはここでMFAコードを検証する
        return code == "123456"

    def get_current_user(self) -> Optional[Dict]:
        """
        現在のユーザー情報を取得する
        """
        return st.session_state.get("user")

    def logout(self):
        """
        ログアウト処理
        """
        st.session_state['user'] = None
        st.session_state['mfa_verified'] = False
        st.rerun()
