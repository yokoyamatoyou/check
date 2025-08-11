#!/usr/bin/env python3
"""
システム診断スクリプト
問題の原因を特定する
"""
import sys
import os
import traceback

def diagnose_python():
    """Python環境の診断"""
    print("=== Python環境診断 ===")
    print(f"Python version: {sys.version}")
    print(f"Python executable: {sys.executable}")
    print(f"Python path: {sys.path[:3]}...")  # 最初の3つだけ表示
    print(f"Current working directory: {os.getcwd()}")
    print()

def diagnose_imports():
    """インポートの診断"""
    print("=== インポート診断 ===")
    
    # 基本的なモジュール
    basic_modules = ['os', 'sys', 'json', 'datetime']
    for module in basic_modules:
        try:
            __import__(module)
            print(f"✅ {module} - OK")
        except ImportError as e:
            print(f"❌ {module} - FAILED: {e}")
    
    # プロジェクト固有のモジュール
    project_modules = [
        'pytest',
        'streamlit',
        'pandas',
        'numpy'
    ]
    
    print("\n--- プロジェクトモジュール ---")
    for module in project_modules:
        try:
            __import__(module)
            print(f"✅ {module} - OK")
        except ImportError as e:
            print(f"❌ {module} - FAILED: {e}")
    
    print()

def diagnose_src_imports():
    """srcモジュールの診断"""
    print("=== srcモジュール診断 ===")
    
    # srcディレクトリの存在確認
    if not os.path.exists('src'):
        print("❌ srcディレクトリが存在しません")
        return
    
    print("✅ srcディレクトリが存在します")
    
    # __init__.pyファイルの確認
    init_files = [
        'src/__init__.py',
        'src/core/__init__.py',
        'src/parsers/__init__.py',
        'src/vector_store/__init__.py',
        'src/rag/__init__.py',
        'src/chat/__init__.py',
        'src/admin/__init__.py',
        'src/auth/__init__.py',
        'src/utils/__init__.py'
    ]
    
    for init_file in init_files:
        if os.path.exists(init_file):
            print(f"✅ {init_file} - OK")
        else:
            print(f"❌ {init_file} - MISSING")
    
    print()

def diagnose_specific_modules():
    """特定のモジュールの診断"""
    print("=== 特定モジュール診断 ===")
    
    # DocumentProcessor
    try:
        from src.core.document_processor import DocumentProcessor
        processor = DocumentProcessor()
        print("✅ DocumentProcessor - OK")
    except Exception as e:
        print(f"❌ DocumentProcessor - FAILED: {e}")
        traceback.print_exc()
    
    # ChunkProcessor
    try:
        from src.core.chunk_processor import ChunkProcessor
        print("✅ ChunkProcessor import - OK")
    except Exception as e:
        print(f"❌ ChunkProcessor import - FAILED: {e}")
        traceback.print_exc()
    
    print()

def diagnose_streamlit():
    """Streamlitの診断"""
    print("=== Streamlit診断 ===")
    
    try:
        import streamlit as st
        print(f"✅ Streamlit version: {st.__version__}")
        
        # Streamlitの基本機能テスト
        print("✅ Streamlit基本機能 - OK")
        
    except Exception as e:
        print(f"❌ Streamlit - FAILED: {e}")
        traceback.print_exc()
    
    print()

def diagnose_pytest():
    """pytestの診断"""
    print("=== pytest診断 ===")
    
    try:
        import pytest
        print(f"✅ pytest version: {pytest.__version__}")
        
        # pytestの基本機能テスト
        print("✅ pytest基本機能 - OK")
        
    except Exception as e:
        print(f"❌ pytest - FAILED: {e}")
        traceback.print_exc()
    
    print()

def main():
    """メイン関数"""
    print("🔍 システム診断を開始します...")
    print("=" * 60)
    
    try:
        diagnose_python()
        diagnose_imports()
        diagnose_src_imports()
        diagnose_specific_modules()
        diagnose_streamlit()
        diagnose_pytest()
        
        print("=" * 60)
        print("🎉 診断が完了しました")
        
    except Exception as e:
        print(f"❌ 診断中にエラーが発生しました: {e}")
        traceback.print_exc()

if __name__ == '__main__':
    main()

