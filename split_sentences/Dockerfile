FROM python:3.9-slim

# 設置工作目錄
WORKDIR /app

# 安裝系統依賴
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 複製需要的檔案
COPY requirements.txt .

# 安裝 Python 依賴
RUN pip install --no-cache-dir -r requirements.txt && \
    python -m spacy download zh_core_web_sm

# 複製應用程式碼
COPY . .

# 創建上傳目錄
RUN mkdir -p upload_data && chmod 777 upload_data

# 暴露端口
EXPOSE 8000

# 啟動應用
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"] 