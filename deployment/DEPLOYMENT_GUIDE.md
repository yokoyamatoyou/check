# RAGシステム Google Cloud デプロイガイド

## 前提条件

### 1. Google Cloud プロジェクトの準備
```bash
# プロジェクトIDを設定
export PROJECT_ID="your-project-id"
gcloud config set project $PROJECT_ID

# 必要なAPIを有効化
gcloud services enable \
  cloudbuild.googleapis.com \
  run.googleapis.com \
  artifactregistry.googleapis.com \
  firestore.googleapis.com \
  aiplatform.googleapis.com \
  secretmanager.googleapis.com \
  identitytoolkit.googleapis.com \
  storage.googleapis.com
```

### 2. サービスアカウントの作成
```bash
# サービスアカウントを作成
gcloud iam service-accounts create rag-system-sa \
  --display-name="RAG System Service Account"

# 必要な権限を付与
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:rag-system-sa@$PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/datastore.user"

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:rag-system-sa@$PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/aiplatform.user"

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:rag-system-sa@$PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/storage.objectViewer"

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:rag-system-sa@$PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"
```

### 3. Secret Manager の設定
```bash
# APIキーをSecret Managerに保存
echo -n "your-openai-api-key" | gcloud secrets create openai-api-key --data-file=-
echo -n "your-anthropic-api-key" | gcloud secrets create anthropic-api-key --data-file=-
echo -n "your-google-api-key" | gcloud secrets create google-api-key --data-file=-
```

## デプロイ手順

### 1. ローカルテスト
```bash
# アプリケーションの動作確認
streamlit run app.py

# Dockerイメージのビルドテスト
docker build -f deployment/Dockerfile -t rag-system:test .
docker run -p 8501:8501 rag-system:test
```

### 2. Cloud Build でのデプロイ
```bash
# Cloud Build を実行
gcloud builds submit --config deployment/cloudbuild.yaml

# または、GitHubと連携して自動デプロイ
# GitHubリポジトリにプッシュすると自動的にデプロイされます
```

### 3. 手動デプロイ（オプション）
```bash
# Dockerイメージをビルド
docker build -f deployment/Dockerfile -t gcr.io/$PROJECT_ID/rag-system:$COMMIT_SHA .

# Artifact Registryにプッシュ
docker push gcr.io/$PROJECT_ID/rag-system:$COMMIT_SHA

# Cloud Runにデプロイ
gcloud run deploy rag-system \
  --image gcr.io/$PROJECT_ID/rag-system:$COMMIT_SHA \
  --region asia-northeast1 \
  --platform managed \
  --allow-unauthenticated \
  --service-account rag-system-sa@$PROJECT_ID.iam.gserviceaccount.com \
  --memory 2Gi \
  --cpu 2 \
  --max-instances 10 \
  --min-instances 0 \
  --timeout 300
```

## 環境変数の設定

### 1. Cloud Run 環境変数の設定
```bash
gcloud run services update rag-system \
  --region asia-northeast1 \
  --set-env-vars="GCP_PROJECT_ID=$PROJECT_ID,STREAMLIT_SERVER_HEADLESS=true"
```

### 2. Secret Manager からの環境変数取得
```bash
# Secret Managerから環境変数を取得して設定
gcloud run services update rag-system \
  --region asia-northeast1 \
  --set-env-vars="OPENAI_API_KEY=$(gcloud secrets versions access latest --secret=openai-api-key)"
```

## デプロイ後の確認

### 1. アプリケーションの動作確認
```bash
# デプロイされたURLを確認
gcloud run services describe rag-system --region asia-northeast1 --format="value(status.url)"

# ヘルスチェック
curl https://your-app-url/_stcore/health
```

### 2. ログの確認
```bash
# Cloud Run のログを確認
gcloud logs read "resource.type=cloud_run_revision AND resource.labels.service_name=rag-system" --limit=50
```

### 3. 監視の設定
```bash
# Cloud Monitoring でアラートを設定
gcloud alpha monitoring policies create \
  --policy-from-file=deployment/monitoring-policy.yaml
```

## トラブルシューティング

### よくある問題と解決方法

1. **メモリ不足エラー**
   - Cloud Run のメモリを増やす（2Gi → 4Gi）

2. **タイムアウトエラー**
   - タイムアウト時間を延長（300s → 600s）

3. **認証エラー**
   - サービスアカウントの権限を確認
   - Secret Manager のアクセス権限を確認

4. **外部API接続エラー**
   - APIキーの有効性を確認
   - ネットワーク設定を確認

## 運用管理

### 1. スケーリング設定
```bash
# 自動スケーリングの設定
gcloud run services update rag-system \
  --region asia-northeast1 \
  --max-instances 20 \
  --min-instances 1
```

### 2. バックアップ設定
```bash
# Firestore のバックアップ設定
gcloud firestore databases create --location=asia-northeast1
```

### 3. セキュリティ設定
```bash
# HTTPS の強制
gcloud run services update rag-system \
  --region asia-northeast1 \
  --set-env-vars="FORCE_HTTPS=true"
```

## 更新手順

### 1. コード更新時のデプロイ
```bash
# 新しいバージョンをデプロイ
gcloud builds submit --config deployment/cloudbuild.yaml

# または、特定のタグでデプロイ
gcloud run deploy rag-system \
  --image gcr.io/$PROJECT_ID/rag-system:latest \
  --region asia-northeast1
```

### 2. ロールバック手順
```bash
# 前のバージョンに戻す
gcloud run services update-traffic rag-system \
  --region asia-northeast1 \
  --to-revisions=rag-system-00001-abc=100
```

## コスト最適化

### 1. リソース使用量の監視
```bash
# コスト分析
gcloud billing budgets create \
  --billing-account=your-billing-account \
  --budget-amount=100.00USD \
  --budget-filter="project.id=$PROJECT_ID"
```

### 2. 自動スケーリングの最適化
```bash
# コスト効率の良い設定
gcloud run services update rag-system \
  --region asia-northeast1 \
  --min-instances 0 \
  --max-instances 5
```

