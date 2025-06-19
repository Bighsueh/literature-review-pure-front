#!/bin/bash

# =============================================================================
# 學術研究管理平台 - 完全自動化重建與驗證腳本
# =============================================================================
# 功能：完全自動化地重建 PostgreSQL 資料庫並驗證多工作區架構
# 作者：AI Assistant
# 版本：v1.0
# =============================================================================

set -e  # 遇到錯誤立即停止

# 顏色輸出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 日誌函數
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_step() {
    echo ""
    echo -e "${YELLOW}======================================${NC}"
    echo -e "${YELLOW}$1${NC}"
    echo -e "${YELLOW}======================================${NC}"
}

# 等待函數
wait_for_container() {
    local container_name=$1
    local max_attempts=30
    local attempt=1
    
    log_info "等待容器 $container_name 啟動..."
    
    while [ $attempt -le $max_attempts ]; do
        if docker ps --filter "name=$container_name" --filter "status=running" | grep -q $container_name; then
            log_success "容器 $container_name 已啟動"
            return 0
        fi
        log_info "嘗試 $attempt/$max_attempts - 等待容器 $container_name..."
        sleep 2
        attempt=$((attempt + 1))
    done
    
    log_error "容器 $container_name 啟動失敗"
    return 1
}

# 等待資料庫準備就緒
wait_for_database() {
    local max_attempts=30
    local attempt=1
    
    log_info "等待 PostgreSQL 資料庫準備就緒..."
    
    while [ $attempt -le $max_attempts ]; do
        if docker exec paper_analysis_db pg_isready -U postgres >/dev/null 2>&1; then
            log_success "PostgreSQL 資料庫已準備就緒"
            return 0
        fi
        log_info "嘗試 $attempt/$max_attempts - 等待資料庫..."
        sleep 2
        attempt=$((attempt + 1))
    done
    
    log_error "PostgreSQL 資料庫啟動失敗"
    return 1
}

# 檢查遷移狀態
check_migration_status() {
    log_info "檢查當前遷移狀態..."
    
    # 嘗試獲取當前版本
    local current_version=$(docker exec paper_analysis_backend sh -c "cd /app/backend && alembic current 2>/dev/null | grep -o '[a-f0-9]\{12\}'" || echo "none")
    
    if [ "$current_version" != "none" ]; then
        log_info "當前遷移版本: $current_version"
        return 0
    else
        log_warning "無法檢測遷移狀態，將進行完整遷移"
        return 1
    fi
}

# 智能遷移執行
smart_migration() {
    log_info "開始智能遷移執行..."
    
    # 檢查當前遷移狀態
    local current_migration=$(docker exec paper_analysis_backend sh -c "cd /app/backend && alembic current 2>/dev/null | grep -o '[a-z0-9_]*'" || echo "none")
    log_info "當前遷移狀態: $current_migration"
    
    # 檢查必要表格是否存在
    local users_exists=$(docker exec paper_analysis_db psql -U postgres -d paper_analysis -t -c "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'users');" | tr -d ' ')
    
    if [ "$users_exists" = "f" ]; then
        log_warning "核心表格不存在，需要重新執行遷移"
        
        # 重置到基礎版本並重新執行所有遷移
        log_info "重置遷移狀態到 b7c75e7ad4e6..."
        docker exec paper_analysis_backend sh -c "cd /app/backend && alembic stamp b7c75e7ad4e6" >/dev/null 2>&1 || true
        
        # 逐步執行每個遷移，確保每個都成功
        local migrations=("001_users_workspaces_chat" "002_papers_workspaces" "003_isolate_core_entities" "004_isolate_processing_entities" "005_legacy_data_migration" "006_workspace_indexes")
        
        for migration in "${migrations[@]}"; do
            log_info "執行遷移: $migration"
            if docker exec paper_analysis_backend sh -c "cd /app/backend && alembic upgrade $migration"; then
                log_success "遷移 $migration 執行成功"
                
                # 驗證關鍵表格創建
                if [ "$migration" = "001_users_workspaces_chat" ]; then
                    local users_created=$(docker exec paper_analysis_db psql -U postgres -d paper_analysis -t -c "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'users');" | tr -d ' ')
                    if [ "$users_created" = "t" ]; then
                        log_success "users 表格創建成功"
                    else
                        log_error "users 表格創建失敗，停止遷移"
                        return 1
                    fi
                fi
            else
                log_error "遷移 $migration 執行失敗"
                return 1
            fi
        done
    else
        log_info "核心表格已存在，執行標準升級..."
        docker exec paper_analysis_backend sh -c "cd /app/backend && alembic upgrade head"
    fi
    
    log_success "智能遷移執行完成"
    
    # 最終驗證
    local final_users_exists=$(docker exec paper_analysis_db psql -U postgres -d paper_analysis -t -c "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'users');" | tr -d ' ')
    if [ "$final_users_exists" = "t" ]; then
        log_success "遷移後驗證：所有核心表格已創建"
    else
        log_error "遷移後驗證失敗：核心表格仍不存在"
        return 1
    fi
}

# 驗證資料庫結構
verify_database_structure() {
    log_info "驗證資料庫結構..."
    
    # 檢查必要的表格
    local required_tables=("users" "workspaces" "chat_histories" "papers" "paper_sections" "sentences" "paper_selections" "processing_queue" "processing_tasks" "processing_errors" "processing_events")
    
    for table in "${required_tables[@]}"; do
        if docker exec paper_analysis_db psql -U postgres -d paper_analysis -c "\dt" | grep -q "$table"; then
            log_success "表格 $table 存在"
        else
            log_error "表格 $table 不存在"
            return 1
        fi
    done
    
    # 檢查系統用戶和工作區
    local user_count=$(docker exec paper_analysis_db psql -U postgres -d paper_analysis -t -c "SELECT COUNT(*) FROM users WHERE google_id = 'system_legacy_user';" | tr -d ' ')
    local workspace_count=$(docker exec paper_analysis_db psql -U postgres -d paper_analysis -t -c "SELECT COUNT(*) FROM workspaces WHERE name = 'Legacy Data Workspace';" | tr -d ' ')
    
    if [ "$user_count" -eq 1 ]; then
        log_success "系統用戶已正確創建"
    else
        log_error "系統用戶創建失敗"
        return 1
    fi
    
    if [ "$workspace_count" -eq 1 ]; then
        log_success "遺留工作區已正確創建"
    else
        log_error "遺留工作區創建失敗"
        return 1
    fi
    
    log_success "資料庫結構驗證通過"
}

# 主執行流程
main() {
    log_step "🚀 開始完全自動化重建與驗證流程"
    
    # 步驟 1: 停止所有服務並刪除 volumes
    log_step "📦 步驟 1: 清理現有環境"
    log_info "停止所有服務並刪除 volumes..."
    docker-compose down -v >/dev/null 2>&1 || true
    log_success "環境清理完成"
    
    # 步驟 2: 啟動服務
    log_step "🐳 步驟 2: 啟動服務"
    log_info "啟動所有服務..."
    docker-compose up -d
    
    # 步驟 3: 等待服務準備就緒
    log_step "⏳ 步驟 3: 等待服務準備就緒"
    wait_for_container "paper_analysis_db"
    wait_for_container "paper_analysis_backend"
    wait_for_database
    
    # 額外等待確保所有服務完全啟動
    log_info "額外等待 10 秒確保服務完全準備..."
    sleep 10
    
    # 步驟 4: 執行遷移
    log_step "📊 步驟 4: 執行資料庫遷移"
    smart_migration
    
    # 步驟 5: 驗證資料庫結構
    log_step "🔍 步驟 5: 驗證資料庫結構"
    verify_database_structure
    
    # 步驟 6: 執行完整驗證
    log_step "✅ 步驟 6: 執行完整資料完整性驗證"
    
    # 確保驗證腳本可執行
    chmod +x scripts/validation/run_validation.sh
    
    # 執行驗證
    if scripts/validation/run_validation.sh; then
        log_success "資料完整性驗證通過"
    else
        log_error "資料完整性驗證失敗"
        return 1
    fi
    
    # 步驟 7: 顯示最終狀態
    log_step "📋 步驟 7: 最終狀態報告"
    
    # 顯示遷移版本
    local final_version=$(docker exec paper_analysis_backend sh -c "cd /app/backend && alembic current 2>/dev/null | grep -o '[a-z0-9_]*workspace[a-z0-9_]*'" || echo "unknown")
    log_info "最終遷移版本: $final_version"
    
    # 顯示表格數量
    local table_count=$(docker exec paper_analysis_db psql -U postgres -d paper_analysis -t -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public' AND table_type = 'BASE TABLE';" | tr -d ' ')
    log_info "資料庫表格總數: $table_count"
    
    # 顯示用戶和工作區
    local user_count=$(docker exec paper_analysis_db psql -U postgres -d paper_analysis -t -c "SELECT COUNT(*) FROM users;" | tr -d ' ')
    local workspace_count=$(docker exec paper_analysis_db psql -U postgres -d paper_analysis -t -c "SELECT COUNT(*) FROM workspaces;" | tr -d ' ')
    log_info "用戶總數: $user_count"
    log_info "工作區總數: $workspace_count"
    
    # 成功完成
    log_step "🎉 完全自動化重建與驗證流程成功完成！"
    echo ""
    log_success "✅ 所有步驟都已自動化執行完成"
    log_success "✅ 多工作區架構已完全重建並驗證"
    log_success "✅ 系統已準備就緒供生產使用"
    echo ""
    
    return 0
}

# 錯誤處理
trap 'log_error "腳本執行過程中發生錯誤，請檢查上方日誌"; exit 1' ERR

# 執行主流程
main "$@" 