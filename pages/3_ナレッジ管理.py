"""
ナレッジ管理ページ

RAGシステムの知識ベースとなるドキュメントを管理する。
- 直感的なUI/UX
- プロセスの透明性
- 効率的な管理機能
"""
import streamlit as st
import pandas as pd
import plotly.express as px
import time
from src.core.document_manager import DocumentManager
from src.auth.identity_platform import AuthManager

# --- ページ設定 --- #
st.set_page_config(page_title="ナレッジ管理", page_icon="📚", layout="wide")

# --- 認証 --- #
auth_manager = AuthManager()
if not auth_manager.check_authentication():
    st.stop()

# --- DIコンテナ --- #
# ログインしているユーザーからテナントIDを取得（ダミー）
user_info = auth_manager.get_current_user()
tenant_id = user_info.get("tenant_id", "default_tenant") # 本来はユーザー情報から取得
doc_manager = DocumentManager(tenant_id)

# --- メイン画面 --- #
st.title("📚 ナレッジ管理")
st.caption("RAGシステムの知識ベースとなるドキュメントを管理します。")

tab1, tab2, tab3 = st.tabs(["📊 ダッシュボード", "📤 新規アップロード", "📂 ドキュメント一覧"])

# --- Tab 1: ダッシュボード --- #
with tab1:
    stats = doc_manager.get_dashboard_stats()
    st.header("ナレッジベース概要")

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("総ドキュメント数", f"{stats['total_docs']} 件")
    col2.metric("総ファイルサイズ", f"{stats['total_size_mb']:.2f} MB")
    col3.metric("処理済み", f"{stats['by_status'].get('処理済み', 0)} 件")
    col4.metric("エラー", f"{stats['by_status'].get('エラー', 0)} 件", delta_color="inverse")

    st.divider()

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("ファイル種別ごとの内訳")
        if not stats["by_type"].empty:
            fig = px.pie(stats["by_type"], names='type', values='count', title='ファイルタイプ分布')
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("データがありません。")
    with col2:
        st.subheader("ステータス別ドキュメント")
        if stats["by_status"]:
            st.dataframe(pd.DataFrame.from_dict(stats["by_status"], orient='index', columns=['件数']), use_container_width=True)
        else:
            st.info("データがありません。")

# --- Tab 2: 新規アップロード --- #
with tab2:
    st.header("ドキュメントの新規アップロード")
    uploaded_files = st.file_uploader(
        "ここにファイルをドラッグ＆ドロップするか、ファイルを選択してください",
        accept_multiple_files=True,
        type=["pdf", "docx", "txt", "md"],
        help="対応形式: PDF, Word, テキスト, マークダウン"
    )

    if uploaded_files:
        st.write("選択されたファイル:")
        for f in uploaded_files:
            st.write(f"- {f.name} ({round(f.size / (1024*1024), 2)} MB)")
        
        if st.button("アップロードと処理を開始", type="primary"):
            with st.spinner("ファイルをアップロードし、処理を実行しています..."):
                doc_manager.upload_and_process_documents(uploaded_files)
            st.success(f"{len(uploaded_files)}個のファイルの処理を開始しました。ドキュメント一覧タブで状況を確認してください。")

# --- Tab 3: ドキュメント一覧 --- #
with tab3:
    st.header("登録済みドキュメント")

    # 検索とフィルタ
    col1, col2 = st.columns([3, 1])
    with col1:
        search_term = st.text_input("ファイル名で検索", placeholder="例: 事業計画")
    with col2:
        status_filter = st.selectbox("ステータスで絞り込み", ["すべて", "処理済み", "処理中", "エラー"])

    # ドキュメント一覧の表示
    documents = doc_manager.get_all_documents(search_term, status_filter)
    
    if not documents:
        st.info("表示するドキュメントがありません。新規アップロードタブからファイルを追加してください。")
    else:
        st.write(f"{len(documents)}件のドキュメントが見つかりました。")

        for doc in documents:
            st.divider()
            col1, col2, col3, col4, col5 = st.columns([3, 1, 1, 1, 2])
            
            file_icons = {".pdf": "📄", ".docx": "📝", ".txt": "✍️", ".md": "✍️"}
            with col1:
                st.markdown(f"**{file_icons.get(doc['type'], '❓')} {doc['name']}**")
                st.caption(f"アップロード日: {doc['uploaded_at']}")
            
            with col2:
                st.metric("サイズ", f"{doc['size']} MB")

            with col3:
                status_color = {"処理済み": "success", "処理中": "info", "エラー": "error"}
                # st.metric("状態", doc['status'])
                st.status(doc['status'], state=status_color.get(doc['status'], "running"))

            with col4:
                if st.button("詳細", key=f"detail_{doc['id']}"):
                    st.session_state.selected_doc_id = doc['id']
            
            with col5:
                if st.button("削除", key=f"delete_{doc['id']}", type="secondary"):
                    if doc_manager.delete_document(doc['id']):
                        st.success(f"「{doc['name']}」を削除しました。")
                        st.rerun()

    # 詳細表示エリア
    if 'selected_doc_id' in st.session_state and st.session_state.selected_doc_id:
        details = doc_manager.get_document_details(st.session_state.selected_doc_id)
        if details:
            with st.expander(f"詳細: {details['name']}", expanded=True):
                st.subheader("ドキュメント情報")
                st.write(f"- **ファイルID:** {details['id']}")
                st.write(f"- **チャンク数:** {details['chunks']}個")
                
                if details['status'] == "エラー":
                    st.error(f"**エラーメッセージ:** {details['error_message']}")
                    if st.button("再処理を実行", key=f"reprocess_{details['id']}"):
                        st.info("再処理を開始しました...（未実装）")

                st.subheader("抽出テキスト（プレビュー）")
                st.text_area("", value=details['content_preview'], height=200, disabled=True)

                if st.button("閉じる", key=f"close_{details['id']}"):
                    st.session_state.selected_doc_id = None
                    st.rerun()
