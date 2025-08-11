from abc import ABC, abstractmethod
from typing import Dict, Any
import os
import datetime

class BaseParser(ABC):
    """
    全てのパーサーの基底クラス
    """
    def get_common_metadata(self, file_path: str) -> Dict[str, Any]:
        """全ファイル共通のメタデータを取得する"""
        try:
            creation_time = os.path.getctime(file_path)
            modification_time = os.path.getmtime(file_path)
            metadata = {
                "creation_date": datetime.datetime.fromtimestamp(creation_time).isoformat(),
                "modification_date": datetime.datetime.fromtimestamp(modification_time).isoformat(),
                "file_size_bytes": os.path.getsize(file_path),
            }
        except OSError:
            metadata = {
                "creation_date": "不明",
                "modification_date": "不明",
                "file_size_bytes": -1,
            }
        return metadata

    @abstractmethod
    def parse(self, file_path: str) -> Dict[str, Any]:
        """
        ファイルをパースし、テキストとメタデータを抽出する
        
        Args:
            file_path: パース対象のファイルパス
        
        Returns:
            {
                "text": str,
                "metadata": Dict[str, Any]
            }
        """
        pass