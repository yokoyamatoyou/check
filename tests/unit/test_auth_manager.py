
import pytest
from unittest.mock import patch, MagicMock
from src.auth.identity_platform import AuthManager

# Streamlitのセッションステートを模倣するためのフィクスチャ
@pytest.fixture
def mock_session_state():
    """st.session_stateを模倣する辞書を返す"""
    with patch('src.auth.identity_platform.st') as mock_st:
        mock_st.session_state = {}
        yield mock_st.session_state

@pytest.fixture
def auth_manager(mock_session_state):
    """テスト用のAuthManagerインスタンスを返す"""
    return AuthManager()

class TestAuthManagerLogic:

    def test_initialization(self, mock_session_state):
        """初期化時にセッションステートが正しく設定されるか"""
        assert "user" not in mock_session_state
        assert "mfa_verified" not in mock_session_state
        manager = AuthManager()
        assert mock_session_state["user"] is None
        assert mock_session_state["mfa_verified"] is False

    @pytest.mark.parametrize("email, password, expected_role, mfa_enabled", [
        ("admin@example.com", "password", "admin", True),
        ("user@example.com", "password", "user", False),
        ("wrong@email.com", "password", None, None),
        ("user@example.com", "wrong_password", None, None),
    ])
    def test_dummy_authenticate(self, auth_manager, email, password, expected_role, mfa_enabled):
        """ダミー認証ロジックをテストする"""
        user_info = auth_manager.dummy_authenticate(email, password)
        if expected_role:
            assert user_info is not None
            assert user_info["role"] == expected_role
            assert user_info["mfa_enabled"] == mfa_enabled
        else:
            assert user_info is None

    @pytest.mark.parametrize("code, expected_result", [
        ("123456", True),
        ("654321", False),
        ("", False),
    ])
    def test_verify_mfa_code(self, auth_manager, code, expected_result):
        """MFAコード検証ロジックをテストする"""
        assert auth_manager.verify_mfa_code(code) == expected_result

    def test_get_current_user(self, auth_manager, mock_session_state):
        """現在のユーザー情報取得をテストする"""
        mock_session_state["user"] = {"email": "test@user.com"}
        user = auth_manager.get_current_user()
        assert user is not None
        assert user["email"] == "test@user.com"

        mock_session_state["user"] = None
        user = auth_manager.get_current_user()
        assert user is None

    def test_logout(self, auth_manager, mock_session_state):
        """ログアウト処理をテストする"""
        mock_session_state["user"] = {"email": "test@user.com"}
        mock_session_state["mfa_verified"] = True
        
        # st.rerunは例外を発生させるので、それをキャッチする
        with patch('src.auth.identity_platform.st.rerun') as mock_rerun:
            auth_manager.logout()

        assert mock_session_state["user"] is None
        assert mock_session_state["mfa_verified"] is False
        mock_rerun.assert_called_once()
