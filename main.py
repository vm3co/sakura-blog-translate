# main.py
from urllib.parse import urlparse, urljoin
import os
from dotenv import load_dotenv
import logging

from fastapi import FastAPI, HTTPException, Query
from typing import Optional
from fastapi.responses import HTMLResponse, FileResponse
import uvicorn

import japan_translator 
import constants
import html_processor


load_dotenv()

BLOG_LIST_URL = constants.BLOG_LIST_URL
parsed_url = urlparse(BLOG_LIST_URL)
BASE_URL = f"{parsed_url.scheme}://{parsed_url.netloc}"
ARTICLES_DIR = os.path.join("templates", "translated_articles")

# 配置日誌
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(), # 輸出到控制台
        logging.FileHandler(constants.LOG_FILE_PATH, encoding='utf-8') # 輸出到檔案
    ]
)

# 獲取一個 logger 實例
logger = logging.getLogger(__name__)

app = FastAPI()

@app.get("/", response_class=HTMLResponse)
async def get_blog_list():
    """
    [On-Demand] 當使用者訪問首頁時，
    即時抓取官網列表頁，並修改連結。
    """
    logger.info("【訪客】: 正在請求網頁...")
    soup = html_processor.prepare_soup(BLOG_LIST_URL)
    if soup is None:
        raise HTTPException(status_code=503, detail="無法從來源網站抓取列表頁，請稍後再試。") # 這會被 FastAPI 捕獲並記錄

    # 2. 修復 CSS/JS/IMG 路徑
    new_soup = html_processor.fix_url(soup, BLOG_LIST_URL)
            
    return HTMLResponse(content=str(new_soup.prettify()))
    

@app.get("/s/s46/diary/detail/{article_id}", response_class=HTMLResponse)
async def get_original_article(
    # 路徑參數 (Path Parameters)
    article_id: str,
    # 查詢參數 (Query Parameters)
    ima: Optional[str] = Query(None, description="Image marker"), # 對應 ima=0000
    cd: Optional[str] = Query(None, description="Category code")  # 對應 cd=blog
):
    """
    [On-Demand + Cache] 當使用者點擊文章時，
    檢查快取，有就回傳，沒有就即時翻譯。
    """
    # 簡單的防護
    if not article_id.isdigit():
        raise HTTPException(status_code=400, detail="無效的 Article ID")
        
    file_path = os.path.join(ARTICLES_DIR, f"{article_id}.html")
    
    # --- 1. 檢查快取 (Cache Hit) ---
    if os.path.exists(file_path): # 檢查檔案是否存在
        logger.info(f"【快取命中】: {article_id}.html (正在回傳已儲存檔案)")
    else:
        # --- 2. 快取未命中 (Cache Miss) ---
        logger.info(f"【快取未命中】: {article_id}.html (正在觸發即時翻譯)")
        
        # 這會導致使用者等待 1-2 分鐘...
        try:
            # 重建官網的 URL
            original_article_url = f"{BASE_URL}/s/s46/diary/detail/{article_id}?ima=0000&cd=blog"
            
            # 呼叫主函式
            trans = japan_translator.translate_webpage(original_article_url, output_file=file_path)

            if trans is None:
                raise HTTPException(status_code=503, detail="翻譯失敗，請稍後再試。")
               
        except Exception as e:
            logger.error(f"翻譯失敗: {e}")
            raise HTTPException(status_code=503, detail=f"翻譯任務失敗: {e}")
    return FileResponse(file_path)


@app.get("/s/s46/diary/blog/list", response_class=HTMLResponse)
async def get_page(
    # 查詢參數 (Query Parameters)
    ima: Optional[str] = Query(None, description="Image marker"), # 對應 ima=0000
    page: Optional[str] = Query(None, description="Page"), # 對應 page=0
    cd: Optional[str] = Query(None, description="Category code"),  # 對應 cd=blog
    ct: Optional[str] = Query(None, description="Category code")  # 對應 ct=43
):
    """
    [On-Demand] 當使用者訪問其他頁時，
    即時抓取列表頁，並修改連結。
    """
    logger.info("【訪客】: 正在請求網頁...")
    if ct:
        url = f"{BASE_URL}/s/s46/diary/blog/list?{ima}=0000&ct={ct}"
    else:
        url = f"{BASE_URL}/s/s46/diary/blog/list?{ima}=0000&page={page}&cd={cd}"
    soup = html_processor.prepare_soup(url)
    if soup is None:
        raise HTTPException(status_code=503, detail="無法從來源網站抓取列表頁，請稍後再試。") # 這會被 FastAPI 捕獲並記錄

    # 2. 修復 CSS/JS/IMG 路徑
    new_soup = html_processor.fix_url(soup, url)
            
    return HTMLResponse(content=str(new_soup.prettify()))


    



if __name__ == "__main__":
    logger.info("啟動 FastAPI On-Demand 伺服器...")
    uvicorn.run(app, host="0.0.0.0", port=8095)