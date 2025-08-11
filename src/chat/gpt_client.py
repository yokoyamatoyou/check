"
GPTクライアントモジュール

LLMFactoryと連携し、チャット応答生成の主要なロジックを担う。
- ファイル解析結果やWeb検索結果をプロンプトに統合
- CoT (Chain of Thought) プロンプトの適用
"
from typing import List, Dict, Any, Tuple
import logging

from src.rag.llm_factory import LLMFactory
# from src.chat.web_search import WebSearcher
# from src.chat.file_analyzer import FileAnalyzer

class GPTClient:
    """
    チャット応答を生成するクライアント
    """
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.llm_factory = LLMFactory()
        # self.web_searcher = WebSearcher() # TODO
        # self.file_analyzer = FileAnalyzer() # TODO
        self.logger.info("GPTClient initialized.")

    def generate_response(self, 
                          messages: List[Dict[str, str]],
                          model_name: str = "gpt-4.1-mini",
                          use_web_search: bool = False,
                          attached_files: List[Any] = None) -> Tuple[str, str]:
        """
        ユーザーの入力に対して、思考プロセスと最終的な回答を生成する
        """
        self.logger.info(f"Generating response with model: {model_name}, web_search: {use_web_search}")

        thought_process = "--- 思考プロセス ---
"

        # TODO: ファイル解析とWeb検索の実装
        file_context = ""
        web_context = ""
        thought_process += "1. ファイル解析とWeb検索は現在スキップされています（ダミー）。\n"

        thought_process += "2. 最終的なプロンプトを構築しています...\n"
        final_prompt_messages = self._construct_final_prompt_messages(messages, file_context, web_context)
        thought_process += "   - プロンプト構築完了。\n"

        thought_process += f"3. LLM ({model_name}) を呼び出しています...\n"
        llm = self.llm_factory.get_model(model_name)
        if not llm:
            error_msg = "指定されたモデルの初期化に失敗しました。APIキーが設定されているか確認してください。"
            self.logger.error(error_msg)
            return error_msg, thought_process + f"   - エラー: {error_msg}\n"
        
        try:
            final_answer = llm.invoke(final_prompt_messages, model=model_name)
            thought_process += "4. LLMから応答を受信しました。\n"
        except Exception as e:
            self.logger.error(f"LLM invocation failed: {e}", exc_info=True)
            final_answer = f"エラー：LLMの呼び出し中に問題が発生しました。詳細はログを確認してください。"
            thought_process += f"   - エラー: {e}\n"

        return final_answer, thought_process

    def _construct_final_prompt_messages(self, 
                                         messages: List[Dict[str, str]], 
                                         file_context: str, 
                                         web_context: str) -> List[Dict[str, str]]:
        """
        LLMに渡すためのメッセージリストを構築する
        """
        system_prompt = """
        あなたは優秀なAIアシスタントです。以下の情報を総合的に判断し、ユーザーの質問に日本語で回答してください。
        """
        
        # システムプロンプトとコンテキストを最初のメッセージとして設定
        context_info = ""
        if file_context:
            context_info += f"--- 添付ファイルからの情報 ---\n{file_context}\n\n"
        if web_context:
            context_info += f"--- Web検索からの情報 ---\n{web_context}\n\n"
        
        # 履歴の前にシステムプロンプトとコンテキストを挿入
        prompt_messages = [{"role": "system", "content": system_prompt + "\n" + context_info}] + messages
        
        return prompt_messages
