FROM python:3.11-slim

# 設置工作目錄
WORKDIR /app

# 安裝系統依賴（包含編譯工具、SSL支援和debug工具）
RUN apt-get update && apt-get install -y \
    curl \
    gcc \
    g++ \
    build-essential \
    libmagic1 \
    libssl-dev \
    libffi-dev \
    postgresql-client \
    net-tools \
    htop \
    vim \
    less \
    strace \
    && rm -rf /var/lib/apt/lists/*

# 複製requirements檔案
COPY backend/requirements.txt .

# 安裝Python依賴（啟用SSL支援）
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# 複製應用程式碼
COPY backend/ /app/backend/

# 建立暫存檔案目錄
RUN mkdir -p /app/temp_files

# 設置環境變數
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1
ENV ASYNCPG_SSL_ENABLED=1

# 暴露端口
EXPOSE 8000

# 啟動命令（啟用debug logging）
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000", "--log-level", "info", "--access-log"] 