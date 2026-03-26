# 櫻坂 Blog 翻譯程式

自動抓取 [sakurazaka46.com](https://sakurazaka46.com) 的部落格文章，並以日中對照格式呈現。
本專案已改寫為無狀態 (Stateless) 架構，專為 **Google Cloud Run** 部署所設計。翻譯後的 HTML 將存放於 Google Cloud Storage，翻譯日誌存放於 Firestore，系統日誌存放於 Cloud Logging。

---

## 環境需求

- Python 3.11+
- [uv](https://github.com/astral-sh/uv)（套件管理工具）
- Google Cloud SDK (gcloud CLI) - 用於部屬與本地端登入

---

## 設定環境變數

在專案根目錄建立 `.env` 檔案，填入以下內容：

```env
# 必填：Gemini API 金鑰（預設翻譯引擎）
GEMINI_API_KEY=your_gemini_api_key_here

# 選填：若要使用 DeepL 翻譯，請一併填入
DEEPL_API_KEY=your_deepl_api_key_here

# 必填：Google Cloud Storage 的 Bucket 名稱（用於存放翻譯後的 HTML）
GCS_BUCKET_NAME=your_gcs_bucket_name_here
```

---

## 安裝與本地測試

### 1. 安裝環境
```bash
# 建立虛擬環境並安裝相依套件 (包含 GCP 套件)
uv sync
```

### 2. 本地端 Google Cloud 認證 (要在本機執行必須先登入 GCP)
程式由於改用 GCP 的 Storage 與 Firestore，本地端並無這些服務。要在電腦上測試，需要讓程式能夠使用您 GCP 專案的權限：
```bash
# 登入並取得應用程式預設憑證 (Application Default Credentials)
gcloud auth application-default login
```

### 3. 啟動伺服器
```bash
uv run python main.py
```
- 啟動後，開啟瀏覽器訪問：[http://localhost:8095](http://localhost:8095)
- 完成翻譯的頁面，會自動上傳到您的 **Google Cloud Storage (GCS)** Bucket 中。
- 翻譯紀錄將會寫入 **Cloud Firestore** 的 `translation_logs` 集合中。
- API 日誌將自動上傳至 **Cloud Logging**。

---

## 切換翻譯引擎（Gemini / DeepL）

在 `main.py` 呼叫 `translate_webpage` 的地方切換模型。
> ⚠️ 請確認 `.env` 中已設定對應的 API KEY，否則程式無法正常運作。

```python
# 預設 model="gemini"
translate_webpage(original_article_url, article_id, model="gemini")

# 若要切換成 DeepL：
translate_webpage(original_article_url, article_id, model="deepL")
```

---

## 部署至 Google Cloud Run

本系統已改寫為無狀態架構，完全兼容 Google Cloud Run。

### 步驟 1：準備 Google Cloud Project
1. 登入 [Google Cloud Console](https://console.cloud.google.com/) 並建立專案(在左上角點擊並建立一個新的 Project)。
2. 啟用必要的 API：
   - [Cloud Run](https://console.cloud.google.com/run)
   - [Cloud Storage](https://console.cloud.google.com/storage)
   - [Cloud Firestore](https://console.cloud.google.com/firestore)
3. 在 Firestore 主控台建立資料庫：
   - [Cloud Firestore](https://console.cloud.google.com/firestore)
   - 點擊「建立資料庫」，選取版本「Standard版」。
   - 注意資料庫ID不需更改，維持原名稱「(default)」。
   - 選擇 Native mode（原生模式）。
   - 選擇「區域」> 選擇與您 Cloud Run 預計部署於相近的地區（如 `asia-east1` 台灣）。
4. 在 Cloud Storage 主控台建立一個 Bucket：
   - [Cloud Storage](https://console.cloud.google.com/storage)
   - 點擊「建立 Bucket」。
   - 取名並將名稱記下。
   - 選擇「Region (可在單一地區中提供最低延遲)」> 選擇與您 Cloud Run 預計部署於相近的地區（如 `asia-east1` 台灣）。
   - 選擇「設定預設級別」>「Standard」。
5. 部屬金鑰(`Google Cloud Secret Manager`)：
   - 把金鑰存進 Secret Manager：
        - [Secret Manager](https://console.cloud.google.com/security/secret-manager)
        - 點擊上方的 「建立機密 (Create Secret)」。
        - 名稱：輸入 GEMINI_API_KEY（建議跟環境變數同名，比較好記）。
        - 機密值：把你的 Gemini API Key 貼在這裡。
        - 點擊最下方的 「建立機密」。
        - (DeepL 的金鑰，重複這個動作建立另一個 DEEPL_API_KEY)
   - 發保險箱鑰匙給 Cloud Run：
        - [IAM](https://console.cloud.google.com/iam-admin/iam)
        - 找到結尾是 @developer.gserviceaccount.com 的「預設運算服務帳戶」(也就是之前加 Storage 和 Firestore 權限的那個帳號)。
        - 點擊旁邊的鉛筆圖示編輯，點擊「新增其他角色」。
        - 搜尋並選擇 Secret Manager Secret Accessor (中文名稱叫：機密管理員機密存取者)。
        - 按下儲存。
### 步驟 2：使用 Google Cloud CLI 部署

請確定您的終端機已經安裝了 [Google Cloud SDK (gcloud CLI)](https://cloud.google.com/sdk/docs/install) 並已登入：
```bash
# 登入 GCP 並設定專案
gcloud auth login
gcloud config set project <您的專案ID>
```

**直接部署原始碼 (最推薦的方式)**：
```bash
gcloud run deploy sakura-translator \
  --source . \
  --region asia-east1 \
  --allow-unauthenticated \
  --set-env-vars GCS_BUCKET_NAME=<您剛才建立的bucket名稱> \
  --set-secrets GEMINI_API_KEY=GEMINI_API_KEY:latest,DEEPL_API_KEY=DEEPL_API_KEY:latest

# 如果你沒有部屬金鑰的話，就直接把金鑰寫在環境變數，但這建議是在測試環境使用
gcloud run deploy sakura-translator \
  --source . \
  --region asia-east1 \
  --allow-unauthenticated \
  --set-env-vars GCS_BUCKET_NAME=<您剛才建立的bucket名稱> \
  --set-env-vars GEMINI_API_KEY=您的GeminiKey \
  --set-env-vars DEEPL_API_KEY=您的DeepLKey

```

> 💡 **進階安全提示**：在實際的生產環境中，建議使用 `Google Cloud Secret Manager` 來管理 API Key，而非直接寫在環境變數。

### 步驟 3：驗證部署
部署完成後，命令列終端機會輸出一個 Cloud Run 給您的服務網址（例如 `https://sakura-translator-xxxxxx-de.a.run.app`）。
1. **瀏覽首頁擷取清單**：打開該網址，應該要能看到原本網站的櫻坂文章列表頁。
2. **點擊測試翻譯**：點入一篇文章，觀察 Cloud Run 啟動抓取與翻譯功能。翻譯成功後，文章應能被顯示出來。
3. **查閱 GCS 快取**：前往 Cloud Storage 的 Bucket 裡，檢查是否有成功建立名為 `translated_articles/xxxx.html` 的檔案。
4. **查閱 Firestore 紀錄**：前往 Firestore，檢查 `translation_logs` Collection 內是否有該次翻譯的詳細資料。
5. **查閱 Cloud Logging 日誌**：在 Cloud Run 主控台的服務詳細頁面，點擊「紀錄(Logs)」，您應該會看到 FastAPI 以及程式裡所呼叫的 `logger.info(...)` 正在正確輸出。
