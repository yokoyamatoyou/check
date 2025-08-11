import re
from playwright.sync_api import sync_playwright, Page, expect
import pytest

# E2Eテストは時間がかかるため、デフォルトでは無効化し、
# `pytest --e2e` のように明示的に指定された場合のみ実行する
pytestmark = pytest.mark.e2e

def test_chat_with_openai_model(page: Page):
    """
    OpenAIモデルとの対話が正常に行えるかをテストするE2Eテスト
    """
    # 1. アプリにアクセスし、ウェルカムページを確認
    page.goto("http://localhost:8501")
    expect(page.get_by_text("ようこそ、エンタープライズRAGシステムへ")).to_be_visible()

    # 2. サイドバーから「生成AI対話」ページに移動
    page.get_by_role("link", name="生成AI対話").click()

    # 3. ログイン情報を入力
    page.get_by_label("メールアドレス").fill("admin@example.com")
    page.get_by_label("パスワード").fill("password")
    page.get_by_role("button", name="ログイン").click()
    page.get_by_label("認証コード").fill("123456")
    page.get_by_role("button", name="検証").click()
    expect(page.get_by_text("AIモデル選択")).to_be_visible(timeout=10000)

    # 3. `gpt-4.1-mini`モデルを選択
    page.get_by_label("AIモデル選択").select_option(label='gpt-4.1-mini')

    # 4. プロンプトを入力して送信
    prompt = "こんにちは、自己紹介してください。"
    page.get_by_placeholder("メッセージを送信").fill(prompt)
    page.get_by_role("button", name="送信").click()

    # 5. AIからの応答が表示されることを確認
    # 応答がストリーミングされるため、最終的な応答が完了するまで待機する
    # ここでは、応答に「OpenAI」という単語が含まれているかで簡易的に判定
    expect(page.locator(".stChatMessage").last().get_by_text("OpenAI")).to_be_visible(timeout=20000)
