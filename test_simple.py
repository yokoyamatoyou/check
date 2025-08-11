#!/usr/bin/env python3
"""
シンプルなテストファイル
基本的なテストが動作するか確認
"""
import os
import sys

# テスト環境変数を設定
os.environ['TESTING'] = 'true'
os.environ['STREAMLIT_SERVER_HEADLESS'] = 'true'

def test_basic_function():
    """基本的な関数テスト"""
    def add(a, b):
        return a + b
    
    assert add(1, 2) == 3
    assert add(-1, 1) == 0
    print("✅ 基本的な関数テストが成功しました")

def test_import_modules():
    """モジュールのインポートテスト"""
    try:
        import pytest
        print("✅ pytestのインポートが成功しました")
    except ImportError as e:
        print(f"❌ pytestのインポートに失敗: {e}")
        return False
    
    try:
        import streamlit
        print("✅ streamlitのインポートが成功しました")
    except ImportError as e:
        print(f"❌ streamlitのインポートに失敗: {e}")
        return False
    
    return True

def test_document_processor_import():
    """DocumentProcessorのインポートテスト"""
    try:
        from src.core.document_processor import DocumentProcessor
        processor = DocumentProcessor()
        print("✅ DocumentProcessorのインポートと初期化が成功しました")
        return True
    except Exception as e:
        print(f"❌ DocumentProcessorのテストに失敗: {e}")
        return False

def test_chunk_processor_import():
    """ChunkProcessorのインポートテスト"""
    try:
        from src.core.chunk_processor import ChunkProcessor
        # EmbeddingClientのモックが必要
        import unittest.mock
        with unittest.mock.patch('src.core.chunk_processor.EmbeddingClient'):
            processor = ChunkProcessor()
        print("✅ ChunkProcessorのインポートと初期化が成功しました")
        return True
    except Exception as e:
        print(f"❌ ChunkProcessorのテストに失敗: {e}")
        return False

def main():
    """メイン関数"""
    print("🧪 シンプルなテストを開始します...")
    print("=" * 50)
    
    # 基本的なテスト
    test_basic_function()
    
    # モジュールインポートテスト
    if not test_import_modules():
        print("❌ モジュールインポートテストが失敗しました")
        return False
    
    # DocumentProcessorテスト
    if not test_document_processor_import():
        print("❌ DocumentProcessorテストが失敗しました")
        return False
    
    # ChunkProcessorテスト
    if not test_chunk_processor_import():
        print("❌ ChunkProcessorテストが失敗しました")
        return False
    
    print("=" * 50)
    print("🎉 すべてのテストが成功しました！")
    return True

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)

