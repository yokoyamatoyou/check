"""
メインアプリケーション
"""
import streamlit as st

st.set_page_config(
    page_title="エンタープライズRAGシステム",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)


def main():
    """メインページ"""
    st.title("ようこそ、エンタープライズRAGシステムへ")
    st.caption("左のメニューから機能を選択してください")

    st.sidebar.success("上のメニューを選択してください")

    st.markdown(
        """
        このシステムは、社内ナレッジを効率的に活用するための統合プラットフォームです。
        
        ### 主な機能
        - **高精度RAG検索**: アップロードされたドキュメントに対して、自然言語で高精度な検索を実行します。
        - **生成AI対話**: 最新のLLMと対話し、アイデアの創出や文章作成をサポートします。
        - **ナレッジ管理**: RAGシステムの知識ベースとなるドキュメントを管理します。
        - **管理者画面**: システムの利用状況や設定を管理します。
        """
    )

if __name__ == "__main__":
    # ここで認証チェックを行う想定
    # auth_manager = AuthManager()
    # if not auth_manager.check_authentication():
    #     st.stop()
    main()
