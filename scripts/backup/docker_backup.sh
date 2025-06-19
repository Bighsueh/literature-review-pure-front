#!/bin/bash

# Docker 資料庫備份腳本
# 版本: 1.0
# 目標: 在 Docker 環境中備份 PostgreSQL 資料庫

set -e  # 遇到錯誤時立即退出

# 配置參數
CONTAINER_NAME="paper_analysis_db"
DB_NAME="paper_analysis"
DB_USER="postgres"
BACKUP_DIR="/app/backups"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_FILE="paper_analysis_backup_${TIMESTAMP}.sql"
SCHEMA_FILE="paper_analysis_schema_${TIMESTAMP}.sql"

# 顏色輸出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}🚀 開始 Docker 資料庫備份程序...${NC}"
echo "時間戳: $TIMESTAMP"
echo "容器名稱: $CONTAINER_NAME"
echo "資料庫名稱: $DB_NAME"

# 檢查 Docker 容器是否運行
echo -e "${YELLOW}📋 檢查 Docker 容器狀態...${NC}"
if ! docker ps | grep -q "$CONTAINER_NAME"; then
    echo -e "${RED}❌ 錯誤: 容器 $CONTAINER_NAME 未運行${NC}"
    echo "請先啟動容器: docker-compose up -d postgres"
    exit 1
fi

echo -e "${GREEN}✅ 容器 $CONTAINER_NAME 正在運行${NC}"

# 創建備份目錄
echo -e "${YELLOW}📁 準備備份目錄...${NC}"
docker exec $CONTAINER_NAME mkdir -p $BACKUP_DIR

# 1. 備份完整資料庫
echo -e "${YELLOW}💾 執行完整資料庫備份...${NC}"
docker exec $CONTAINER_NAME pg_dump -U $DB_USER -d $DB_NAME -v \
    --no-owner --no-privileges --clean --if-exists \
    > "./backups/${BACKUP_FILE}" 2>/dev/null

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ 完整備份成功: ${BACKUP_FILE}${NC}"
else
    echo -e "${RED}❌ 完整備份失敗${NC}"
    exit 1
fi

# 2. 備份僅結構 (schema only)
echo -e "${YELLOW}🏗️  執行結構備份...${NC}"
docker exec $CONTAINER_NAME pg_dump -U $DB_USER -d $DB_NAME -s -v \
    --no-owner --no-privileges --clean --if-exists \
    > "./backups/${SCHEMA_FILE}" 2>/dev/null

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ 結構備份成功: ${SCHEMA_FILE}${NC}"
else
    echo -e "${RED}❌ 結構備份失敗${NC}"
    exit 1
fi

# 3. 備份關鍵統計資訊
echo -e "${YELLOW}📊 收集資料庫統計資訊...${NC}"
STATS_FILE="backup_stats_${TIMESTAMP}.txt"

cat > "./backups/${STATS_FILE}" << EOF
資料庫備份統計資訊
==================
備份時間: $(date)
資料庫名稱: $DB_NAME
備份檔案: $BACKUP_FILE
結構檔案: $SCHEMA_FILE

資料表統計:
EOF

# 收集各表的行數統計
docker exec $CONTAINER_NAME psql -U $DB_USER -d $DB_NAME -c "
SELECT 
    schemaname,
    tablename,
    n_tup_ins as inserts,
    n_tup_upd as updates,
    n_tup_del as deletes,
    n_live_tup as live_rows,
    n_dead_tup as dead_rows
FROM pg_stat_user_tables 
ORDER BY schemaname, tablename;
" >> "./backups/${STATS_FILE}" 2>/dev/null

# 4. 檢查備份檔案大小
echo -e "${YELLOW}📏 檢查備份檔案...${NC}"
BACKUP_SIZE=$(du -h "./backups/${BACKUP_FILE}" | cut -f1)
SCHEMA_SIZE=$(du -h "./backups/${SCHEMA_FILE}" | cut -f1)

echo "完整備份大小: $BACKUP_SIZE"
echo "結構備份大小: $SCHEMA_SIZE"

# 5. 測試備份完整性
echo -e "${YELLOW}🔍 測試備份完整性...${NC}"
if head -10 "./backups/${BACKUP_FILE}" | grep -q "PostgreSQL database dump"; then
    echo -e "${GREEN}✅ 備份檔案格式正確${NC}"
else
    echo -e "${RED}❌ 備份檔案可能損壞${NC}"
    exit 1
fi

# 6. 清理舊備份 (保留最近 7 天)
echo -e "${YELLOW}🧹 清理舊備份檔案...${NC}"
find ./backups -name "paper_analysis_backup_*.sql" -mtime +7 -delete 2>/dev/null || true
find ./backups -name "paper_analysis_schema_*.sql" -mtime +7 -delete 2>/dev/null || true
find ./backups -name "backup_stats_*.txt" -mtime +7 -delete 2>/dev/null || true

echo -e "${GREEN}🎉 備份程序完成!${NC}"
echo ""
echo "備份檔案:"
echo "  📄 完整備份: ./backups/${BACKUP_FILE}"
echo "  🏗️  結構備份: ./backups/${SCHEMA_FILE}"
echo "  📊 統計資訊: ./backups/${STATS_FILE}"
echo ""
echo "恢復指令:"
echo "  docker exec -i $CONTAINER_NAME psql -U $DB_USER -d $DB_NAME < ./backups/${BACKUP_FILE}" 