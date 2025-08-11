
import pytest
from unittest.mock import MagicMock, patch
import streamlit as st

# テスト対象のモジュールをインポート
from src.auth.identity_platform import AuthManager
from src.auth.tenant_manager import TenantManager
from src.utils.security_utils import require_admin, require_mfa

# Streamlitのセッションステートをモックするためのフィクスチャ
@pytest.fixture
def mock_session_state(monkeypatch):
    """Streamlitのセッションステートを属性アクセス可能なMagicMockでモックする"""
    mock_state = MagicMock()
    mock_user = MagicMock()
    mock_user.get.return_value = None # デフォルトではroleはNone
    mock_state.user = mock_user
    mock_state.mfa_verified = False
    monkeypatch.setattr(st, 'session_state', mock_state)
    # getメソッドもモックする
    monkeypatch.setattr(st.session_state, 'get', mock_state.__getitem__)
    mock_state.__getitem__.side_effect = lambda key: getattr(mock_state, key, None)
    return mock_state

# === AuthManagerのテスト ===

class TestAuthManager:

    def test_initialization(self, mock_session_state):
        """初期化時にセッションが正しく設定されるか"""
        AuthManager()
        assert mock_session_state.user is None
        assert not mock_session_state.mfa_verified

    def test_dummy_authenticate_admin(self):
        """管理者ユーザーのダミー認証"""
        auth = AuthManager()
        user = auth.dummy_authenticate("admin@example.com", "password")
        assert user is not None
        assert user['role'] == 'admin'
        assert user['mfa_enabled']

    def test_dummy_authenticate_user(self):
        """一般ユーザーのダミー認証"""
        auth = AuthManager()
        user = auth.dummy_authenticate("user@example.com", "password")
        assert user is not None
        assert user['role'] == 'user'
        assert not user['mfa_enabled']

    def test_dummy_authenticate_fail(self):
        """認証失敗"""
        auth = AuthManager()
        user = auth.dummy_authenticate("wrong@example.com", "wrong")
        assert user is None

    @patch('streamlit.rerun')
    def test_logout(self, mock_rerun, mock_session_state):
        """ログアウト処理"""
        auth = AuthManager()
        mock_session_state.user = {'email': 'test@example.com'}
        mock_session_state.mfa_verified = True
        
        auth.logout()
            
        assert mock_session_state.user is None
        assert not mock_session_state.mfa_verified
        mock_rerun.assert_called_once()

# === TenantManagerのテスト ===

@patch('src.auth.tenant_manager.firestore.Client')
def test_create_tenant(mock_firestore_client):
    """テナント作成が正しくFirestoreを呼び出すか"""
    mock_db = MagicMock()
    mock_firestore_client.return_value = mock_db
    
    tenant_manager = TenantManager()
    tenant_data = tenant_manager.create_tenant("Test Tenant", "test@example.com", "pro")
    
    assert tenant_data['name'] == "Test Tenant"
    assert tenant_data['plan'] == "pro"
    
    # Firestoreのdocument().set()が呼ばれたことを確認
    mock_db.collection("tenants").document.assert_called_once_with(tenant_data['tenant_id'])
    mock_db.collection("tenants").document().set.assert_called_once()

# === security_utilsのテスト ===

def test_require_admin_success(mock_session_state):
    """管理者権限がある場合のデコレータ"""
    mock_session_state.user.get.return_value = 'admin'
    
    @require_admin
    def dummy_func():
        return "Success"
        
    assert dummy_func() == "Success"

@patch('streamlit.stop')
def test_require_admin_fail(mock_stop, mock_session_state):
    """管理者権限がない場合のデコレータ"""
    mock_session_state.user.get.return_value = 'user'
    
    @require_admin
    def dummy_func():
        return "Should not be called"
    
    dummy_func()
    mock_stop.assert_called_once()

def test_require_mfa_success(mock_session_state):
    """MFA検証済みの場合のデコレータ"""
    mock_session_state.user.get.side_effect = lambda key: {'role': 'admin', 'mfa_enabled': True}.get(key)
    mock_session_state.mfa_verified = True
    
    @require_mfa
    def dummy_func():
        return "Success"
        
    assert dummy_func() == "Success"

@patch('streamlit.stop')
def test_require_mfa_fail(mock_stop, mock_session_state):
    """MFA未検証の場合のデコレータ"""
    mock_user = MagicMock()
    mock_user.get.side_effect = lambda key: {'role': 'admin', 'mfa_enabled': True}.get(key)
    mock_session_state.user = mock_user
    mock_session_state.mfa_verified = False
    
    @require_mfa
    def dummy_func():
        return "Should not be called"
        
    dummy_func()
    mock_stop.assert_called_once()
