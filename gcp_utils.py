import os
import logging
from google.cloud import storage
from google.cloud import firestore
import google.cloud.logging
from datetime import datetime

# 取得 logger
logger = logging.getLogger(__name__)

# 全域的 Client (Lazy Initialization)
_storage_client = None
_firestore_client = None
_gcs_bucket_name = None

def setup_gcp_logging():
    """初始化 Google Cloud Logging"""
    try:
        # 實例化 Cloud Logging 客戶端
        client = google.cloud.logging.Client()
        # 設定為預設的 logging handler，這會自動擷取標準 logging 模組的日誌
        client.setup_logging()
        logger.info("成功初始化 Google Cloud Logging")
    except Exception as e:
        logger.warning(f"無法初始化 Google Cloud Logging (可能是本地環境沒有權限): {e}")

def get_storage_client():
    global _storage_client
    if _storage_client is None:
        _storage_client = storage.Client()
    return _storage_client

def get_firestore_client():
    global _firestore_client
    if _firestore_client is None:
        _firestore_client = firestore.Client()
    return _firestore_client

def get_bucket_name():
    global _gcs_bucket_name
    if _gcs_bucket_name is None:
        _gcs_bucket_name = os.environ.get("GCS_BUCKET_NAME", "your-default-bucket-name")
    return _gcs_bucket_name

def upload_html_to_gcs(article_id: str, html_content: str):
    """上傳 HTML 到 Cloud Storage"""
    try:
        client = get_storage_client()
        bucket = client.bucket(get_bucket_name())
        blob = bucket.blob(f"translated_articles/{article_id}.html")
        blob.upload_from_string(html_content, content_type="text/html")
        logger.info(f"已成功上傳 {article_id}.html 到 Cloud Storage ({get_bucket_name()})")
        return True
    except Exception as e:
        logger.error(f"上傳至 Cloud Storage 失敗: {e}")
        return False

def get_cached_html_from_gcs(article_id: str) -> str | None:
    """從 Cloud Storage 取得快取的 HTML"""
    try:
        client = get_storage_client()
        bucket = client.bucket(get_bucket_name())
        blob = bucket.blob(f"translated_articles/{article_id}.html")
        if blob.exists():
            return blob.download_as_text()
    except Exception as e:
        logger.error(f"從 Cloud Storage 讀取失敗: {e}")
    return None

def save_translation_log_to_firestore(article_id: str, url: str, status: str, original_html: str, translated_html: str, error_msg: str = None):
    """將翻譯紀錄儲存到 Firestore"""
    try:
        db = get_firestore_client()
        doc_ref = db.collection(u'translation_logs').document()
        doc_ref.set({
            u'timestamp': firestore.SERVER_TIMESTAMP,
            u'local_time': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            u'article_id': article_id,
            u'url': url,
            u'status': status,
            u'original_html': original_html,
            u'translated_html': translated_html,
            u'error_msg': error_msg
        })
        # logger.info("成功寫入翻譯日誌到 Firestore")
    except Exception as e:
        logger.error(f"寫入 Firestore 失敗: {e}")
