#!/bin/bash

# Docker Logs 查看腳本
# 用於統一查看 paper_analysis_backend 容器的日誌

set -e

# 設定顏色
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 預設參數
CONTAINER_NAME="paper_analysis_backend"
TAIL_LINES=300
FOLLOW=false
SHOW_TIMESTAMP=false

# 顯示使用說明
show_help() {
    echo -e "${GREEN}Docker Logs 查看腳本${NC}"
    echo ""
    echo "用法: $0 [選項]"
    echo ""
    echo "選項:"
    echo "  -h, --help          顯示此說明"
    echo "  -f, --follow        持續追蹤日誌 (類似 tail -f)"
    echo "  -t, --tail LINES    顯示最後 N 行 (預設: 300)"
    echo "  -s, --since TIME    顯示指定時間後的日誌 (如: '5m', '1h', '2023-01-01')"
    echo "  -c, --container NAME 指定容器名稱 (預設: paper_analysis_backend)"
    echo "  --timestamp         顯示時間戳記"
    echo "  --all-containers    顯示所有相關容器的日誌"
    echo ""
    echo "範例:"
    echo "  $0                           # 顯示最後 300 行日誌"
    echo "  $0 -f                        # 持續追蹤日誌"
    echo "  $0 -t 100                    # 顯示最後 100 行"
    echo "  $0 -s 5m                     # 顯示最近 5 分鐘的日誌"
    echo "  $0 --all-containers          # 顯示所有容器日誌"
}

# 檢查容器是否存在且運行中
check_container() {
    local container=$1
    
    if ! docker ps --format "table {{.Names}}" | grep -q "^${container}$"; then
        echo -e "${YELLOW}警告: 容器 '${container}' 未運行${NC}"
        
        # 檢查是否存在但已停止
        if docker ps -a --format "table {{.Names}}" | grep -q "^${container}$"; then
            echo -e "${BLUE}容器存在但已停止，嘗試啟動...${NC}"
            docker start "${container}" || {
                echo -e "${RED}錯誤: 無法啟動容器 '${container}'${NC}"
                return 1
            }
            sleep 2
        else
            echo -e "${RED}錯誤: 容器 '${container}' 不存在${NC}"
            echo -e "${BLUE}可用的容器:${NC}"
            docker ps -a --format "table {{.Names}}\t{{.Status}}"
            return 1
        fi
    fi
    
    return 0
}

# 顯示所有相關容器的日誌
show_all_containers() {
    echo -e "${GREEN}=== 顯示所有相關容器日誌 ===${NC}"
    
    # 定義相關容器
    local containers=("paper_analysis_backend" "paper_analysis_postgres" "paper_analysis_frontend")
    
    for container in "${containers[@]}"; do
        if docker ps --format "table {{.Names}}" | grep -q "^${container}$"; then
            echo -e "${BLUE}--- 容器: ${container} ---${NC}"
            docker logs --tail 50 "${container}" 2>&1 | cat
            echo ""
        fi
    done
}

# 解析命令行參數
SINCE=""
ALL_CONTAINERS=false

while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            show_help
            exit 0
            ;;
        -f|--follow)
            FOLLOW=true
            shift
            ;;
        -t|--tail)
            TAIL_LINES="$2"
            shift 2
            ;;
        -s|--since)
            SINCE="$2"
            shift 2
            ;;
        -c|--container)
            CONTAINER_NAME="$2"
            shift 2
            ;;
        --timestamp)
            SHOW_TIMESTAMP=true
            shift
            ;;
        --all-containers)
            ALL_CONTAINERS=true
            shift
            ;;
        *)
            echo -e "${RED}未知選項: $1${NC}"
            show_help
            exit 1
            ;;
    esac
done

# 如果選擇顯示所有容器
if [[ "$ALL_CONTAINERS" == true ]]; then
    show_all_containers
    exit 0
fi

# 檢查容器狀態
if ! check_container "$CONTAINER_NAME"; then
    exit 1
fi

# 建構 docker logs 命令
DOCKER_CMD="docker logs"

# 添加參數
if [[ "$SHOW_TIMESTAMP" == true ]]; then
    DOCKER_CMD+=" --timestamps"
fi

if [[ -n "$SINCE" ]]; then
    DOCKER_CMD+=" --since $SINCE"
else
    DOCKER_CMD+=" --tail $TAIL_LINES"
fi

if [[ "$FOLLOW" == true ]]; then
    DOCKER_CMD+=" --follow"
fi

DOCKER_CMD+=" $CONTAINER_NAME"

# 顯示執行的命令
echo -e "${GREEN}執行: ${DOCKER_CMD}${NC}"
echo -e "${BLUE}容器: ${CONTAINER_NAME}${NC}"
echo -e "${BLUE}按 Ctrl+C 退出${NC}"
echo ""

# 執行命令並使用 cat 避免分頁
eval "$DOCKER_CMD" 2>&1 | cat 