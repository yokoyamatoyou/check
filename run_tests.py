#!/usr/bin/env python3
"""
テスト実行スクリプト
Streamlitの干渉を避けてテストを実行
"""
import os
import sys
import subprocess
import argparse

def setup_test_environment():
    """テスト環境のセットアップ"""
    # テスト環境変数を設定
    os.environ['TESTING'] = 'true'
    os.environ['STREAMLIT_SERVER_HEADLESS'] = 'true'
    os.environ['STREAMLIT_SERVER_RUN_ON_SAVE'] = 'false'
    os.environ['PYTHONPATH'] = os.getcwd()
    
    # Streamlitのログを無効化
    os.environ['STREAMLIT_LOGGER_LEVEL'] = 'error'

def run_tests(test_type='unit', verbose=True):
    """テストを実行"""
    setup_test_environment()
    
    # pytestコマンドを構築
    cmd = [
        sys.executable, '-m', 'pytest',
        f'tests/{test_type}/',
        '--tb=short',
        '--disable-warnings',
        '--import-mode=importlib'
    ]
    
    if verbose:
        cmd.append('-v')
    
    print(f"実行コマンド: {' '.join(cmd)}")
    print(f"テストタイプ: {test_type}")
    print("-" * 50)
    
    try:
        result = subprocess.run(cmd, capture_output=False, text=True)
        return result.returncode == 0
    except Exception as e:
        print(f"テスト実行エラー: {e}")
        return False

def run_specific_test(test_path):
    """特定のテストファイルを実行"""
    setup_test_environment()
    
    cmd = [
        sys.executable, '-m', 'pytest',
        test_path,
        '-v',
        '--tb=short',
        '--disable-warnings',
        '--import-mode=importlib'
    ]
    
    print(f"実行コマンド: {' '.join(cmd)}")
    print("-" * 50)
    
    try:
        result = subprocess.run(cmd, capture_output=False, text=True)
        return result.returncode == 0
    except Exception as e:
        print(f"テスト実行エラー: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description='RAGシステムテスト実行')
    parser.add_argument('--type', choices=['unit', 'integration', 'e2e'], 
                       default='unit', help='テストタイプ')
    parser.add_argument('--file', help='特定のテストファイル')
    parser.add_argument('--quiet', action='store_true', help='詳細出力を無効化')
    
    args = parser.parse_args()
    
    if args.file:
        success = run_specific_test(args.file)
    else:
        success = run_tests(args.type, not args.quiet)
    
    if success:
        print("\n✅ テストが正常に完了しました")
        sys.exit(0)
    else:
        print("\n❌ テストが失敗しました")
        sys.exit(1)

if __name__ == '__main__':
    main()

