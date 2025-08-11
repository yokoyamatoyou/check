# エラー修正とアルゴリズム改善計画

**合意日:** 2025-08-11

---

## 1. 基本方針

現在の「複数OCRのレース方式」から、「複数エンジン（LLM＋OCR）の結果を統合する方式」へアーキテクチャを刷新する。
目標は、単なるテキスト抽出に留まらず、検索精度を向上させるためのリッチで創造的なメタデータを生成すること。

## 2. アーキテクチャと各エンジンの役割

### **主エンジン: GPT-5mini (OpenAI Vision Model)**
- **役割:** 画像の総合的な理解と、創造的なメタデータ生成。
- **処理内容:**
    1. 画像からテキストを正確に抽出する（OCR）。
    2. 画像の視覚的な内容を要約・分析する。
    3. 抽出したテキストや画像の内容から連想を広げ、検索に有効なキーワードやタグを**創造的に生成**する。
- **実装:** `_process_with_openai_vision` メソッドとして実装。OpenAI APIのJSONモードを利用し、構造化された出力を得る。

### **補助エンジン1: EasyOCR**
- **役割:** 構造的なメタデータの補足。
- **処理内容:** GPT-5miniの出力には含まれない、各単語やテキストブロックの**バウンディングボックス（位置座標）情報**を抽出する。

### **補助エンジン2: Tesseract**
- **役割:** 定量的なメタデータの補足。
- **処理内容:** 総単語数など、統計的な情報を抽出する。

## 3. 新しい処理フロー (`process_image`)

1.  **並列実行:** GPT-5mini, EasyOCR, Tesseractの3つのエンジンを同時に（並列で）実行する。
2.  **結果の統合 (マージ):**
    - **GPT-5mini**の出力を「正」とし、テキストと創造的メタデータを取得する。
    - **EasyOCR**と**Tesseract**の結果から、バウンディングボックスや単語数といった補足的なメタデータを取り出す。
    - 全ての情報を一つに統合し、最終的な成果物とする。

## 4. 必須メタ情報

- 全ての処理対象ファイルについて、以下の情報を必ずメタデータに含める。
    - **作成日 (`creation_date`)**
    - **最終更新日 (`modification_date`)**
- `os.path.getctime()` と `os.path.getmtime()` を利用して取得する。取得できない場合は「不明」とする。

## 5. 修正対象のエラー

- `ImportError: cannot import name 'vision' from 'google.cloud'`
    - **解決策:** Cloud Visionへの依存コードを削除することで解決する。
- `SyntaxError` in `pages/1_高精度RAG検索.py`
- `SyntaxError` in `pages/2_生成AI対話.py`

## 6. 【厳守】依存関係ファイルの変更ルール

以下の4つのファイルは、デプロイの安定性に直結するため、原則として変更しない。

- `C:\Users\Ne\Downloads\GCP\constraints.txt`
- `C:\Users\Ne\Downloads\GCP\requirements.txt`
- `C:\Users\Ne\Downloads\GCP\deployment\Dockerfile`
- `C:\Users\Ne\Downloads\GCP\deployment\cloudbuild.yaml`

やむを得ず変更が必要な場合は、**ライブラリ等の「削除」のみを許可**とし、追加やバージョンの変更は行わない。また、これらのファイルに触れた場合は、必ず`status.md`にその記録を残す。
