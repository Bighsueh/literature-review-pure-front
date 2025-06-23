#!/bin/bash

# 資料庫遷移測試腳本
# 版本: 1.0
# 目標: 驗證 Alembic 遷移腳本在全新和現有資料庫上的執行

set -e

# 配置參數
TEST_CONTAINER_PREFIX="migration_test"
TEST_DB_NAME="migration_test_db"
TEST_DB_USER="postgres"
TEST_DB_PASSWORD="test_password"
DOCKER_COMPOSE_TEST_FILE="docker-compose.test.yml"

# 顏色輸出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# 測試結果
TESTS_PASSED=0
TESTS_FAILED=0
TEST_RESULTS=()

log_test_result() {
    local test_name="$1"
    local result="$2"
    local message="$3"
    
    if [ "$result" = "PASS" ]; then
        echo -e "${GREEN}✅ $test_name: PASSED${NC}"
        ((TESTS_PASSED++))
        TEST_RESULTS+=("✅ $test_name: PASSED - $message")
    else
        echo -e "${RED}❌ $test_name: FAILED${NC}"
        echo -e "${RED}   $message${NC}"
        ((TESTS_FAILED++))
        TEST_RESULTS+=("❌ $test_name: FAILED - $message")
    fi
}

# 清理函數
cleanup() {
    echo -e "${YELLOW}🧹 清理測試環境...${NC}"
    docker-compose -f "$DOCKER_COMPOSE_TEST_FILE" down -v 2>/dev/null || true
    docker rmi "${TEST_CONTAINER_PREFIX}_backend" 2>/dev/null || true
    rm -f "$DOCKER_COMPOSE_TEST_FILE"
}

# 設定信號處理
trap cleanup EXIT

echo -e "${BLUE}🚀 開始資料庫遷移測試程序${NC}"
echo "測試時間: $(date)"
echo ""

# 1. 創建測試用的 docker-compose 配置
echo -e "${YELLOW}📋 準備測試環境配置...${NC}"
cat > "$DOCKER_COMPOSE_TEST_FILE" << EOF
version: '3.8'
services:
  postgres_test:
    image: postgres:15
    container_name: ${TEST_CONTAINER_PREFIX}_postgres
    environment:
      POSTGRES_DB: $TEST_DB_NAME
      POSTGRES_USER: $TEST_DB_USER
      POSTGRES_PASSWORD: $TEST_DB_PASSWORD
      POSTGRES_HOST_AUTH_METHOD: trust
    ports:
      - "25433:5432"
    volumes:
      - postgres_test_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U $TEST_DB_USER"]
      interval: 5s
      timeout: 5s
      retries: 5

  backend_test:
    build:
      context: .
      dockerfile: backend/Dockerfile
    container_name: ${TEST_CONTAINER_PREFIX}_backend
    environment:
      - POSTGRES_HOST=postgres_test
      - POSTGRES_PORT=5432
      - POSTGRES_DB=$TEST_DB_NAME
      - POSTGRES_USER=$TEST_DB_USER
      - POSTGRES_PASSWORD=$TEST_DB_PASSWORD
      - ENVIRONMENT=testing
    volumes:
      - ./backend:/app/backend
    depends_on:
      postgres_test:
        condition: service_healthy
    command: ["tail", "-f", "/dev/null"]

volumes:
  postgres_test_data:
EOF

# 2. 啟動測試環境
echo -e "${YELLOW}🔧 啟動測試環境...${NC}"
if docker-compose -f "$DOCKER_COMPOSE_TEST_FILE" up -d; then
    log_test_result "Environment Setup" "PASS" "測試環境啟動成功"
else
    log_test_result "Environment Setup" "FAIL" "測試環境啟動失敗"
    exit 1
fi

# 等待服務就緒
echo -e "${YELLOW}⏳ 等待服務就緒...${NC}"
sleep 15

# 3. 測試 1: 全新資料庫遷移
echo -e "${BLUE}📋 測試 1: 全新資料庫遷移${NC}"

# 檢查資料庫是否為空
table_count=$(docker exec "${TEST_CONTAINER_PREFIX}_postgres" psql -U $TEST_DB_USER -d $TEST_DB_NAME -t -c \
    "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='public';" 2>/dev/null | tr -d ' ')

if [ "$table_count" = "0" ]; then
    log_test_result "Fresh Database Check" "PASS" "確認資料庫為空 (0 tables)"
else
    log_test_result "Fresh Database Check" "FAIL" "資料庫不為空 ($table_count tables)"
fi

# 執行遷移
echo -e "${YELLOW}🔄 執行 alembic upgrade head...${NC}"
migration_start_time=$(date +%s)

if docker exec "${TEST_CONTAINER_PREFIX}_backend" \
    bash -c "cd /app/backend && alembic upgrade head" 2>&1; then
    migration_end_time=$(date +%s)
    migration_duration=$((migration_end_time - migration_start_time))
    log_test_result "Fresh Migration" "PASS" "遷移成功 (耗時: ${migration_duration}秒)"
else
    log_test_result "Fresh Migration" "FAIL" "遷移失敗"
fi

# 檢查遷移後的表格
echo -e "${YELLOW}🔍 檢查遷移後的資料庫結構...${NC}"
final_table_count=$(docker exec "${TEST_CONTAINER_PREFIX}_postgres" psql -U $TEST_DB_USER -d $TEST_DB_NAME -t -c \
    "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='public';" 2>/dev/null | tr -d ' ')

expected_tables=("papers" "paper_sections" "sentences" "paper_selections" "processing_queue" "system_settings" "users" "workspaces" "chat_histories")
missing_tables=()

for table in "${expected_tables[@]}"; do
    if ! docker exec "${TEST_CONTAINER_PREFIX}_postgres" psql -U $TEST_DB_USER -d $TEST_DB_NAME -c "\\dt" 2>/dev/null | grep -q "$table"; then
        missing_tables+=("$table")
    fi
done

if [ ${#missing_tables[@]} -eq 0 ]; then
    log_test_result "Schema Validation" "PASS" "所有必要表格已創建 ($final_table_count tables)"
else
    log_test_result "Schema Validation" "FAIL" "缺少表格: ${missing_tables[*]}"
fi

# 4. 測試 2: 檢查外鍵約束
echo -e "${BLUE}📋 測試 2: 外鍵約束檢查${NC}"

# 檢查重要的外鍵約束
foreign_keys_check=$(docker exec "${TEST_CONTAINER_PREFIX}_postgres" psql -U $TEST_DB_USER -d $TEST_DB_NAME -t -c \
    "SELECT COUNT(*) FROM information_schema.table_constraints WHERE constraint_type='FOREIGN KEY';" 2>/dev/null | tr -d ' ')

if [ "$foreign_keys_check" -gt 0 ]; then
    log_test_result "Foreign Keys" "PASS" "外鍵約束已正確設置 ($foreign_keys_check constraints)"
else
    log_test_result "Foreign Keys" "FAIL" "沒有找到外鍵約束"
fi

# 5. 測試 3: 索引檢查
echo -e "${BLUE}📋 測試 3: 索引檢查${NC}"

index_count=$(docker exec "${TEST_CONTAINER_PREFIX}_postgres" psql -U $TEST_DB_USER -d $TEST_DB_NAME -t -c \
    "SELECT COUNT(*) FROM pg_indexes WHERE schemaname='public';" 2>/dev/null | tr -d ' ')

if [ "$index_count" -gt 10 ]; then  # 期望有多個索引
    log_test_result "Indexes" "PASS" "索引已正確創建 ($index_count indexes)"
else
    log_test_result "Indexes" "FAIL" "索引數量不足 ($index_count indexes)"
fi

# 6. 測試 4: 插入測試資料
echo -e "${BLUE}📋 測試 4: 基本資料操作測試${NC}"

# 插入測試用戶
test_user_id=$(docker exec "${TEST_CONTAINER_PREFIX}_postgres" psql -U $TEST_DB_USER -d $TEST_DB_NAME -t -c \
    "INSERT INTO users (google_id, email, name) VALUES ('test123', 'test@example.com', 'Test User') RETURNING id;" 2>/dev/null | tr -d ' ')

if [ -n "$test_user_id" ]; then
    log_test_result "User Insert" "PASS" "測試用戶創建成功 (ID: $test_user_id)"
    
    # 插入測試工作區
    test_workspace_id=$(docker exec "${TEST_CONTAINER_PREFIX}_postgres" psql -U $TEST_DB_USER -d $TEST_DB_NAME -t -c \
        "INSERT INTO workspaces (user_id, name) VALUES ('$test_user_id', 'Test Workspace') RETURNING id;" 2>/dev/null | tr -d ' ')
    
    if [ -n "$test_workspace_id" ]; then
        log_test_result "Workspace Insert" "PASS" "測試工作區創建成功 (ID: $test_workspace_id)"
        
        # 插入測試對話
        test_chat_id=$(docker exec "${TEST_CONTAINER_PREFIX}_postgres" psql -U $TEST_DB_USER -d $TEST_DB_NAME -t -c \
            "INSERT INTO chat_histories (workspace_id, role, content) VALUES ('$test_workspace_id', 'user', 'Test message') RETURNING id;" 2>/dev/null | tr -d ' ')
        
        if [ -n "$test_chat_id" ]; then
            log_test_result "Chat Insert" "PASS" "測試對話創建成功 (ID: $test_chat_id)"
        else
            log_test_result "Chat Insert" "FAIL" "對話創建失敗"
        fi
    else
        log_test_result "Workspace Insert" "FAIL" "工作區創建失敗"
    fi
else
    log_test_result "User Insert" "FAIL" "用戶創建失敗"
fi

# 7. 測試 5: 回滾測試
echo -e "${BLUE}📋 測試 5: 回滾功能測試${NC}"

# 記錄當前版本
current_revision=$(docker exec "${TEST_CONTAINER_PREFIX}_backend" \
    bash -c "cd /app/backend && alembic current" 2>/dev/null | grep -E '^[a-f0-9]+' | head -1)

if [ -n "$current_revision" ]; then
    log_test_result "Current Revision" "PASS" "當前版本: $current_revision"
    
    # 嘗試回滾一個版本
    if docker exec "${TEST_CONTAINER_PREFIX}_backend" \
        bash -c "cd /app/backend && alembic downgrade -1" 2>&1; then
        log_test_result "Downgrade Test" "PASS" "回滾功能正常"
        
        # 重新升級
        if docker exec "${TEST_CONTAINER_PREFIX}_backend" \
            bash -c "cd /app/backend && alembic upgrade head" 2>&1; then
            log_test_result "Re-upgrade Test" "PASS" "重新升級成功"
        else
            log_test_result "Re-upgrade Test" "FAIL" "重新升級失敗"
        fi
    else
        log_test_result "Downgrade Test" "FAIL" "回滾功能失敗"
    fi
else
    log_test_result "Current Revision" "FAIL" "無法獲取當前版本"
fi

# 8. 效能測試
echo -e "${BLUE}📋 測試 6: 基本效能測試${NC}"

# 插入大量測試資料
perf_start_time=$(date +%s)
docker exec "${TEST_CONTAINER_PREFIX}_postgres" psql -U $TEST_DB_USER -d $TEST_DB_NAME -c \
    "INSERT INTO papers (file_name, original_filename, file_hash) 
     SELECT 'test_' || generate_series || '.pdf', 'original_' || generate_series || '.pdf', md5(random()::text)
     FROM generate_series(1, 100);" 2>/dev/null

perf_end_time=$(date +%s)
perf_duration=$((perf_end_time - perf_start_time))

if [ "$perf_duration" -lt 10 ]; then  # 期望在10秒內完成
    log_test_result "Performance Test" "PASS" "100筆資料插入耗時: ${perf_duration}秒"
else
    log_test_result "Performance Test" "FAIL" "效能測試超時: ${perf_duration}秒"
fi

# 9. 最終報告
echo ""
echo -e "${BLUE}📊 測試結果總結${NC}"
echo "=================="
echo -e "${GREEN}✅ 通過: $TESTS_PASSED${NC}"
echo -e "${RED}❌ 失敗: $TESTS_FAILED${NC}"
echo ""

echo "詳細結果:"
for result in "${TEST_RESULTS[@]}"; do
    echo "  $result"
done

echo ""
if [ $TESTS_FAILED -eq 0 ]; then
    echo -e "${GREEN}🎉 所有測試通過! 遷移腳本驗證成功${NC}"
    exit 0
else
    echo -e "${RED}⚠️  有 $TESTS_FAILED 個測試失敗，請檢查遷移腳本${NC}"
    exit 1
fi 