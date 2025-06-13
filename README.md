# 定義類型辨識與查詢系統 (純前端版本)

這是一個基於 React 和 TypeScript 的純前端應用程式，用於識別學術文件中的操作型定義 (OD) 和概念型定義 (CD)，並提供智慧型查詢功能。

## 功能特點

- PDF 文件上傳與處理
- 自動識別操作型定義 (OD) 和概念型定義 (CD)
- 智慧型查詢介面，根據關鍵詞匹配相關定義
- 即時處理進度顯示
- 定義引用與 PDF 內容跳轉
- 完全在瀏覽器中運行，無需後端（僅使用外部 API）

## 技術架構

- **核心框架**: React 18+, TypeScript 5.0+
- **建構工具**: Vite 4+
- **狀態管理**: Zustand
- **API 處理**: TanStack Query (React Query)
- **UI 和樣式**: TailwindCSS, Headless UI
- **PDF 處理**: PDF.js
- **資料存儲**: IndexedDB, LocalStorage

## 外部 API 依賴

- **split_sentences API**: 將 PDF 文檔拆分為句子
- **n8n Webhook APIs**:
  - OD/CD 分類: 識別句子類型
  - 關鍵詞提取: 從查詢中提取關鍵詞
  - 回答組織: 生成基於定義的智慧回答

## 快速開始

### 環境配置

首先創建 `.env` 文件來配置 API 端點：

```bash
# 複製範例配置文件
cp .env.example .env

# 編輯配置（根據您的後端部署地址）
VITE_API_BASE_URL=http://localhost:28001/api
VITE_WS_BASE_URL=ws://localhost:28001
VITE_SPLIT_SENTENCES_BASE_URL=http://localhost:28000
```

> 📋 詳細的配置說明請參考 [API 配置文檔](docs/api-configuration.md)

### 安裝依賴

```bash
npm install
```

### 開發模式運行

```bash
npm run dev
```

### 建置生產版本

```bash
npm run build
```

## 使用說明

1. 上傳 PDF 檔案（學術論文或包含定義的文檔）
2. 等待系統處理並識別定義類型
3. 在查詢欄位輸入問題
4. 系統會提取關鍵詞，找到相關定義，並生成回答
5. 點擊引用可以跳轉到 PDF 中的原始內容

## 資料流程

1. 用戶上傳 PDF → split_sentences API 拆分句子
2. 逐句分析 → n8n OD/CD API 分類句子類型
3. 儲存處理結果 → 本地存儲
4. 用戶輸入查詢 → n8n 關鍵詞 API 提取關鍵詞
5. 本地搜尋相符句子 → 找出相關定義
6. 組織回答 → n8n 組織 API 生成回答
7. 顯示結果 → 帶有引用的回答顯示

## 專案結構

```
src/
├── components/           # React 組件
│   ├── common/          # 通用組件
│   ├── file/            # 檔案相關組件  
│   ├── chat/            # 聊天相關組件
│   └── progress/        # 進度相關組件
├── hooks/               # 自定義 Hooks
├── services/            # API 服務層
├── stores/              # Zustand 狀態管理
├── types/               # TypeScript 類型定義
├── utils/               # 工具函數
└── constants/           # 常量配置
```
