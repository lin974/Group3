### **地端 $\text{LLM}$ 驅動的金融時序分析系統：美聯儲政策報告解讀與市場預測**

此專案旨在利用地端部署的大型語言模型 ($\text{LLM}$)，對美國聯邦儲備系統 ($\text{Fed}$) 發表的金融報告進行**自動化摘要與情感解讀**，並將其洞察應用於 **$\text{TimesFM}$ 時序模型**，以增強金融市場指標的預測能力。

-----

### 🛠️ 步驟一：環境建置與依賴項安裝 (Setup & Dependencies)

  * **1. 核心模型庫安裝**

      * **$\text{TimesFM}$ (時序預測引擎)：**
        ```bash
        pip install timesfm
        # 如果需要從原始碼安裝：
        git clone https://github.com/google-research/timesfm.git
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

