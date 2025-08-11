# --- build stage ---
FROM python:3.11-slim AS builder

# ビルドに必要になりがちな開発用ライブラリを広めに入れる
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    python3-dev \
    pkg-config \
    libffi-dev \
    libssl-dev \
    libxml2-dev \
    libxslt1-dev \
    libpq-dev \
    default-libmysqlclient-dev \
    git \
    curl \
 && rm -rf /var/lib/apt/lists/*

# 仮想環境を作成
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Python 依存関係のインストール
COPY requirements.txt constraints.txt ./
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -r requirements.txt -c constraints.txt


# --- run stage ---
FROM python:3.11-slim

# 実行に必要なランタイム依存
RUN groupadd -r streamlit && useradd -r -g streamlit streamlit && \
    apt-get update && apt-get install -y --no-install-recommends \
      tesseract-ocr \
      tesseract-ocr-jpn \
      tesseract-ocr-eng \
      poppler-utils \
      libgl1-mesa-glx \
      libglib2.0-0 \
      fonts-noto-cjk \
      curl \
    && rm -rf /var/lib/apt/lists/* && apt-get clean

# venv をコピーして PATH を通す
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# アプリ配置
WORKDIR /app
COPY --chown=streamlit:streamlit . .

# 不要ファイル削除（任意）
RUN find . -type f -name "*.pyc" -delete && \
    find . -type d -name "__pycache__" -delete

# 非 root で動かす
USER streamlit

# Streamlit の基本設定
ENV PYTHONUNBUFFERED=1 \
    STREAMLIT_SERVER_ADDRESS=0.0.0.0 \
    STREAMLIT_SERVER_HEADLESS=true

# Cloud Run は $PORT（デフォ 8080）で受ける
EXPOSE 8080

# （任意）ヘルスチェック：必要なら有効化
# HEALTHCHECK CMD curl --fail "http://localhost:${PORT:-8080}/_stcore/health" || exit 1

# 起動コマンド（シェル形式で $PORT を確実に使う）
CMD streamlit run app.py --server.port "$PORT" --server.address 0.0.0.0


