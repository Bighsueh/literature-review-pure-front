#!/bin/bash

# =============================================================================
# 學術研究管理平台 - 自動化部署腳本
# =============================================================================
# 功能：從全新環境自動化部署整個多工作區架構系統
# 作者：AI Assistant
# 版本：v1.0
# =============================================================================

set -e

# 顏色輸出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

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
    echo -e "${YELLOW}========================================${NC}"
    echo -e "${YELLOW}$1${NC}"
    echo -e "${YELLOW}========================================${NC}"
}

# 檢查 Docker 環境
check_docker() {
    log_info "檢查 Docker 環境..."
    
    if ! command -v docker &> /dev/null; then
        log_error "Docker 未安裝，請先安裝 Docker"
        exit 1
    fi
    
    if ! command -v docker-compose &> /dev/null; then
        log_error "Docker Compose 未安裝，請先安裝 Docker Compose"
        exit 1
    fi
    
    if ! docker info >/dev/null 2>&1; then
        log_error "Docker 服務未運行，請啟動 Docker"
        exit 1
    fi
    
    log_success "Docker 環境檢查通過"
}

# 檢查必要文件
check_required_files() {
    log_info "檢查必要文件..."
    
    local required_files=(
        "docker-compose.yml"
        "backend/Dockerfile"
        "backend/requirements.txt"
        "backend/alembic.ini"
        "backend/migrations/env.py"
    )
    
    for file in "${required_files[@]}"; do
        if [ ! -f "$file" ]; then
            log_error "必要文件不存在: $file"
            exit 1
        fi
        log_success "文件檢查通過: $file"
    done
}

# 構建並啟動服務
build_and_start() {
    log_info "構建並啟動所有服務..."
    
    # 構建所有鏡像
    docker-compose build --no-cache
    
    # 啟動服務
    docker-compose up -d
    
    log_success "服務啟動完成"
}

# 等待服務準備就緒
wait_for_services() {
    log_info "等待服務準備就緒..."
    
    # 等待資料庫
    local max_attempts=60
    local attempt=1
    
    while [ $attempt -le $max_attempts ]; do
        if docker exec paper_analysis_db pg_isready -U postgres >/dev/null 2>&1; then
            log_success "PostgreSQL 已準備就緒"
            break
        fi
        
        log_info "等待 PostgreSQL... ($attempt/$max_attempts)"
        sleep 2
        attempt=$((attempt + 1))
        
        if [ $attempt -gt $max_attempts ]; then
            log_error "PostgreSQL 啟動超時"
            exit 1
        fi
    done
    
    # 等待後端服務
    attempt=1
    while [ $attempt -le $max_attempts ]; do
        if docker ps --filter "name=paper_analysis_backend" --filter "status=running" | grep -q paper_analysis_backend; then
            log_success "後端服務已準備就緒"
            break
        fi
        
        log_info "等待後端服務... ($attempt/$max_attempts)"
        sleep 2
        attempt=$((attempt + 1))
        
        if [ $attempt -gt $max_attempts ]; then
            log_error "後端服務啟動超時"
            exit 1
        fi
    done
    
    # 額外等待確保服務完全啟動
    log_info "額外等待 15 秒確保服務完全準備..."
    sleep 15
}

# 執行資料庫遷移
run_migrations() {
    log_info "執行資料庫遷移..."
    
    # 檢查 Alembic 配置
    if ! docker exec paper_analysis_backend sh -c "cd /app/backend && ls alembic.ini" >/dev/null 2>&1; then
        log_error "Alembic 配置文件不存在"
        exit 1
    fi
    
    # 執行遷移
    docker exec paper_analysis_backend sh -c "cd /app/backend && alembic upgrade head"
    
    log_success "資料庫遷移完成"
}

# 驗證部署
verify_deployment() {
    log_info "驗證部署結果..."
    
    # 檢查容器狀態
    local containers=("paper_analysis_db" "paper_analysis_backend" "react-frontend")
    
    for container in "${containers[@]}"; do
        if docker ps --filter "name=$container" --filter "status=running" | grep -q $container; then
            log_success "容器 $container 運行正常"
        else
            log_error "容器 $container 未正常運行"
            exit 1
        fi
    done
    
    # 檢查資料庫連接
    if docker exec paper_analysis_db psql -U postgres -d paper_analysis -c "SELECT 1;" >/dev/null 2>&1; then
        log_success "資料庫連接正常"
    else
        log_error "資料庫連接失敗"
        exit 1
    fi
    
    # 檢查表格存在
    local table_count=$(docker exec paper_analysis_db psql -U postgres -d paper_analysis -t -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public' AND table_type = 'BASE TABLE';" | tr -d ' ')
    
    if [ "$table_count" -ge 10 ]; then
        log_success "資料庫表格創建正常 ($table_count 個表格)"
    else
        log_error "資料庫表格創建異常 (僅 $table_count 個表格)"
        exit 1
    fi
    
    # 檢查多工作區架構
    if docker exec paper_analysis_db psql -U postgres -d paper_analysis -c "\dt" | grep -q "users\|workspaces\|chat_histories"; then
        log_success "多工作區架構部署成功"
    else
        log_error "多工作區架構部署失敗"
        exit 1
    fi
}

# 顯示部署信息
show_deployment_info() {
    log_step "📋 部署信息"
    
    # 獲取服務狀態
    echo "🔧 服務狀態:"
    docker-compose ps
    echo ""
    
    # 獲取版本信息
    local migration_version=$(docker exec paper_analysis_backend sh -c "cd /app/backend && alembic current 2>/dev/null | grep -o '[a-z0-9_]*workspace[a-z0-9_]*'" || echo "unknown")
    echo "📊 遷移版本: $migration_version"
    
    # 獲取表格統計
    local table_count=$(docker exec paper_analysis_db psql -U postgres -d paper_analysis -t -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public' AND table_type = 'BASE TABLE';" | tr -d ' ')
    echo "📋 資料庫表格: $table_count 個"
    
    # 獲取用戶統計
    local user_count=$(docker exec paper_analysis_db psql -U postgres -d paper_analysis -t -c "SELECT COUNT(*) FROM users;" | tr -d ' ')
    local workspace_count=$(docker exec paper_analysis_db psql -U postgres -d paper_analysis -t -c "SELECT COUNT(*) FROM workspaces;" | tr -d ' ')
    echo "👥 系統用戶: $user_count 個"
    echo "🏢 工作區: $workspace_count 個"
    
    echo ""
    echo "🌐 服務端點:"
    echo "  - 前端: http://localhost:20080"
    echo "  - 後端 API: http://localhost:28001"
    echo "  - 文件處理服務: http://localhost:28000"
    echo "  - PostgreSQL: localhost:25432"
    echo ""
}

# 主流程
main() {
    log_step "🚀 開始自動化部署學術研究管理平台"
    
    # 環境檢查
    log_step "🔍 步驟 1: 環境檢查"
    check_docker
    check_required_files
    
    # 清理現有環境
    log_step "🧹 步驟 2: 清理現有環境"
    log_info "停止並清理現有服務..."
    docker-compose down -v >/dev/null 2>&1 || true
    log_success "環境清理完成"
    
    # 構建並啟動
    log_step "🏗️ 步驟 3: 構建並啟動服務"
    build_and_start
    
    # 等待服務準備
    log_step "⏳ 步驟 4: 等待服務準備就緒"
    wait_for_services
    
    # 執行遷移
    log_step "📊 步驟 5: 執行資料庫遷移"
    run_migrations
    
    # 驗證部署
    log_step "✅ 步驟 6: 驗證部署結果"
    verify_deployment
    
    # 顯示部署信息
    show_deployment_info
    
    # 完成
    log_step "🎉 部署成功完成！"
    echo ""
    log_success "✅ 學術研究管理平台已成功部署"
    log_success "✅ 多工作區架構已啟用"
    log_success "✅ 系統已準備就緒供使用"
    echo ""
    
    return 0
}

# 錯誤處理
trap 'log_error "部署過程中發生錯誤，請檢查上方日誌"; exit 1' ERR

# 執行主流程
main "$@" 