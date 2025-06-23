#!/bin/bash

# Docker 資料庫恢復腳本
# 版本: 1.0
# 目標: 在 Docker 環境中恢復 PostgreSQL 資料庫

set -e  # 遇到錯誤時立即退出

# 配置參數
CONTAINER_NAME="paper_analysis_db"
DB_NAME="paper_analysis"
DB_USER="postgres"
BACKUP_DIR="./backups"

# 顏色輸出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 顯示使用說明
show_usage() {
    echo -e "${BLUE}使用說明:${NC}"
    echo "  $0 <backup_file>                    # 恢復指定的備份檔案"
    echo "  $0 --list                           # 列出可用的備份檔案"
    echo "  $0 --latest                         # 恢復最新的備份檔案"
    echo "  $0 --emergency                      # 緊急恢復模式 (重置資料庫)"
    echo ""
    echo -e "${YELLOW}範例:${NC}"
    echo "  $0 paper_analysis_backup_20241212_143000.sql"
    echo "  $0 --latest"
}

# 列出可用的備份檔案
list_backups() {
    echo -e "${GREEN}📋 可用的備份檔案:${NC}"
    if [ -d "$BACKUP_DIR" ]; then
        ls -la "$BACKUP_DIR"/paper_analysis_backup_*.sql 2>/dev/null | \
        awk '{print "  " $9 " (" $5 " bytes, " $6 " " $7 " " $8 ")"}' || \
        echo -e "${YELLOW}  沒有找到備份檔案${NC}"
    else
        echo -e "${RED}  備份目錄不存在: $BACKUP_DIR${NC}"
    fi
}

# 取得最新的備份檔案
get_latest_backup() {
    latest=$(ls -t "$BACKUP_DIR"/paper_analysis_backup_*.sql 2>/dev/null | head -n1)
    if [ -n "$latest" ]; then
        echo "$latest"
    else
        echo ""
    fi
}

# 檢查參數
if [ $# -eq 0 ]; then
    echo -e "${RED}❌ 錯誤: 請提供備份檔案名稱或選項${NC}"
    show_usage
    exit 1
fi

# 處理選項
case "$1" in
    --help|-h)
        show_usage
        exit 0
        ;;
    --list|-l)
        list_backups
        exit 0
        ;;
    --latest)
        BACKUP_FILE=$(get_latest_backup)
        if [ -z "$BACKUP_FILE" ]; then
            echo -e "${RED}❌ 沒有找到備份檔案${NC}"
            exit 1
        fi
        echo -e "${GREEN}使用最新備份: $(basename "$BACKUP_FILE")${NC}"
        ;;
    --emergency)
        echo -e "${RED}⚠️  緊急恢復模式 - 這將完全重置資料庫!${NC}"
        read -p "確定要繼續嗎? (輸入 'YES' 確認): " confirm
        if [ "$confirm" != "YES" ]; then
            echo "操作已取消"
            exit 1
        fi
        BACKUP_FILE=$(get_latest_backup)
        EMERGENCY_MODE=true
        ;;
    *)
        if [ ! -f "$1" ]; then
            # 嘗試在備份目錄中查找
            if [ -f "$BACKUP_DIR/$1" ]; then
                BACKUP_FILE="$BACKUP_DIR/$1"
            else
                echo -e "${RED}❌ 備份檔案不存在: $1${NC}"
                echo ""
                list_backups
                exit 1
            fi
        else
            BACKUP_FILE="$1"
        fi
        ;;
esac

echo -e "${GREEN}🚀 開始 Docker 資料庫恢復程序...${NC}"
echo "容器名稱: $CONTAINER_NAME"
echo "資料庫名稱: $DB_NAME"
echo "備份檔案: $BACKUP_FILE"

# 檢查 Docker 容器是否運行
echo -e "${YELLOW}📋 檢查 Docker 容器狀態...${NC}"
if ! docker ps | grep -q "$CONTAINER_NAME"; then
    echo -e "${RED}❌ 錯誤: 容器 $CONTAINER_NAME 未運行${NC}"
    echo "正在嘗試啟動容器..."
    docker-compose up -d postgres
    
    # 等待容器就緒
    echo "等待資料庫啟動..."
    sleep 10
    
    if ! docker ps | grep -q "$CONTAINER_NAME"; then
        echo -e "${RED}❌ 無法啟動容器${NC}"
        exit 1
    fi
fi

echo -e "${GREEN}✅ 容器 $CONTAINER_NAME 正在運行${NC}"

# 檢查備份檔案
echo -e "${YELLOW}🔍 檢查備份檔案...${NC}"
if [ ! -f "$BACKUP_FILE" ]; then
    echo -e "${RED}❌ 備份檔案不存在: $BACKUP_FILE${NC}"
    exit 1
fi

file_size=$(du -h "$BACKUP_FILE" | cut -f1)
echo "備份檔案大小: $file_size"

# 測試備份檔案格式
if ! head -10 "$BACKUP_FILE" | grep -q "PostgreSQL database dump"; then
    echo -e "${RED}❌ 備份檔案格式不正確${NC}"
    exit 1
fi

echo -e "${GREEN}✅ 備份檔案檢查通過${NC}"

# 創建恢復前的安全備份
echo -e "${YELLOW}💾 創建恢復前安全備份...${NC}"
SAFETY_BACKUP="./backups/pre_restore_safety_$(date +%Y%m%d_%H%M%S).sql"
docker exec $CONTAINER_NAME pg_dump -U $DB_USER -d $DB_NAME \
    --no-owner --no-privileges --clean --if-exists \
    > "$SAFETY_BACKUP" 2>/dev/null || true

echo "安全備份已創建: $SAFETY_BACKUP"

# 緊急模式: 完全重置資料庫
if [ "$EMERGENCY_MODE" = true ]; then
    echo -e "${RED}🔥 執行緊急重置...${NC}"
    
    # 停止可能的連線
    docker exec $CONTAINER_NAME psql -U $DB_USER -d postgres -c \
        "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname='$DB_NAME' AND pid <> pg_backend_pid();" 2>/dev/null || true
    
    # 刪除並重建資料庫
    docker exec $CONTAINER_NAME psql -U $DB_USER -d postgres -c "DROP DATABASE IF EXISTS $DB_NAME;" 2>/dev/null || true
    docker exec $CONTAINER_NAME psql -U $DB_USER -d postgres -c "CREATE DATABASE $DB_NAME;" 2>/dev/null || true
fi

# 執行恢復
echo -e "${YELLOW}🔄 執行資料庫恢復...${NC}"
start_time=$(date +%s)

# 恢復資料庫
if cat "$BACKUP_FILE" | docker exec -i $CONTAINER_NAME psql -U $DB_USER -d $DB_NAME > /dev/null 2>&1; then
    end_time=$(date +%s)
    duration=$((end_time - start_time))
    echo -e "${GREEN}✅ 資料庫恢復成功 (耗時: ${duration}秒)${NC}"
else
    echo -e "${RED}❌ 資料庫恢復失敗${NC}"
    echo -e "${YELLOW}🔄 正在恢復安全備份...${NC}"
    cat "$SAFETY_BACKUP" | docker exec -i $CONTAINER_NAME psql -U $DB_USER -d $DB_NAME > /dev/null 2>&1 || true
    exit 1
fi

# 驗證恢復結果
echo -e "${YELLOW}🔍 驗證恢復結果...${NC}"
table_count=$(docker exec $CONTAINER_NAME psql -U $DB_USER -d $DB_NAME -t -c \
    "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='public';" 2>/dev/null | tr -d ' ')

echo "公共表格數量: $table_count"

if [ "$table_count" -gt 0 ]; then
    echo -e "${GREEN}✅ 資料庫結構驗證通過${NC}"
else
    echo -e "${RED}❌ 資料庫結構驗證失敗${NC}"
    exit 1
fi

# 檢查關鍵表格
echo -e "${YELLOW}📊 檢查關鍵表格...${NC}"
key_tables=("papers" "users" "workspaces" "chat_histories")

for table in "${key_tables[@]}"; do
    if docker exec $CONTAINER_NAME psql -U $DB_USER -d $DB_NAME -c "\\dt" 2>/dev/null | grep -q "$table"; then
        row_count=$(docker exec $CONTAINER_NAME psql -U $DB_USER -d $DB_NAME -t -c \
            "SELECT COUNT(*) FROM $table;" 2>/dev/null | tr -d ' ' || echo "0")
        echo "  ✅ $table: $row_count 筆記錄"
    else
        echo "  ⚠️  $table: 表格不存在"
    fi
done

echo -e "${GREEN}🎉 恢復程序完成!${NC}"
echo ""
echo "恢復統計:"
echo "  📄 恢復檔案: $(basename "$BACKUP_FILE")"
echo "  💾 安全備份: $SAFETY_BACKUP"
echo "  🕒 恢復時間: ${duration}秒"
echo "  📊 表格數量: $table_count" 