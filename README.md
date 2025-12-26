# 地端 LLM 驅動的金融時序分析系統：美聯儲政策解讀與市場預測

本專案結合 **地端大型語言模型 (Mistral LLM)** 與 **Google TimesFM 時序基礎模型**，建立一套完整的金融分析管線。系統會自動抓取聯準會 (Fed) 記者會逐字稿，透過 RAG 技術進行情感建模，最後整合宏觀數據進行美債收益率的精準預測。

---

## 🛠️ 環境建置與依賴項安裝 (Setup & Dependencies)

本專案需要處理 PDF 文本解析、地端 LLM 推論及時序預測，請安裝以下依賴：

### 1. 核心模型庫安裝

* **TimesFM (預測引擎)：** `pip install git+https://github.com/google-research/timesfm.git`
* **LLaMA-CPP (LLM 執行環境)：** `pip install llama-cpp-python` (建議配置 CUDA 加速)

### 2. 專案依賴項安裝

```bash
# 運行以下指令，安裝所有必要的套件
pip install -r requirements.txt

```

---

## ⬇️ 模型檔案下載 (Model Preparation)

1. **LLM 模型：** 下載 [Mistral-Nemo-Instruct-2407-Q4_K_M-GGUF](https://huggingface.co/Nehal07/Mistral-Nemo-Instruct-2407-Q4_K_M-GGUF)。
2. **放置路徑：** 將 `mistral-nemo-instruct-2407.Q4_K_M.gguf` 放置於專案目錄中，並確保在 Notebook 中正確引用路徑。

---

## 🚀 執行流程 (Execution Flow)

請依照下列編號順序執行檔案：

### **Step 01: 數據抓取與結構化 (`01_catch_data.py`)**

* **功能：** 自動從聯準會官網下載指定日期 (2021-2025) 的 FOMC 記者會 PDF 逐字稿。
* **技術：** 使用 `pdfminer` 進行文本提取，並將非結構化文本解析為「發言人、問題、回答內容」的結構化 CSV 格式。

### **Step 02: RAG 語意分析與指標生成 (`02_fomc_analysis.ipynb`)**

* **功能：** 載入 Mistral LLM 並建立 **RAG (檢索增強生成) 索引**。
* **核心邏輯：** * 針對每一場記者會，從索引中檢索關鍵片段。
* 由 LLM 判定聯準會立場（Hawkish/Dovish）並量化為 `Score`。



### **Step 03: 多因子時序預測 (`03_timesfm_prediction.ipynb`)**

* **功能：** 載入 Google TimesFM 模型進行未來預測。
* **預測策略：** 採用 **最佳策略**，綜合考慮 2 年期美債利率、LLM 情感得分以及宏觀經濟數據。


---

## ⚠️ 注意事項

* **硬體提醒：** 執行 `02_fomc_analysis` 時，建議 GPU 顯存至少 8GB 以啟用 `n_gpu_layers` 加速。
* **數據更新：** 若要預測最新日期，請在 `01_catch_data.py` 中的 `FOMC_DATES` 列表新增日期。
