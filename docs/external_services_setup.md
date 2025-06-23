# 外部依賴服務架設指南

本文件介紹專案執行前必需的兩項外部服務：**Grobid** 與 **n8n**，及其建議安裝方式與設定步驟。

> 🛠️ *所有指令皆以 macOS / Linux Bash 為例，Windows 亦可使用 WSL 或 PowerShell 對應指令。*

---

## 1. Grobid Server

Grobid (GeneRation Of BIbliographic Data) 係一套開源 PDF 解析工具，可將論文轉換為 TEI XML。系統透過 Grobid 擷取章節與句子，屬於**必要服務**。

### 1.1 快速安裝

```bash
docker run -d \
  --name grobid \
  -p 8070:8070 \
  lfoppiano/grobid:0.8.0
```

- `-d`：背景模式
- `-p 8070:8070`：將容器 Port 8070 映射至本機 8070

### 1.2 健康檢查

```bash
curl http://localhost:8070/api/isalive  # 回傳 "true" 表示健康
```

### 1.3 進階設定

- 若需提高併發，請於 `grobid.properties` 調升 `org.grobid.batch.max.parallel(=10)`。
- 可將模型快取掛載 Volume 避免每次重建重新下載。

---

## 2. n8n Server

n8n 為開源自動化工作流程工具，於本專案負責觸發 LLM、規劃與組織回答等邏輯。

### 2.1 快速安裝

```bash
docker run -d \
  --name n8n \
  -p 5678:5678 \
  -e N8N_BASIC_AUTH_ACTIVE=true \
  -e N8N_BASIC_AUTH_USER=admin \
  -e N8N_BASIC_AUTH_PASSWORD=admin123 \
  -v n8n_data:/home/node/.n8n \
  n8nio/n8n:1.46.0
```

- 建議設定 Basic Auth 以保護工作流程 UI。
- 資料卷 `n8n_data` 用於持久化 workflow 設定與 credentials。

### 2.2 匯入 Workflow

1. 開啟瀏覽器 `http://localhost:5678` 並以 Basic Auth 登入。
2. 點選 *Import*，匯入 `docs/n8n_api_document.md` 中提供的 JSON 範本，或自行建立相同路由。
3. 確認下列 Webhook URL 與 `docs/n8n_api_document.md` 一致：
   - `/webhook/intelligent_section_selection`
   - `/webhook/query_keyword_extraction`
   - `/webhook/unified_content_analysis`

### 2.3 設定 LLM Provider

依實際需求於 *Credentials* 中新增 OpenAI / Gemini 等 Key，並在 Workflow 節點內選擇。

---

## 3. 整合測試

完成上述安裝後，請依序：

1. 於 `.env` 設定 `GROBID_URL=http://localhost:8070` 與 `N8N_BASE_URL=http://localhost:5678`。
2. 重新啟動 `docker-compose up -d --force-recreate backend`。
3. 呼叫後端健康檢查：
   ```bash
   curl http://localhost:28001/api/health/detailed | jq .
   ```
   - `status` 應顯示 `healthy`。
4. 透過前端上傳一份 PDF，觀察 n8n Workflow Log 是否正確執行。

若有連線錯誤，可檢查：
- 防火牆或公司 Proxy 是否攔截 8070/5678 Port。
- Docker Bridge 網路名稱與 `.env` Host 是否一致。

---

## 4. 常見問題

| 問題 | 解決方案 |
|------|-----------|
| Grobid 回傳 404 | 確認呼叫 URL 是否包含 `/api/processFulltextDocument` 路徑 |
| n8n Webhook 未觸發 | Workflow 須在 **Active** 狀態，或檢查 Basic Auth 是否阻擋外部呼叫 |
| LLM 回傳 429 | 速率限制，可於 n8n Workflow 增加 *Wait* 節點或升級方案 | 