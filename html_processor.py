# html_processor.py
import requests
from urllib.parse import urlparse, urljoin
from bs4 import BeautifulSoup
import logging
import re

# 獲取一個 logger 實例
logger = logging.getLogger(__name__)

def prepare_soup(url_to_scrape):
    """
    準備 BeautifulSoup 物件
    """
    logger.info(f"抓取網頁: {url_to_scrape} ...")
    try:
        page_response = requests.get(url_to_scrape, verify=False)
        page_response.raise_for_status()
    except requests.exceptions.RequestException as e:
        logger.error(f"抓取網頁失敗: {e}")
        return None

    soup = BeautifulSoup(page_response.content, 'html.parser')
    return soup

def fix_url(soup, url_to_scrape: str):
    """
    修復資源的相對路徑 (CSS, JS, Images)
    """
    logger.info("修復資源的相對路徑 (CSS, JS, Images)...")
    
    # 解析出 "https://sakurazaka46.com" 這樣的基礎 URL
    parsed_url = urlparse(url_to_scrape)
    base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"

    # 找出所有 <link> 標籤 (主要用於 CSS)
    for link_tag in soup.find_all('link', href=True):
        original_href = link_tag['href']
        absolute_href = urljoin(base_url, original_href)
        link_tag['href'] = absolute_href

    # 找出所有 <script> 標籤 (用於 JS)
    for script_tag in soup.find_all('script', src=True):
        original_src = script_tag['src']
        absolute_src = urljoin(base_url, original_src)
        script_tag['src'] = absolute_src

    # 找出所有 <img> 標籤 (用於 圖片)
    for img_tag in soup.find_all('img'):
        # 處理標準 src
        if img_tag.get('src'):
            original_src = img_tag['src']
            absolute_src = urljoin(base_url, original_src)
            img_tag['src'] = absolute_src
        
        # 處理 lazy loading (延遲載入) 常用的 data-src
        if img_tag.get('data-src'):
            original_data_src = img_tag['data-src']
            absolute_data_src = urljoin(base_url, original_data_src)
            img_tag['data-src'] = absolute_data_src

    # 找出所有帶有 style 屬性且包含 url() 的標籤 (用於背景圖片)
    for tag_with_style in soup.find_all(style=re.compile(r'url\s*\(([^)]+)\)')):
        original_style = tag_with_style['style']
        
        # 使用正規表示式尋找 url() 中的路徑
        match = re.search(r'url\s*\(([^)]+)\)', original_style)
        if match:
            # 取得括號內的路徑，並移除可能存在的引號
            url_path = match.group(1).strip().strip("'\"")
            
            # 轉換為絕對路徑
            absolute_url = urljoin(base_url, url_path)
            
            # 替換 style 屬性中的路徑
            tag_with_style['style'] = original_style.replace(url_path, absolute_url)
    
    return soup

if __name__ == "__main__":
    url_to_scrape = "https://sakurazaka46.com/s/s46/diary/blog/list?ima=0000"
    soup = prepare_soup(url_to_scrape)
    new_soup = fix_url(soup, url_to_scrape)
