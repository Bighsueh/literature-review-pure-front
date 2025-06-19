#!/bin/bash

# 資料完整性驗證執行腳本
# Data Integrity Validation Runner

echo "🚀 啟動資料完整性驗證..."

# 設定環境變量
export DB_HOST=paper_analysis_db
export DB_PORT=5432
export DB_NAME=paper_analysis
export DB_USER=postgres
export DB_PASSWORD=password

# 檢查是否在 Docker 環境中
if command -v docker &> /dev/null; then
    echo "🐳 檢測到 Docker 環境，使用容器執行驗證..."
    
    # 檢查 PostgreSQL 容器是否運行
    if docker ps | grep -q "paper_analysis_db"; then
        echo "✅ PostgreSQL 容器正在運行"
        
        # 安裝 psycopg2 到後端容器中（如果需要）
        docker exec paper_analysis_backend pip install psycopg2-binary > /dev/null 2>&1
        
        # 複製驗證腳本到容器中
        docker cp $(dirname "$0")/data_integrity_validator.py paper_analysis_backend:/app/
        
        # 在容器中執行驗證，設定正確的環境變量
        docker exec -e DB_HOST=paper_analysis_db -e DB_PORT=5432 -e DB_NAME=paper_analysis -e DB_USER=postgres -e DB_PASSWORD=password paper_analysis_backend python /app/data_integrity_validator.py
        
        # 複製報告回來
        docker cp paper_analysis_backend:/app/validation_report_*.json ./ 2>/dev/null || true
        
    else
        echo "❌ PostgreSQL 容器未運行，請先啟動 docker-compose"
        exit 1
    fi
else
    echo "💻 本地環境，直接執行驗證..."
    
    # 檢查 Python 依賴
    if ! python3 -c "import psycopg2" 2>/dev/null; then
        echo "⚠️  需要安裝 psycopg2：pip install psycopg2-binary"
        exit 1
    fi
    
    # 執行驗證
    python3 $(dirname "$0")/data_integrity_validator.py
fi

echo "✅ 驗證完成！" 