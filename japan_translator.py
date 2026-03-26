# -*- coding: utf-8 -*-
"""
Created on Tue Oct 28 14:26:11 2025

@author: 2501053
"""

from bs4 import BeautifulSoup
import os
import deepl
import time
from dotenv import load_dotenv
import logging
import sqlite3
from datetime import datetime

import google.generativeai as genai
from google.generativeai import types
import gcp_utils

import html_processor


load_dotenv()

# --- 設定常數 ---
ARTICLES_DIR = os.path.join("templates", "translated_articles")

# 獲取一個 logger 實例
logger = logging.getLogger(__name__)


# --- 設定 deepl API 的端點
DEEPL_API_KEY = os.environ.get("DEEPL_API_KEY")
deepl_client = deepl.DeepLClient(DEEPL_API_KEY)

# --- 設定 Gemini Client ---
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-2.5-flash')

# --- 這是 LLM 的核心：提示 (Prompt) ---
# SYSTEM_PROMPT = """
# 你是一名專業的日中翻譯家，尤其擅長翻譯日本偶像部落格(Blog)。
# 你的任務是將使用者提供的 HTML 內容，從日文翻譯成「自然、口語化、符合粉絲語氣」的「繁體中文」。

# **翻譯規則 (極度重要)：**
# 1.  **保持結構**：你「必須」完整保留所有的 HTML 標籤 (如 <div>, <p>, <span>, <a>, <img>) 及其所有屬性 (如 class, style, href, src)。
# 2.  **只翻文字**：只翻譯標籤內的日文文字。
# 3.  **精準翻譯**：
#     * 人名（例如：谷口愛季）如果沒有約定俗成的中文翻譯，請保持日文漢字。
#     * 準確傳達原文的語氣、情緒。
# 4.  **輸出格式**：你的回答「只能」包含翻譯後的 HTML 內容，不要有任何額外的說明或引言 (例如「好的，這是翻譯結果：」)。
# """
SYSTEM_PROMPT = """
你是一名專業的日中翻譯家，尤其擅長翻譯日本偶像部落格(Blog)。
你的任務是將使用者提供的 HTML 內容，從日文翻譯成「日中對照」的格式，並以「繁體中文」呈現。

**翻譯規則 (極度重要)：**

1.  **翻譯格式 (日中並列 + 樣式)**：
    * 你必須遍歷所有 HTML 標籤，找到**每一個**直接包含日文文字的節點 (text node)。
    * 你「必須保留」原始的日文文字。
    * 在該日文文字的**正後方**，依序插入以下 HTML 程式碼：
        1.  一個 `<br/>` 標籤
        2.  一個 `<span style="color: #008080;">` 標籤 (使用這個 Teal 藍綠色)
        3.  翻譯後的「繁體中文」
        4.  一個 `</span>` 閉合標籤
        5.  一個 `<br/>` 標籤

    * **範例 (前):** `<p>こんにちは</p>`
    * **範例 (後):** `<p>こんにちは<br/><span style="color: #008080;">你好</span><br/></p>`
    * **範例 (前):** `<span>熱気と盛り上がり</span>`
    * **範例 (後):** `<span>熱気と盛り上がり<br/><span style="color: #008080;">熱情與高漲的氣氛</span><br/></span>`
    
2.  **保持結構**：
    * 你「必須」完整保留所有的 HTML 標籤 (如 <div>, <p>, <a>, <img>) 及其所有屬性 (如 class, src)。
    * 範例中的 `<img>` 標籤和它所有的屬性都必須原封不動地保留。

3.  **翻譯內容**：
    * 只翻譯有意義的日文句子或片語。
    * 對於純粹的排版符號 (如 `‪𓂃 𓈒𓏸◌‬`) 或大量的 `&nbsp;`，請直接保留它們，**不要** 試圖在它們後面插入翻譯。
    * 人名（例如：松田里奈）如果沒有約定俗成的中文翻譯，請保持日文漢字。
    * 如果是"ちゃん"、"さん"、"くん"結尾的人名，直接保持日文名假名即可。
    * 準確傳達原文的語氣、情緒。

4.  **輸出格式**：你的回答「只能」包含修改並翻譯後的 HTML 內容，不要有任何額外的說明或引言 (例如「好的，這是翻譯結果：」)。
"""

def get_translation_deepL(text_to_translate):
    """
    呼叫 deepL API
    """
    try:
        result_test = deepl_client.translate_text(
            text_to_translate, 
            target_lang="ZH-HANT",
            tag_handling="html"
            )
        
        return result_test.text.strip().replace("`", "")
    except Exception as e:
        logger.error(f"deepL API 呼叫失敗: {e}")
        return None

def get_translation_gemini(html_to_translate):
    """
    呼叫 Gemini API 進行 HTML 翻譯
    """
    try:
        
        # 建立模型並開始聊天傳送 HTML
        response = model.generate_content(
            contents=[html_to_translate, SYSTEM_PROMPT]
        )

        translated_html = response.text
        return translated_html

    except Exception as e:
        logger.error(f"Gemini API 呼叫失敗: {e}")
        return None

def translate_webpage(url_to_scrape, article_id, model="gemini"):
    """
    主程式：抓取、翻譯並儲存網頁
    """
    # 抓取網頁
    soup = html_processor.prepare_soup(url_to_scrape)
    
    # 路徑修復
    new_soup = html_processor.fix_url(soup, url_to_scrape)

    # --- 關鍵：遍歷所有需要翻譯的文字標籤 ---
    # (您可以根據目標網站自訂標籤清單)
    tags_to_translate = new_soup.select(".box-article")

    logger.info(f"開始翻譯 {len(tags_to_translate)} 個 .box-article 區塊...")
    count = 0
    for tag in tags_to_translate:
        html_to_translate = str(tag)
        # --- 呼叫 API ---
        if model == "gemini":
            time.sleep(1)
            translated_html_string = get_translation_gemini(html_to_translate) 
        elif model == "deepL":
            translated_html_string = get_translation_deepL(html_to_translate)   
        else:
            continue
        
        # --- 替換內容 ---
        if translated_html_string is None:
            return None
        if translated_html_string != html_to_translate: # 確保翻譯成功
            error_msg = None
            try:
                # 將翻譯回來的 "HTML字串" 重新解析為 "BeautifulSoup 標籤"，並替換舊標籤
                new_tag = BeautifulSoup(translated_html_string, 'html.parser')
                tag.replace_with(new_tag)
                status = "success"
            except Exception as e:
                logger.error(f"解析翻譯後的HTML時出錯: {e}")
                status = "fail"
                error_msg = str(e)
            finally:
                gcp_utils.save_translation_log_to_firestore(
                    article_id,
                    url_to_scrape,
                    status,
                    html_to_translate, 
                    translated_html_string,
                    error_msg
                )
        count += 1
        logger.info(f"已翻譯 {count} / {len(tags_to_translate)} 個區塊...")
            
    logger.info(f"翻譯完成！")
    return str(new_soup)

if __name__ == "__main__":
    # 範例：翻譯一個日本網站
    target_url = "https://sakurazaka46.com/s/s46/diary/detail/66643?ima=0000&cd=blog" # 範例網站
    translate_webpage(target_url, "test.html", "gemini")
    # translate_webpage(target_url, "山田_deepL.html", "deepL")
    
