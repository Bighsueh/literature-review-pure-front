# Debug & DB Backlog

> 本文件彙整「檔案上傳流程最後一步在 backend log 出現 db rollback」之完整解決方案待辦清單（Backlog）與例外/除錯步驟（Exception Steps）。所有除錯與驗證作業一律透過 Docker 容器執行，所有日誌查詢一律使用 `docker logs` 指令。
必須在確保前後端原始功能不會出錯的情況下進行伺服器的調整。
專案文檔：/docs
系統流程文檔(重要)：/docs/user_query_flowchart.md & docs/file_upload_flowchart.md
請使用測試上傳檔案：/docs/test.pdf
前端：src/
後端：backend/

---

## 0️⃣ 核心目標
1. 徹底釐清並修正 **未提交事務被自動 ROLLBACK** 的根因。
2. 建立 **一致且可追蹤的資料庫 Schema**，涵蓋上傳流程與使用者查詢流程所需的所有持久化資料。
3. 建立 **可重現的 Debug 流程**，確保未來部署或改動皆能快速定位交易問題。

---

## 1️⃣ Backlog 目錄

| 編號 | 優先級 | 類別 | 事項 | 驗收標準 |
|------|--------|------|------|---------|
| A1 | High | 事務管理 | 對 `services/` 下所有寫入函式補上 `await db.commit()` | 所有更新在 request 結束後仍存在，無多餘 ROLLBACK |
| A2 | High | 事務管理 | 調整 `get_async_db()`：若偵測到有寫入則自動 `commit()`；否則 `rollback()` | SELECT-only 請求不影響資料，寫入請求不丟失 |
| A3 | High | Session | 將 `processing_service` 改為可接受呼叫端 Session 或顯式先 `commit()` 後新開 Session | 背景 Task 可讀取到最新資料 |
| B1 | High | Schema | 建立 `processing_tasks`, `processing_events`, `processing_errors` 三表 | 在上傳/處理期間可實時查詢進度與錯誤 |
| B2 | Medium | Schema | 建立 `user_queries`, `analysis_results`, `analysis_references` 與關聯表 | 可儲存與快取 LLM 分析結果 |
| B3 | Medium | Schema | 為 `sentences` 新增 index `(paper_id, defining_type, sentence_text gin_trgm_ops)` | 關鍵詞搜尋 < 100 ms |
| C1 | Medium | Monitoring | 啟用 SQLAlchemy `echo_pool`, `log_level=INFO` | Docker log 中可見完整 SQL 與連線回收 |
| C2 | Low | Monitoring | 整合 Prometheus + Grafana（或 pg_stat_statements） | 可視化事務衝突與慢查詢 |
| D1 | High | DevOps | 將 `backend` Dockerfile 增加 `--enable-asyncpg-ssl` 與必需 debug 套件 | 利用單一 `docker compose up -d --build` 完成部屬 |
| D2 | High | DevOps | 撰寫 `scripts/dev/print_logs.sh`，封裝 `docker logs -f paper_analysis_backend | cat` | 團隊成員可一鍵查看即時 log |
| D3 | Low | DevOps | CI pipeline 加入 `pytest` + `mypy` + `ruff` | PR 需通過所有檢查才能合併 |

> 備註：High＝兩週內完成；Medium＝一個月內；Low＝排期視情況調整。

---

## 2️⃣ 詳細工作拆解

### A. 事務與 Session 管理
1. **程式碼審計**：
   - 逐一檢查 `backend/services/*.py` 與 `backend/api/*.py`。
   - 搜尋所有 `db.add(`、`db.delete(`、欄位直接賦值 (`model.attr = x`) 後未呼叫 `commit()` 的位置。
2. **自動化測試**：
   - 新增 pytest 測試覆蓋 `mark_paper_selected`、`update_status` 等函式，驗證資料在請求結束後仍存在。
3. **依賴調整**：
   - 在 `database/connection.py` 的 `get_async_db()`：
     ```python
     try:
         yield session
         if session.dirty or session.new or session.deleted:
             await session.commit()
     finally:
         await session.rollback()
         await session.close()
     ```
4. **Session 傳遞**：
   - 讓 `processing_service.process_file()` 接收現有 `AsyncSession` 或於呼叫前 `await db.commit()`。

### B. Schema 擴充與演進
1. **資料表 DDL 草稿**（以 Alembic migration 實作）：
   ```sql
   CREATE TABLE processing_tasks (
     id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
     paper_id UUID REFERENCES papers(id) ON DELETE CASCADE,
     task_id VARCHAR(64) NOT NULL,
     priority SMALLINT DEFAULT 2,
     retries SMALLINT DEFAULT 0,
     status VARCHAR(32) NOT NULL,
     started_at TIMESTAMPTZ,
     finished_at TIMESTAMPTZ,
     created_at TIMESTAMPTZ DEFAULT now()
   );
   ```
   > 其餘表格參考 docs 設計，於後續 migration 補齊。
2. **漸進式上線**：
   - 先實作 **只寫** `processing_tasks` 與 `processing_events`，觀察無業務衝擊後再擴展其他表。

### C. Logging & Monitoring
1. **SQL 可觀測性**：在 `settings.py` 調整：
   ```python
   SQLALCHEMY_ECHO=True
   SQLALCHEMY_ECHO_POOL=True
   LOG_LEVEL="INFO"
   ```
2. **統一日誌格式**：採用 `uvicorn --log-config logging.yaml`，確保容器 log 可被 `docker logs` 解析（JSONLine 或 key=value）。

### D. Containerized Debug 流程
1. **本地重現步驟**：
   ```bash
   # 啟動環境並重新構建
   docker compose down -v
   docker compose up -d --build backend
   
   # 送出測試上傳請求
   curl -F "file=@tests/sample.pdf" http://localhost:8000/upload/
   
   # 即時查看 backend log
   docker logs -f paper_analysis_backend --tail 300 | cat
   ```
2. **常用指令速查**：
   | 操作 | 指令 |
   |------|------|
   | 查看所有容器 | `docker ps` |
   | 進入 DB 容器 | `docker exec -it paper_analysis_postgres psql -U postgres` |
   | 停止並刪除 | `docker compose down -v` |

---

## 3️⃣ 例外 / 除錯步驟 (Runbook)

| 編號 | 場景 | 立即動作 | 深入調查 |
|------|------|-----------|-----------|
| E1 | 上傳 API 返回 500 | 1. `docker logs paper_analysis_backend --tail 200 | cat`  <br>2. 確認 traceback | a. 檢查 `processing_errors` 是否有新記錄 <br>b. `psql` 查 `papers` status |
| E2 | 前端顯示「進度卡住」 | 1. `docker logs paper_analysis_backend | grep "progress"` <br>2. 查看 `processing_events` 最新時間 | a. 若無 events，檢查 `processing_tasks.status` <br>b. 重啟 worker：`docker compose restart backend` |
| E3 | 資料被 rollback | 1. 在 Log 搜尋 `ROLLBACK` 同行 SQL | a. 找到對應函式，確認是否漏 `commit()` |
| E4 | Query 分析結果重算 | 1. 檢查 `analysis_results` 是否已有相同 query & selected_sections | a. 若已存在，回傳快取 <br>b. 若重算，重置 tokens 記錄 |

> 所有步驟完成後，**務必在對應 GitHub Issue 更新進度**，並於 PR 說明 *影響範圍* 與 *回滾策略*。

---

## 4️⃣ 時程建議 (Milestone)

1. **M1（本週）**：完成 A1~A3、D1~D2；確保基本寫入不被 rollback。
2. **M2（+2 週）**：完成 B1 + 部分 B2；進度與錯誤可於前端顯示。
3. **M3（+4 週）**：完成 C1~C2、B3、D3；建立監控與 CI。
4. **M4（+6 週）**：全量上線所有新 Schema，移除舊欄位／過時程式碼。

---

### ↩️ 版本控制與回滾
* 所有 migration 使用 **Alembic**；重大變動需編寫 `downgrade()`。
* Docker Image 標籤：`backend:<semver>-<gitsha>`；部署若失敗可 `docker compose pull backend:<prev>` 回滾。

---

> **最後提醒：** 無論是本地或 CI/CD，請確保 *每一次 debug 部署都走 Docker*，並且 *每一次檢視 log 都走 `docker logs`*，保持環境一致與可追溯性。 