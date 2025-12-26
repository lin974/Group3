import os
import re
import pandas as pd
import requests
from io import BytesIO
from pdfminer.high_level import extract_text

# 1. 聯準會 FOMC 記者會日期列表 (完整保留)
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

# 2. 利率變動對照表 (None 表示不加入標籤)
RATE_CHANGE_MAP = {
    '20251029': None, '20250917': None, # 這兩個日期保留報告，但不加入變動數據
    '20250730': -3, '20250618': -3, '20250507': -3, '20250319': -3, '20250129': -3,
    '20241211': -3, '20240918': -4, '20240612': -2, '20240320': -2,
    '20231213': 0, '20231101': 0, '20230920': 0, '20230726': 0, '20230614': 1, '20230503': 1, '20230322': 3, '20230201': 4,
    '20221214': 3, '20221102': 7, '20220921': 11, '20220727': 13, '20220615': 15, '20220504': 12, '20220316': 11, '20220126': 6,
    '20211215': 3, '20210922': 0, '20210616': 0, '20210317': 0,
    '20201216': 0, '20201105': 0, '20200916': 0, '20200729': 0, '20200610': 0, '20200429': 0, '20200315': 0, '20200129': -6,
    '20191211': -6, '20191030': -6, '20190918': -6, '20190731': -3, '20190619': -3, '20190501': -3, '20190320': -1, '20190130': -1,
    '20181219': -1, '20180926': 2, '20180613': 2, '20180321': 2,
    '20171213': 2, '20170920': 2, '20170614': 2, '20170315': 2,
    '20161214': 1, '20160921': 1, '20160615': 1, '20160316': 1,
    '20151216': 0, '20150917': 1, '20150617': 1, '20150318': 1,
    '20141217': 0, '20140917': 0, '20140618': 0, '20140319': 0,
    '20131218': 0, '20130918': 0, '20130619': 0, '20130320': 0,
    '20121212': 0, '20120913': 0, '20120620': 0, '20120425': 0, '20120125': 0,
    '20111213': 0, '20110921': 0, '20110622': 0, '20110427': 0
}

BASE_URL = "https://www.federalreserve.gov/mediacenter/files/FOMCpresconf"

def download_pdf(date):
    url = f"{BASE_URL}{date}.pdf"
    try:
        response = requests.get(url, timeout=15)
        if response.status_code == 200 and 'application/pdf' in response.headers.get('Content-Type', ''):
            return BytesIO(response.content)
        return None
    except Exception as e:
        print(f"❌ {date} 下載錯誤: {e}")
        return None

def structure_transcript(pdf_content_io, date):
    data = []
    try:
        full_text = extract_text(pdf_content_io).replace('\n', ' ').replace('\r', ' ').strip()
        
        # 取得該日期的利率變動標籤
        change_val = RATE_CHANGE_MAP.get(date)
        prefix = f"[{change_val}] " if change_val is not None else ""

        qa_match = re.search(r'(QUESTION\s+AND\s+ANSWER\s+PERIOD|Questions\s+and\s+Answers)', full_text, re.IGNORECASE)
        statement_text = full_text[:qa_match.start()].strip() if qa_match else full_text

        if statement_text:
            data.append({
                'Date': date,
                'Rate_Change_6M': change_val,
                'Speaker': 'CHAIR',
                'Section': 'Statement',
                'Text': prefix + statement_text
            })

        if qa_match:
            qa_text = full_text[qa_match.end():].strip()
            transactions = re.split(r'((?:CHAIR\s+(?:POWELL|YELLEN|BERNANKE)|QUESTION\s+FROM.*|MR\.\s+.*):\s*)', qa_text, flags=re.IGNORECASE)

            current_speaker = None
            current_question = ""

            for i, part in enumerate(transactions):
                part = part.strip()
                if not part: continue

                if re.match(r'(CHAIR\s+(POWELL|YELLEN|BERNANKE)|QUESTION\s+FROM.*|MR\.\s+.*):', part, re.IGNORECASE):
                    current_speaker = part.replace(':', '').strip()
                elif current_speaker:
                    if current_speaker.startswith('QUESTION FROM') or re.match(r'MR\.\s+.*', current_speaker, re.IGNORECASE):
                        current_question = part
                        data.append({
                            'Date': date, 'Rate_Change_6M': change_val, 'Speaker': 'REPORTER', 
                            'Section': 'Q&A', 'Question': current_question, 'Text': prefix + part
                        })
                    elif current_speaker.startswith('CHAIR'):
                        data.append({
                            'Date': date, 'Rate_Change_6M': change_val, 'Speaker': 'CHAIR', 
                            'Section': 'Q&A', 'Question': current_question, 'Text': prefix + part
                        })
                    current_speaker = None
    except Exception as e:
        print(f"❌ {date} 解析錯誤: {e}")
    return data

if __name__ == '__main__':
    all_records = []
    for date in FOMC_DATES:
        pdf_io = download_pdf(date)
        if pdf_io:
            records = structure_transcript(pdf_io, date)
            all_records.extend(records)
            print(f"✅ {date} 處理完成")

    df = pd.DataFrame(all_records)
    df['Date'] = pd.to_datetime(df['Date'], format='%Y%m%d').dt.strftime('%Y-%m-%d')
    df.to_csv(r'data\raw\fed_transcripts_with_labels.csv', index=False, encoding='utf-8')
    print("✨ 任務完成，檔案已儲存。")