import streamlit as st

def apply_custom_css():
    """
    StreamlitアプリケーションにカスタムCSSを適用
    """
    st.markdown(
        """
        <style>
        .reportview-container {
            flex-direction: row;
        }
        .main .block-container {
            padding-top: 2rem;
            padding-right: 2rem;
            padding-left: 2rem;
            padding-bottom: 2rem;
        }
        </style>
        """,
        unsafe_allow_html=True
    )

def init_session_state():
    """
    Streamlitのセッション状態を初期化
    """
    if "global_llm_provider" not in st.session_state:
        st.session_state["global_llm_provider"] = "OpenAI"
    if "global_llm_model" not in st.session_state:
        st.session_state["global_llm_model"] = "gpt-4o-mini"
    if "global_temperature" not in st.session_state:
        st.session_state["global_temperature"] = 0.3
    if "vector_index_id" not in st.session_state:
        st.session_state["vector_index_id"] = "your-vector-index-id"
    if "vector_endpoint_id" not in st.session_state:
        st.session_state["vector_endpoint_id"] = "your-vector-endpoint-id"
    if "user_info" not in st.session_state:
        st.session_state["user_info"] = {"email": "test@example.com", "role": "admin"}
