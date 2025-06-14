# API 配置系統說明

## 概述

本系統採用環境變量配置方式，允許您靈活設置後端 API 地址和其他相關配置，無需修改代碼即可適應不同的部署環境。

## 配置文件結構

### 主要配置文件

- `src/config/api.config.ts` - 統一的 API 配置管理
- `.env` - 本地環境變量配置文件（需要自行創建）
- `docker-compose.yml` - Docker 環境配置

## 可配置的環境變量

### 必要配置

| 變量名 | 預設值 | 說明 |
|--------|--------|------|
| `VITE_API_BASE_URL` | `http://localhost:28001/api` | 主要後端 API 基礎地址 |
| `VITE_WS_BASE_URL` | `ws://localhost:28001` | WebSocket 連接地址 |

### 可選配置

| 變量名 | 預設值 | 說明 |
|--------|--------|------|
| `VITE_API_TIMEOUT` | `30000` | API 請求超時時間（毫秒） |
| `VITE_SPLIT_SENTENCES_BASE_URL` | `http://localhost:28000` | Split Sentences 服務地址 |
| `VITE_DEBUG_MODE` | `false` | 開發除錯模式 |

### 功能開關

| 變量名 | 預設值 | 說明 |
|--------|--------|------|
| `VITE_USE_UNIFIED_QUERY` | `false` | 是否使用統一查詢系統 |
| `VITE_USE_UNIFIED_FILE_PROCESSOR` | `false` | 是否使用統一檔案處理系統 |
| `VITE_DISABLE_DIRECT_N8N` | `false` | 是否禁用直接 N8N 調用 |

## 使用方法

### 1. 本地開發環境

在專案根目錄創建 `.env` 文件：

```bash
# .env
VITE_API_BASE_URL=http://localhost:28001/api
VITE_WS_BASE_URL=ws://localhost:28001
VITE_API_TIMEOUT=30000
VITE_DEBUG_MODE=true
```

### 2. 生產環境

#### 方法一：環境變量
```bash
export VITE_API_BASE_URL=https://api.yourdomain.com/api
export VITE_WS_BASE_URL=wss://api.yourdomain.com
npm run build
```

#### 方法二：Docker 環境
修改 `docker-compose.yml` 中的環境變量：

```yaml
environment:
  - VITE_API_BASE_URL=https://api.yourdomain.com/api
  - VITE_WS_BASE_URL=wss://api.yourdomain.com
```

### 3. 系統環境變量

您也可以直接設置系統環境變量：

```bash
# Linux/macOS
export VITE_API_BASE_URL=https://api.yourdomain.com/api

# Windows
set VITE_API_BASE_URL=https://api.yourdomain.com/api
```

## 配置驗證

系統會在啟動時自動驗證配置：

1. 檢查必要的配置是否存在
2. 在開發模式下顯示配置信息（需開啟 `VITE_DEBUG_MODE`）
3. 配置錯誤時會在控制台顯示錯誤信息

## 部署範例

### 1. 本地測試環境
```bash
VITE_API_BASE_URL=http://192.168.1.100:28001/api
VITE_WS_BASE_URL=ws://192.168.1.100:28001
```

### 2. 內網部署
```bash
VITE_API_BASE_URL=http://internal-api.company.com:28001/api
VITE_WS_BASE_URL=ws://internal-api.company.com:28001
```

### 3. 雲端部署
```bash
VITE_API_BASE_URL=https://api.yourapp.com/api
VITE_WS_BASE_URL=wss://api.yourapp.com
```

## 故障排除

### 常見問題

1. **API 連接失敗**
   - 檢查 `VITE_API_BASE_URL` 是否正確
   - 確認後端服務是否正常運行
   - 檢查防火牆和網路連接

2. **WebSocket 連接失敗**
   - 檢查 `VITE_WS_BASE_URL` 配置
   - 確認協議（ws:// 或 wss://）是否正確

3. **配置不生效**
   - 確認環境變量名稱以 `VITE_` 開頭
   - 重新構建應用程式
   - 檢查 `.env` 文件格式

### 除錯方法

開啟除錯模式：
```bash
VITE_DEBUG_MODE=true
```

這將在瀏覽器控制台顯示詳細的配置信息和 API 調用日誌。

## 遷移指南

如果您從舊版本升級，請按照以下步驟：

1. 創建 `.env` 文件並設置必要的環境變量
2. 移除代碼中的硬編碼地址
3. 測試所有 API 功能是否正常
4. 更新部署腳本以包含環境變量設置

## 安全注意事項

1. 不要在 `.env` 文件中存放敏感信息
2. 在生產環境中使用 HTTPS/WSS 協議
3. 定期檢查和更新 API 端點的安全性
4. 限制 CORS 設置以提高安全性 