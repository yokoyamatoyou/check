"""
AIモデル管理モジュール
"""
import logging
from typing import Dict, Any, Optional
from google.cloud import firestore

class ModelManager:
    """
    AIモデルの構成情報をFirestoreで管理するクラス
    """
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.db = firestore.Client()
        self.collection_name = "system_settings"
        self.document_id = "ai_models"
        self.doc_ref = self.db.collection(self.collection_name).document(self.document_id)

    def save_configuration(self, config: Dict[str, Any]) -> bool:
        """
        AIモデルの構成をFirestoreに保存する
        """
        try:
            self.doc_ref.set(config, merge=True) # merge=Trueで既存のフィールドを保持
            self.logger.info("AI model configuration saved successfully.")
            return True
        except Exception as e:
            self.logger.error(f"Failed to save AI model configuration: {e}")
            return False

    def get_configuration(self) -> Optional[Dict[str, Any]]:
        """
        AIモデルの構成をFirestoreから取得する
        """
        try:
            doc = self.doc_ref.get()
            if doc.exists:
                return doc.to_dict()
            else:
                self.logger.warning("AI model configuration document not found.")
                return None
        except Exception as e:
            self.logger.error(f"Failed to get AI model configuration: {e}")
            return None