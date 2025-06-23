# Google OAuth 設定指南

## 問題描述
您的學術論文分析系統目前Google登入功能未配置，需要設定Google OAuth憑證。

## 設定步驟

### 1. 獲取Google OAuth憑證

1. 前往 [Google Cloud Console](https://console.cloud.google.com/)
2. 創建新專案或選擇現有專案
3. 啟用 "Google Sign-In API" 或 "Google+ API"
4. 在憑證頁面中，點擊 "建立憑證" → "OAuth 2.0 用戶端 ID"
5. 應用程式類型選擇 "網頁應用程式"
6. 設定授權來源 URI：
   - `http://localhost:20080` (前端URL)
7. 設定授權重新導向 URI：
   - `http://localhost:28001/api/auth/google/callback`

### 2. 設定環境變數

創建 `.env` 檔案（或修改現有的）：

```bash
# Google OAuth 設定
GOOGLE_CLIENT_ID=你的-google-client-id
GOOGLE_CLIENT_SECRET=你的-google-client-secret

# JWT 設定
JWT_SECRET_KEY=your-super-secret-jwt-key-change-this-in-production

# 其他設定
FRONTEND_URL=http://localhost:20080
GOOGLE_REDIRECT_URI=http://localhost:28001/api/auth/google/callback
```

### 3. 重啟系統

```bash
docker-compose down
docker-compose up -d
```

## 目前狀態

- ✅ 系統已修復API路由問題，FileList Failed to Fetch 錯誤已解決
- ⚠️ Google登入功能可以使用，但需要配置OAuth憑證
- ✅ 開發模式下系統會自動使用假認證資料，可以正常使用其他功能

## 暫時解決方案

如果您暫時不想設定Google OAuth，系統會在開發模式下：
1. 自動創建假的認證狀態
2. 提供兩個測試工作區：'first-chat' 和 'second-chat'
3. 所有檔案管理功能都能正常運作

## 驗證設定

設定完成後，您可以檢查：
1. 前往 `http://localhost:28001/api/auth/status` 確認OAuth配置狀態
2. 在前端嘗試Google登入功能
3. 確認檔案列表能正常載入 