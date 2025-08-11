"""
生成AI対話ページ

Web版のGeminiやChatGPTのようなプロフェッショナルなデザインを目指す。
- シンプルなインターフェース
- 充実した機能（ファイル添付、Web検索、履歴管理）
"""
import streamlit as st
import time
import os
from src.chat.chat_manager import ChatManager
from src.auth.identity_platform import AuthManager
from src.chat.gpt_client import GPTClient

# --- ページ設定 --- #
st.set_page_config(page_title="生成AI対話", page_icon="💬", layout="wide")

# --- APIキーのチェック --- #
if not os.getenv("OPENAI_API_KEY"):
    st.error("環境変数 `OPENAI_API_KEY` が設定されていません。")
    st.info("`.env` ファイルを作成し、`OPENAI_API_KEY="sk-..."` のようにキーを設定してください。")
    st.stop()

# --- 認証 --- #
auth_manager = AuthManager()
if not auth_manager.check_authentication():
    st.stop()

# --- DIコンテナ --- #
user_info = auth_manager.get_current_user()
tenant_id = user_info.get("tenant_id", "default_tenant")
user_id = user_info.get("email")

chat_manager = ChatManager(tenant_id)
gpt_client = GPTClient()

# --- セッション状態の初期化 --- #
if "current_session_id" not in st.session_state:
    st.session_state.current_session_id = None

# --- サイドバー --- #
with st.sidebar:
    st.title("💬 対話履歴")
    
    if st.button("➕ 新しいチャット", use_container_width=True):
        st.session_state.current_session_id = chat_manager.create_chat_session(user_id)
        st.rerun()

    st.divider()

    sessions = chat_manager.list_sessions(user_id)
    if not sessions:
        st.info("対話履歴はありません。")

    for session in sessions:
        session_id = session["session_id"]
        col1, col2 = st.columns([4, 1])
        with col1:
            if st.button(session.get("title", session_id), key=f"session_btn_{session_id}", use_container_width=True):
                st.session_state.current_session_id = session_id
                st.rerun()
        with col2:
            if st.button("🗑️", key=f"delete_btn_{session_id}", use_container_width=True):
                chat_manager.delete_chat_session(session_id)
                if st.session_state.current_session_id == session_id:
                    st.session_state.current_session_id = None
                st.rerun()

# --- メイン画面 --- #
st.title("生成AI対話")
st.caption("最新のAIモデルとの対話を通じて、アイデアの創出やタスクの実行をサポートします。")

if not st.session_state.current_session_id:
    st.info("サイドバーから新しいチャットを開始するか、既存の履歴を選択してください。")
    st.stop()

# チャット履歴の表示
messages = chat_manager.get_session_history(st.session_state.current_session_id)
if messages is not None:
    for message in messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

# チャット入力
prompt = st.chat_input("メッセージを送信")

# 入力欄の下にオプションを配置
bottom_container = st.container()
with bottom_container:
    cols = st.columns([3, 1])
    with cols[0]:
        attached_files = st.file_uploader(
            "ファイルを添付", 
            accept_multiple_files=True, 
            label_visibility="collapsed",
            type=["pdf", "txt", "md", "docx", "png", "jpg"]
        )
    with cols[1]:
        use_web_search = st.checkbox("Web検索を利用する", value=False)

if prompt:
    # ユーザーメッセージを履歴に追加・表示
    chat_manager.add_message(st.session_state.current_session_id, "user", prompt)
    with st.chat_message("user"):
        st.markdown(prompt)

    # AI応答を生成
    with st.chat_message("assistant"):
        with st.spinner("AIが応答を生成中..."):
            # 履歴を渡すために再度取得
            updated_messages = chat_manager.get_session_history(st.session_state.current_session_id)
            
            response_text, thought_process = gpt_client.generate_response(
                messages=updated_messages, 
                model_name="gpt-4.1-mini", # TODO: モデル選択UIを追加
                use_web_search=use_web_search,
                attached_files=attached_files
            )
            
            with st.expander("思考プロセスを表示"):
                st.text(thought_process)
            
            # 応答をマークダウンで表示
            st.markdown(response_text)

    # AI応答を履歴に追加
    chat_manager.add_message(st.session_state.current_session_id, "assistant", response_text)
    st.rerun()