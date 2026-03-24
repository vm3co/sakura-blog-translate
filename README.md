# 櫻坂 Blog 翻譯程式

自動抓取 [sakurazaka46.com](https://sakurazaka46.com) 的部落格文章，並以日中對照格式呈現。

---

## 環境需求

- Python 3.11+
- [uv](https://github.com/astral-sh/uv)（套件管理工具）

---

## 設定環境變數

在專案根目錄建立 `.env` 檔案，填入以下內容：

```env
# 必填：Gemini API 金鑰（預設翻譯引擎）
GEMINI_API_KEY=your_gemini_api_key_here

# 選填：若要使用 DeepL 翻譯，請一併填入
DEEPL_API_KEY=your_deepl_api_key_here
```

---

## 安裝uv

```bash
# 安裝 uv（若尚未安裝）
pip install uv

# 建立虛擬環境並安裝相依套件
uv sync
```

---

## 啟動伺服器

```bash
uv run python main.py
```

- 啟動後，開啟瀏覽器訪問：[http://localhost:8095](http://localhost:8095)
- 完成翻譯的頁面，會儲存到 `templates` 資料夾中。

---

## 切換翻譯引擎（Gemini / DeepL）

程式預設使用 **Gemini(gemini-2.5-flash)** 進行翻譯。
> ⚠️ 請確認 `.env` 中已設定 `GEMINI_API_KEY`，否則程式無法正常運作。

如果想改用 **DeepL**，請打開 `japan_translator.py`，找到 `translate_webpage` 函式，將 model 參數從 `"gemini"` 改為 `"deepL"`：

```python
# 預設 model="gemini"
translate_webpage(url_to_scrape, output_file="translated_page.html", model="gemini")

# 若要切換成 DeepL：
translate_webpage(url_to_scrape, output_file="translated_page.html", model="deepL")
```

> ⚠️ 使用 DeepL 時，請確認 `.env` 中已設定 `DEEPL_API_KEY`。
