import requests
import fitz  # PyMuPDF
import csv
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm
import time
import re
from urllib.parse import urljoin

# --- 全域設定 ---
BASE_URL = "https://www.federalreserve.gov"
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}


# --- 1. 連結爬取器 (整合 2000-2019 HTML 與 2020+ PDF) ---
def get_all_statement_links(start_year=2000, end_year=2025):
    """
    爬取聯準會所有年份的 Statement 連結。
    整合了「歷史頁面(文字搜尋)」與「新版行事曆(檔名搜尋)」兩種邏輯。
    """
    statement_urls = []
    seen_urls = set()  # 用來去重
    print(f"正在搜尋 {start_year} 到 {end_year} 年的會議連結...")

    # --- 第一部分：針對 2019 (含) 以前的歷史頁面 ---
    # 這些頁面通常用 "Statement" 文字當作連結
    historical_years = [y for y in range(start_year, end_year + 1) if y < 2020]

    for year in historical_years:
        page_url = f"{BASE_URL}/monetarypolicy/fomchistorical{year}.htm"
        try:
            resp = requests.get(page_url, headers=HEADERS, timeout=10)
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.content, 'html.parser')
                # 舊版邏輯：找文字是 "Statement" 的連結
                links = soup.find_all('a', string=re.compile(r'Statement', re.IGNORECASE))

                # 如果找不到，嘗試找舊版 HTML 連結結構
                if not links:
                    links = soup.find_all('a', href=re.compile(r'/boarddocs/press/monetary/.*', re.IGNORECASE))

                for link in links:
                    href = link.get('href')
                    if href and "goals" not in href.lower():  # 排除長期目標文件
                        full_url = urljoin(page_url, href)
                        if full_url not in seen_urls:
                            statement_urls.append({"year": year, "url": full_url, "type": "History-HTML"})
                            seen_urls.add(full_url)
            time.sleep(0.5)
        except Exception as e:
            print(f"  [略過] {year} 年歷史頁面讀取失敗: {e}")

    # --- 第二部分：針對 2020 (含) 以後的新版行事曆 ---
    # 這些通常都在同一個頁面，且連結文字是 "PDF"，所以我們要改抓 href 特徵
    if end_year >= 2020:
        calendar_url = f"{BASE_URL}/monetarypolicy/fomccalendars.htm"
        print(f"正在掃描新版行事曆頁面: {calendar_url}")
        try:
            resp = requests.get(calendar_url, headers=HEADERS, timeout=10)
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.content, 'html.parser')

                # 新版邏輯：直接抓取 href 符合 "monetaryYYYYMMDDa1.pdf" 規則的連結
                # a1 通常代表 Statement (a2 是 Implementation Note)
                pdf_links = soup.find_all('a', href=re.compile(r'monetary\d{8}a1\.pdf'))

                for link in pdf_links:
                    href = link.get('href')
                    full_url = urljoin(calendar_url, href)

                    # 從檔名中提取年份來過濾 (monetary20250129a1.pdf)
                    match = re.search(r'monetary(\d{4})', href)
                    if match:
                        file_year = int(match.group(1))
                        if start_year <= file_year <= end_year:
                            if full_url not in seen_urls:
                                statement_urls.append({"year": file_year, "url": full_url, "type": "Modern-PDF"})
                                seen_urls.add(full_url)
        except Exception as e:
            print(f"  [錯誤] 新版行事曆頁面讀取失敗: {e}")

    # 根據年份排序 (新到舊)
    statement_urls.sort(key=lambda x: x['url'], reverse=True)

    print(f"總共找到 {len(statement_urls)} 個聲明連結。")
    return [item['url'] for item in statement_urls]


# --- 2. 內容處理函式 (處理 PDF 與 HTML) ---
def process_fomc_url(url, timeout=30):
    result = {"url": url, "text": "", "file_type": "unknown", "error": None}

    try:
        response = requests.get(url, headers=HEADERS, timeout=timeout)
        response.raise_for_status()

        content_type = response.headers.get('Content-Type', '').lower()

        # --- 處理 PDF ---
        if 'application/pdf' in content_type or url.lower().endswith('.pdf'):
            result['file_type'] = 'pdf'
            text_content = ""
            with fitz.open(stream=response.content, filetype="pdf") as doc:
                for page in doc:
                    text_content += page.get_text()
            result['text'] = text_content

        # --- 處理 HTML (舊版) ---
        else:
            result['file_type'] = 'html'
            soup = BeautifulSoup(response.content, 'html.parser')

            # 抓取主要內容區
            article = soup.find('div', id='article') or \
                      soup.find('div', id='content') or \
                      soup.find('div', class_='col-xs-12')

            if not article:
                article = soup.find('body')

            # 清除雜訊
            if article:
                for junk in article(["script", "style", "nav", "footer", "header"]):
                    junk.decompose()
                result['text'] = article.get_text(separator='\n').strip()
            else:
                result['error'] = "HTML parsing failed: No content found"

        if not result['text'].strip() and not result['error']:
            result['error'] = "Warning: Extracted text is empty."

    except Exception as e:
        result['error'] = str(e)

    return result


# --- 3. 主程式 ---
def batch_scrape_fomc_unified(output_csv="fomc_history_2000_2025.csv", max_workers=10):
    # 步驟 1: 取得所有連結
    urls = get_all_statement_links(2000, 2025)

    if not urls:
        print("未找到連結，程式結束。")
        return

    results = []

    # 步驟 2: 平行下載
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_url = {executor.submit(process_fomc_url, url): url for url in urls}

        for future in tqdm(as_completed(future_to_url), total=len(urls), desc="下載並解析內容"):
            results.append(future.result())

    # 步驟 3: 存檔
    successful = [r for r in results if not r['error'] or "Warning" in str(r['error'])]
    # 再次按網址排序確保 CSV 順序整齊
    successful.sort(key=lambda x: x['url'], reverse=True)

    print(f"\n處理完成！")
    print(f"成功擷取: {len(successful)} 筆 (包含 PDF 與 HTML)")

    if successful:
        with open(output_csv, 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.DictWriter(f, fieldnames=["url", "file_type", "text"])
            writer.writeheader()
            for item in successful:
                writer.writerow({k: item.get(k) for k in ["url", "file_type", "text"]})
        print(f"所有資料已合併儲存至: {output_csv}")


if __name__ == "__main__":
    batch_scrape_fomc_unified()