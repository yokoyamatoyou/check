"""
チャット管理モジュール
Firestoreを利用して、テナントごとにチャット履歴を管理する
"""
import streamlit as st
from typing import List, Dict, Optional
import uuid
from datetime import datetime
import logging
from google.cloud import firestore
from google.api_core import exceptions

class ChatManager:
    """
    チャット管理クラス
    - チャット履歴の保存・取得・更新・削除
    - テナントごとのデータ分離
    """

    def __init__(self, tenant_id: str):
        if not tenant_id:
            raise ValueError("Tenant ID is required")
        
        self.tenant_id = tenant_id
        self.logger = logging.getLogger(__name__)
        self.use_firestore = False

        try:
            self.db = firestore.Client()
            self.collection_path = f"tenants/{self.tenant_id}/chats"
            self.use_firestore = True
            self.logger.info(f"Firestore client initialized for tenant '{self.tenant_id}'.")
        except Exception as e:
            self.logger.warning(f"Failed to initialize Firestore: {e}. Falling back to session storage.")
            if f"chat_sessions_{self.tenant_id}" not in st.session_state:
                st.session_state[f"chat_sessions_{self.tenant_id}"] = {}

    def create_chat_session(self, user_id: str) -> str:
        session_id = str(uuid.uuid4())
        title = f"新しい会話 - {datetime.now().strftime('%Y/%m/%d %H:%M')}"
        session_data = {
            "user_id": user_id,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "messages": [],
            "title": title
        }

        if self.use_firestore:
            self.db.collection(self.collection_path).document(session_id).set(session_data)
        else:
            st.session_state[f"chat_sessions_{self.tenant_id}"][session_id] = session_data
        
        self.logger.info(f"New chat session created: {session_id}")
        return session_id

    def add_message(self, session_id: str, role: str, content: str) -> bool:
        message = {
            "message_id": str(uuid.uuid4()),
            "role": role,
            "content": content,
            "timestamp": datetime.utcnow()
        }

        if self.use_firestore:
            try:
                session_ref = self.db.collection(self.collection_path).document(session_id)
                session_ref.update({
                    "messages": firestore.ArrayUnion([message]),
                    "updated_at": datetime.utcnow()
                })
                return True
            except exceptions.NotFound:
                self.logger.error(f"Session not found: {session_id}")
                return False
        else:
            if session_id in st.session_state[f"chat_sessions_{self.tenant_id}"]:
                st.session_state[f"chat_sessions_{self.tenant_id}"][session_id]["messages"].append(message)
                return True
            return False

    def get_session_history(self, session_id: str) -> Optional[List[Dict]]:
        if self.use_firestore:
            try:
                doc = self.db.collection(self.collection_path).document(session_id).get()
                if doc.exists:
                    return doc.to_dict().get("messages", [])
                return None
            except Exception as e:
                self.logger.error(f"Failed to get session from Firestore: {e}")
                return None
        else:
            session = st.session_state[f"chat_sessions_{self.tenant_id}"].get(session_id)
            return session.get("messages") if session else None

    def delete_chat_session(self, session_id: str) -> bool:
        if self.use_firestore:
            try:
                self.db.collection(self.collection_path).document(session_id).delete()
                return True
            except Exception as e:
                self.logger.error(f"Failed to delete session from Firestore: {e}")
                return False
        else:
            if session_id in st.session_state[f"chat_sessions_{self.tenant_id}"]:
                del st.session_state[f"chat_sessions_{self.tenant_id}"][session_id]
                return True
            return False

    def list_sessions(self, user_id: str) -> List[Dict]:
        if self.use_firestore:
            try:
                query = self.db.collection(self.collection_path).where("user_id", "==", user_id).order_by("updated_at", direction=firestore.Query.DESCENDING)
                sessions = []
                for doc in query.stream():
                    session_data = doc.to_dict()
                    session_data["session_id"] = doc.id
                    sessions.append(session_data)
                return sessions
            except Exception as e:
                self.logger.error(f"Failed to list sessions from Firestore: {e}")
                return []
        else:
            # Session storage implementation
            all_sessions = st.session_state[f"chat_sessions_{self.tenant_id}"]
            user_sessions = []
            for session_id, session_data in all_sessions.items():
                if session_data["user_id"] == user_id:
                    session_data["session_id"] = session_id
                    user_sessions.append(session_data)
            return sorted(user_sessions, key=lambda x: x["updated_at"], reverse=True)
