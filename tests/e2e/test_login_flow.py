
import re
from playwright.sync_api import sync_playwright, Page, expect

def test_admin_login_flow(page: Page):
    """管理者としてログインし、MFAを通過し、ダッシュボードにアクセスするE2Eテスト"""
    # アプリは事前に `streamlit run app.py --server.port 8501` で起動しておく必要がある
    page.goto("http://localhost:8501")

    # ログイン情報を入力
    page.get_by_label("メールアドレス").fill("admin@example.com")
    page.get_by_label("パスワード").fill("password")
    page.get_by_role("button", name="ログイン").click()

    # MFAフォームの表示を確認
    expect(page.get_by_text("MFA認証")).to_be_visible()

    # MFAコードを入力して検証
    page.get_by_label("認証コード").fill("123456")
    page.get_by_role("button", name="検証").click()

    # ログイン成功を確認
    expect(page.get_by_text("システム概要")).to_be_visible(timeout=10000)

# このスクリプトを直接実行する場合のエントリーポイント
if __name__ == "__main__":
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False) # ヘッドレスモードを解除してブラウザの動きを確認
        page = browser.new_page()
        test_admin_login_flow(page)
        browser.close()
