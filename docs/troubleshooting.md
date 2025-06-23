# Docker 部署故障排除指南

本文件列舉最常見的容器啟動與執行問題，並提供對應解決方案。

| 編號 | 症狀 | 可能原因 | 解決步驟 |
|------|------|----------|-----------|
| T-01 | `backend` 容器反覆重啟 | `.env` 配置不完整或外部服務未啟動 | 1. `docker-compose logs backend -n 50` 查看錯誤訊息 <br> 2. 確認 `GROBID_URL`、`N8N_BASE_URL` 是否可連線 <br> 3. 更新 `.env` 後 `docker-compose up -d backend --force-recreate` |
| T-02 | 上傳 PDF 卡在 `processing` | Grobid 連線失敗或 PDF 過大 | 1. `curl <GROBID_URL>/api/isalive` 檢查 Grobid <br> 2. 調整 `MAX_FILE_SIZE_MB` 或使用較小檔案 |
| T-03 | 智慧查詢 API 回傳 502 | n8n Webhook URL 錯誤或 LLM 配額用盡 | 1. 透過 n8n UI 重新 Deploy workflow <br> 2. 檢查 LLM Provider 餘額或速率限制 |
| T-04 | 前端顯示 `Network Error` | `VITE_API_BASE_URL` 配置錯誤 | 1. 確認 `.env` 內 Vite 變數 <br> 2. 重新建置前端 `docker-compose up -d --build react` |
| T-05 | `split_sentences` 服務變 `unhealthy` | Redis 未啟動或 PDF 無法解析 | 1. `docker-compose logs split_sentences -n 50` <br> 2. 檢查 `upload_data` 目錄是否存在損壞檔案 |

> 若上述步驟仍無法解決，請建立 Issue 並附上相關容器 log 及 `.env`（遮蔽敏感資料）。 