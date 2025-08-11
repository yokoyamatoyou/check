"""
高精度RAG検索ページ
"""
import streamlit as st
import os
from src.auth.identity_platform import AuthManager
from src.rag.rag_engine import RAGEngine

# --- ページ設定 ---
st.set_page_config(page_title="高精度RAG検索", page_icon="🔍", layout="wide")

# --- 環境変数のチェック ---
if not all([os.getenv("OPENAI_API_KEY"), os.getenv("GCP_PROJECT_ID"), os.getenv("GCS_BUCKET_NAME_FOR_VECTOR_SEARCH")]):
    st.error("必要な環境変数が設定されていません。")
    st.info("`.env` ファイルに `OPENAI_API_KEY`, `GCP_PROJECT_ID`, `GCS_BUCKET_NAME_FOR_VECTOR_SEARCH` を設定してください。")
    st.stop()

# --- 認証 --- #
auth_manager = AuthManager()
if not auth_manager.check_authentication():
    st.stop()

# --- DIコンテナ --- #
user_info = auth_manager.get_current_user()
tenant_id = user_info.get("tenant_id", "default_tenant")
rag_engine = RAGEngine(tenant_id)

st.title("🔍 高精度RAG検索")
st.caption("ナレッジベースに登録されたドキュメントから、関連性の高い情報を検索し、AIが回答を生成します。")

# --- 検索入力 --- #
search_query = st.text_input(
    "検索クエリ", 
    placeholder="例：昨年度の事業計画について教えて",
    help="ドキュメントの内容について自然な文章で質問してください。"
)

if st.button("検索実行", type="primary"):
    if search_query:
        with st.spinner(f"「{search_query}」に基づいて回答を生成中..."):
            result = rag_engine.query(search_query)
        
        st.divider()
        st.header("AIによる回答")
        st.markdown(result["answer"])

        st.header("回答の根拠となった情報")
        if not result["context"]:
            st.info("回答の根拠となる情報は見つかりませんでした。")
        else:
            for i, chunk in enumerate(result["context"]):
                with st.expander(f"根拠 {i+1}: {chunk['metadata']['file_name']} (チャンク {chunk['metadata']['chunk_number']})"):
                    st.text(chunk["text"])
    else:
        st.warning("検索クエリを入力してください。")