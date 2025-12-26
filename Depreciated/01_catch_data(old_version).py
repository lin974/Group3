import os
import re
import pandas as pd
import requests
from io import BytesIO
from pdfminer.high_level import extract_text

# 聯準會 FOMC 記者會日期列表 (2011 – 2025)
# 這是您爬蟲所需要的 YYYYMMDD 格式列表
FOMC_DATES = [
    '20251029', '20250917', '20250730', '20250618', '20250507', '20250319', '20250129',
    '20241211', '20240918', '20240612', '20240320',
    '20231213', '20231101', '20230920', '20230726', '20230614', '20230503', '20230322', '20230201',
    '20221214', '20221102', '20220921', '20220727', '20220615', '20220504', '20220316', '20220126',
    '20211215', '20210922', '20210616', '20210317',
    '20201216', '20201105', '20200916', '20200729', '20200610', '20200429', '20200315', '20200129',
    '20191211', '20191030', '20190918', '20190731', '20190619', '20190501', '20190320', '20190130',
    '20181219', '20180926', '20180613', '20180321',
    '20171213', '20170920', '20170614', '20170315',
    '20161214', '20160921', '20160615', '20160316',
    '20151216', '20150917', '20150617', '20150318',
    '20141217', '20140917', '20140618', '20140319',
    '20131218', '20130918', '20130619', '20130320',
    '20121212', '20120913', '20120620', '20120425', '20120125',
    '20111213', '20110921', '20110622', '20110427'
]

BASE_URL = "https://www.federalreserve.gov/mediacenter/files/FOMCpresconf"


def download_pdf(date):
    """根據日期下載 PDF 檔案內容到記憶體 (BytesIO)"""
    url = f"{BASE_URL}{date}.pdf"
    print(f"嘗試下載: {url}")
    try:
        response = requests.get(url, timeout=15)  # 延長 timeout
        # 檢查是否成功 (HTTP 200) 且內容為 PDF
        if response.status_code == 200 and 'application/pdf' in response.headers.get('Content-Type', ''):
            # 將二進制內容包裝在 BytesIO 中
            return BytesIO(response.content)
        elif response.status_code == 404:
            print(f"⚠️ {date}: 檔案不存在 (404 Not Found)。")
            return None
        else:
            print(f"⚠️ {date}: 下載失敗，狀態碼: {response.status_code}")
            return None
    except requests.exceptions.RequestException as e:
        print(f"❌ {date}: 連線錯誤: {e}")
        return None


def structure_transcript(pdf_content_io, date):
    """
    提取 PDF 文本並嘗試結構化。
    """
    data = []
    full_text = ""
    try:
        # 1. 提取所有文字
        full_text = extract_text(pdf_content_io)
        full_text = full_text.replace('\n', ' ').replace('\r', ' ').strip()

        # 2. 尋找 Q&A 環節的起始點
        qa_match = re.search(r'(QUESTION\s+AND\s+ANSWER\s+PERIOD|Questions\s+and\s+Answers)', full_text, re.IGNORECASE)

        # 3. 提取 Statement 部分
        statement_text = full_text[:qa_match.start()].strip() if qa_match else full_text

        if statement_text:
            data.append({
                'Date': date,
                'Speaker': 'CHAIR',
                'Section': 'Statement',
                'Question': '',
                'Text': statement_text,
                'Topic_Key': 'Opening Remarks'
            })

        # 4. 提取 Q&A 部分
        if qa_match:
            qa_text = full_text[qa_match.end():].strip()

            # 使用 Regex 分割發言者 (這是解析的重點與難點)
            # 模式: 匹配大寫主席名稱 (CHAIR POWELL/YELLEN/BERNANKE) 或 'QUESTION FROM...' 後跟冒號
            transactions = re.split(
                r'((?:CHAIR\s+(?:POWELL|YELLEN|BERNANKE)|QUESTION\s+FROM.*|MR\.\s+.*):\s*)',
                qa_text,
                flags=re.IGNORECASE
            )

            current_speaker = None
            current_question = ""

            # 遍歷分割後的內容
            for i, part in enumerate(transactions):
                part = part.strip()
                if not part:
                    continue

                # 識別發言者標籤 (例如: CHAIR POWELL: )
                if re.match(r'(CHAIR\s+(POWELL|YELLEN|BERNANKE)|QUESTION\s+FROM.*|MR\.\s+.*):', part, re.IGNORECASE):
                    current_speaker = part.replace(':', '').strip()
                # 識別發言內容
                elif current_speaker:
                    text_content = part

                    if current_speaker.startswith('QUESTION FROM') or (
                            re.match(r'MR\.\s+.*', current_speaker, re.IGNORECASE) and i > 0):
                        # 這是記者的問題 (假設 MR. X 在 Q&A 環節也是提問者)
                        current_question = text_content
                        data.append({
                            'Date': date,
                            'Speaker': 'REPORTER',
                            'Section': 'Q&A',
                            'Question': current_question,
                            'Text': text_content,
                            'Topic_Key': ''
                        })
                    elif current_speaker.startswith('CHAIR'):
                        # 這是主席的回答
                        data.append({
                            'Date': date,
                            'Speaker': 'CHAIR',
                            'Section': 'Q&A',
                            'Question': current_question,
                            'Text': text_content,
                            'Topic_Key': ''
                        })

                    current_speaker = None  # 重置發言者

    except Exception as e:
        print(f"❌ {date}: 結構化錯誤: {e}")
        # 在錯誤時，將整個文本作為單一記錄儲存
        if full_text:
            data.append({'Date': date, 'Speaker': 'ERROR', 'Section': 'Full Text', 'Question': '', 'Text': full_text,
                         'Topic_Key': 'Parsing Error'})

    return data


# ----------------- 主執行邏輯 -----------------
if __name__ == '__main__':
    all_records = []
    print(f"資料將處理 {len(FOMC_DATES)} 個日期...")

    for date in FOMC_DATES:
        pdf_io = download_pdf(date)
        if pdf_io:
            records = structure_transcript(pdf_io, date)
            all_records.extend(records)
            print(f"✅ {date} 處理完成，新增 {len(records)} 條記錄。")

    # 建立 Pandas DataFrame
    df = pd.DataFrame(all_records)

    # 調整日期格式
    df['Date'] = pd.to_datetime(df['Date'], format='%Y%m%d').dt.strftime('%Y-%m-%d')

    # 清理最終文本
    for col in ['Question', 'Text']:
        # 移除多餘的空白/換行，並清理首尾空白
        df[col] = df[col].astype(str).str.replace(r'\s+', ' ', regex=True).str.strip()

    # 儲存為 CSV 檔案 (會儲存到您的專案根目錄)
    OUTPUT_FILENAME = r'data\raw\fed_transcripts_structured_pycharm.csv'
    df.to_csv(OUTPUT_FILENAME, index=False, encoding='utf-8')

    print("\n==========================================")
    print(f"✨ 數據處理完畢！成功處理 {len(df)} 條發言記錄。")
    print(f"檔案已儲存至您的專案目錄： {OUTPUT_FILENAME}")
    print("==========================================")
