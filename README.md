### **地端 $\text{LLM}$ 驅動的金融時序分析系統：美聯儲政策報告解讀與市場預測**

此專案旨在利用地端部署的大型語言模型 ($\text{LLM}$)，對美國聯邦儲備系統 ($\text{Fed}$) 發表的金融報告進行**自動化摘要與情感解讀**，並將其洞察應用於 **$\text{TimesFM}$ 時序模型**，以增強金融市場指標的預測能力。

-----

### 🛠️ 步驟一：環境建置與依賴項安裝 (Setup & Dependencies)

  * **1. 核心模型庫安裝**

      * **$\text{TimesFM}$ (時序預測引擎)：**
        ```bash
        pip install git+https://github.com/google-research/timesfm.git
        ```
      * **$\text{LLaMA-CPP}$ (地端 $\text{LLM}$ 執行環境)：**
        ```bash
        pip install llama-cpp-python
        # 如果需要從原始碼安裝：
        git clone https://github.com/ggerganov/llama.cpp
        ```
      * *註：建議在地端環境中，優先使用預編譯的 `pip install` 指令。*

  * **2. 專案依賴項安裝**

      * 運行以下指令，安裝所有必要的 $\text{Python}$ 庫：
        ```bash
        pip install -r requirements.txt
        ```
   根據您的硬體 (例如有無 NVIDIA GPU)，您可能需要加上特定參數來啟用加速。
   
⬇️ 模型檔案下載
您需要從 Hugging Face 下載 GGUF 格式的模型檔案。

1. 模型資訊
模型名稱： Mistral-Nemo-Instruct-2407-Q4_K_M-GGUF

Hugging Face 連結： https://huggingface.co/Nehal07/Mistral-Nemo-Instruct-2407-Q4_K_M-GGUF

2. 下載步驟
開啟上方的 Hugging Face 連結。

點擊頁面中央的 "Files and versions" (檔案與版本) 標籤。

在檔案列表中找到主要的 GGUF 檔案，其檔名應為：

mistral-nemo-instruct-2407.Q4_K_M.gguf

點擊檔案名稱右側的 下載圖標 (向下箭頭)。

接著就可以依序從檔案01開始執行
