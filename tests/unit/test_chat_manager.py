
import pytest
from unittest.mock import patch, MagicMock
from src.chat.chat_manager import ChatManager

# Firestoreが利用可能な場合のフィクスチャ
@pytest.fixture
def firestore_manager():
    with patch('src.chat.chat_manager.firestore.Client') as mock_client_class:
        mock_db = MagicMock()
        mock_collection = MagicMock()
        mock_doc_ref = MagicMock()
        mock_doc_snapshot = MagicMock()

        mock_client_class.return_value = mock_db
        mock_db.collection.return_value = mock_collection
        mock_collection.document.return_value = mock_doc_ref
        mock_doc_ref.get.return_value = mock_doc_snapshot
        
        manager = ChatManager(tenant_id="test_tenant")
        manager.db = mock_db # モックを注入
        manager.use_firestore = True
        yield manager, mock_collection, mock_doc_ref, mock_doc_snapshot

# Firestoreが利用不可（セッションストレージ）の場合のフィクスチャ
@pytest.fixture
def session_storage_manager():
    with patch('src.chat.chat_manager.firestore.Client', side_effect=Exception("No Firestore")) as mock_client_class, \
         patch('src.chat.chat_manager.st') as mock_st:
        
        mock_st.session_state = {}
        manager = ChatManager(tenant_id="test_tenant_session")
        yield manager, mock_st.session_state

class TestChatManagerFirestore:
    def test_create_chat_session(self, firestore_manager):
        manager, mock_collection, mock_doc_ref, _ = firestore_manager
        session_id = manager.create_chat_session(user_id="user1")
        mock_collection.document.assert_called_with(session_id)
        mock_doc_ref.set.assert_called_once()

    def test_add_message(self, firestore_manager):
        manager, _, mock_doc_ref, _ = firestore_manager
        result = manager.add_message("session1", "user", "Hello")
        assert result is True
        mock_doc_ref.update.assert_called_once()

    def test_get_session_history(self, firestore_manager):
        manager, _, _, mock_snapshot = firestore_manager
        mock_snapshot.exists = True
        mock_snapshot.to_dict.return_value = {"messages": [{"role": "user", "content": "Hi"}]}
        history = manager.get_session_history("session1")
        assert history is not None
        assert len(history) == 1
        assert history[0]["content"] == "Hi"

    def test_delete_chat_session(self, firestore_manager):
        manager, _, mock_doc_ref, _ = firestore_manager
        result = manager.delete_chat_session("session1")
        assert result is True
        mock_doc_ref.delete.assert_called_once()

class TestChatManagerSessionStorage:
    def test_create_chat_session(self, session_storage_manager):
        manager, session_state = session_storage_manager
        session_id = manager.create_chat_session(user_id="user1")
        assert session_id in session_state[f"chat_sessions_{manager.tenant_id}"]

    def test_add_message(self, session_storage_manager):
        manager, session_state = session_storage_manager
        session_id = manager.create_chat_session(user_id="user1")
        result = manager.add_message(session_id, "user", "Hello Session")
        assert result is True
        assert len(session_state[f"chat_sessions_{manager.tenant_id}"][session_id]["messages"]) == 1

    def test_get_session_history(self, session_storage_manager):
        manager, session_state = session_storage_manager
        session_id = manager.create_chat_session(user_id="user1")
        manager.add_message(session_id, "user", "History Test")
        history = manager.get_session_history(session_id)
        assert history is not None
        assert len(history) == 1
        assert history[0]["content"] == "History Test"

    def test_delete_chat_session(self, session_storage_manager):
        manager, session_state = session_storage_manager
        session_id = manager.create_chat_session(user_id="user1")
        result = manager.delete_chat_session(session_id)
        assert result is True
        assert session_id not in session_state[f"chat_sessions_{manager.tenant_id}"]
