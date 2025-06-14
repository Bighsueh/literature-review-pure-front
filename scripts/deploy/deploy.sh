#!/bin/bash

# 增強的部署腳本 - 包含 Schema 驗證和自動遷移
# 適用於開發、測試和生產環境

set -euo pipefail  # 嚴格模式

# 顏色定義
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

# 配置
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
ENVIRONMENT="${1:-development}"
SKIP_TESTS="${SKIP_TESTS:-false}"
SKIP_SCHEMA_VALIDATION="${SKIP_SCHEMA_VALIDATION:-false}"
BACKUP_ENABLED="${BACKUP_ENABLED:-true}"

log_info "開始部署到環境: $ENVIRONMENT"
log_info "專案根目錄: $PROJECT_ROOT"

# 切換到專案根目錄
cd "$PROJECT_ROOT"

# 步驟 1: 環境檢查
log_info "步驟 1: 環境檢查"

# 檢查 Docker 是否運行
if ! docker info > /dev/null 2>&1; then
    log_error "Docker 未運行，請先啟動 Docker"
    exit 1
fi

# 檢查 docker-compose 是否可用
if ! command -v docker-compose > /dev/null 2>&1; then
    log_error "docker-compose 未安裝"
    exit 1
fi

log_success "環境檢查通過"

# 步驟 2: 資料庫備份（生產環境）
if [[ "$ENVIRONMENT" == "production" && "$BACKUP_ENABLED" == "true" ]]; then
    log_info "步驟 2: 創建資料庫備份"
    
    BACKUP_DIR="backups"
    mkdir -p "$BACKUP_DIR"
    
    BACKUP_FILE="$BACKUP_DIR/paper_analysis_$(date +%Y%m%d_%H%M%S).sql"
    
    if docker exec paper_analysis_db pg_dump -U postgres paper_analysis > "$BACKUP_FILE" 2>/dev/null; then
        log_success "資料庫備份完成: $BACKUP_FILE"
    else
        log_warning "資料庫備份失敗，可能是首次部署"
    fi
else
    log_info "步驟 2: 跳過資料庫備份 (環境: $ENVIRONMENT)"
fi

# 步驟 3: 拉取最新程式碼（如果是 Git 專案）
if [[ -d ".git" ]]; then
    log_info "步驟 3: 拉取最新程式碼"
    
    # 檢查是否有未提交的更改
    if [[ -n "$(git status --porcelain)" ]]; then
        log_warning "發現未提交的更改"
        git status --short
        read -p "是否繼續部署？(y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            log_error "部署被取消"
            exit 1
        fi
    fi
    
    # 拉取最新代碼
    git pull origin main || {
        log_error "拉取程式碼失敗"
        exit 1
    }
    
    log_success "程式碼更新完成"
else
    log_info "步驟 3: 跳過程式碼拉取 (非 Git 專案)"
fi

# 步驟 4: 構建 Docker 映像
log_info "步驟 4: 構建 Docker 映像"

docker-compose build --no-cache || {
    log_error "Docker 映像構建失敗"
    exit 1
}

log_success "Docker 映像構建完成"

# 步驟 5: 啟動資料庫（如果尚未運行）
log_info "步驟 5: 啟動資料庫服務"

# 僅啟動資料庫服務
docker-compose up -d db || {
    log_error "資料庫服務啟動失敗"
    exit 1
}

# 等待資料庫就緒
log_info "等待資料庫服務就緒..."
for i in {1..30}; do
    if docker exec paper_analysis_db pg_isready -U postgres > /dev/null 2>&1; then
        log_success "資料庫服務已就緒"
        break
    fi
    
    if [[ $i -eq 30 ]]; then
        log_error "資料庫服務啟動超時"
        exit 1
    fi
    
    sleep 2
done

# 步驟 6: Schema 驗證
if [[ "$SKIP_SCHEMA_VALIDATION" != "true" ]]; then
    log_info "步驟 6: Schema 驗證"
    
    # 建立 Python 虛擬環境並安裝依賴（如果需要）
    if [[ ! -d "venv" ]]; then
        python3 -m venv venv
        source venv/bin/activate
        pip install -r backend/requirements.txt
    else
        source venv/bin/activate
    fi
    
    # 執行 Schema 驗證
    if python scripts/deploy/schema_validator.py; then
        log_success "Schema 驗證通過"
    else
        log_error "Schema 驗證失敗"
        
        # 詢問是否繼續
        if [[ "$ENVIRONMENT" == "production" ]]; then
            log_error "生產環境 Schema 驗證失敗，部署終止"
            exit 1
        else
            read -p "Schema 驗證失敗，是否繼續部署？(y/N): " -n 1 -r
            echo
            if [[ ! $REPLY =~ ^[Yy]$ ]]; then
                log_error "部署被取消"
                exit 1
            fi
        fi
    fi
else
    log_info "步驟 6: 跳過 Schema 驗證"
fi

# 步驟 7: 執行資料庫遷移
log_info "步驟 7: 執行資料庫遷移"

# 使用 Python 執行遷移
if python -c "
import sys
sys.path.append('backend')
import asyncio
from simplified_migration import ensure_database_schema

try:
    success = asyncio.run(ensure_database_schema())
    if success:
        print('SUCCESS: 遷移完成')
    else:
        print('ERROR: 遷移失敗')
        sys.exit(1)
except Exception as e:
    print(f'ERROR: 遷移失敗 - {e}')
    sys.exit(1)
"; then
    log_success "資料庫遷移完成"
else
    log_error "資料庫遷移失敗"
    exit 1
fi

# 步驟 8: 運行測試（可選）
if [[ "$SKIP_TESTS" != "true" ]]; then
    log_info "步驟 8: 運行測試"
    
    # 啟動測試環境
    docker-compose up -d
    
    # 等待服務就緒
    sleep 10
    
    # 運行基本健康檢查
    if curl -f http://localhost:8001/docs > /dev/null 2>&1; then
        log_success "應用程式健康檢查通過"
    else
        log_error "應用程式健康檢查失敗"
        exit 1
    fi
    
    # 如果有測試腳本，運行它們
    if [[ -f "emergency_fix_verification.py" ]]; then
        if python emergency_fix_verification.py; then
            log_success "驗證測試通過"
        else
            log_error "驗證測試失敗"
            exit 1
        fi
    fi
else
    log_info "步驟 8: 跳過測試"
fi

# 步驟 9: 啟動完整服務
log_info "步驟 9: 啟動完整服務"

docker-compose down
docker-compose up -d || {
    log_error "服務啟動失敗"
    exit 1
}

# 步驟 10: 部署後驗證
log_info "步驟 10: 部署後驗證"

# 等待服務完全啟動
sleep 15

# 檢查服務狀態
if docker-compose ps | grep -q "Up"; then
    log_success "所有服務正在運行"
else
    log_error "部分服務未正常啟動"
    docker-compose ps
    exit 1
fi

# 檢查 API 端點
if curl -f http://localhost:8001/api/papers/ > /dev/null 2>&1; then
    log_success "API 端點正常回應"
else
    log_error "API 端點無法回應"
    exit 1
fi

# 步驟 11: 清理
log_info "步驟 11: 清理"

# 清理舊的 Docker 映像
docker image prune -f > /dev/null 2>&1 || true

# 清理臨時文件
rm -f schema_validation_result.json > /dev/null 2>&1 || true

log_success "清理完成"

# 部署完成
echo
echo "========================================"
log_success "部署完成！"
echo "========================================"
echo
echo "🌐 應用程式 URL: http://localhost:3000"
echo "📚 API 文檔: http://localhost:8001/docs"
echo "🗄️  資料庫: localhost:5432"
echo
echo "📋 服務狀態:"
docker-compose ps

echo
echo "📝 快速檢查指令:"
echo "  查看日誌: docker-compose logs -f"
echo "  查看特定服務日誌: docker-compose logs -f [service_name]"
echo "  重啟服務: docker-compose restart"
echo "  停止服務: docker-compose down"
echo

log_info "部署腳本執行完成" 