from google.cloud import secretmanager

def get_secret(secret_name: str) -> str:
    """
    Secret Managerからシークレットを取得
    """
    # TODO: Secret Managerからシークレットを取得する実装
    # 本番環境では適切な認証情報を使用
    return f"DUMMY_{secret_name}_SECRET"
