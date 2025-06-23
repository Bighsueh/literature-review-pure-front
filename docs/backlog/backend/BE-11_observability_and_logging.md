# Backlog: BE-11 - 可觀測性與集中式日誌

- **Epic:** 後端 API 改造
- **狀態:** To Do
- **優先級:** Medium
- **估算 (Story Points):** 4

---

### 使用者故事 (User Story)

**身為** 後端維運工程師，
**我想要** 在單一介面觀察系統的指標 (metrics)、追蹤 (traces) 與日誌 (logs)，
**以便** 能快速定位問題並評估系統健康狀態。

---

### 驗收標準 (Acceptance Criteria)

1. **中央日誌平台**
   - [ ] FastAPI 與背景工作都透過 `structlog` 或 `loguru` 輸出結構化 JSON 日誌。
   - [ ] 日誌經由 Loki/Fluentd/Elasticsearch 之一路徑集中收集，並可在 Grafana 或 Kibana 查詢。

2. **Metrics 暴露**
   - [ ] 透過 `prometheus-fastapi-instrumentator` 暴露 `/metrics` 端點。
   - [ ] 收集關鍵指標：請求量、延遲、錯誤率、背景任務耗時。

3. **Tracing**
   - [ ] OpenTelemetry SDK 已初始化，並將 traces 匯出到 Jaeger 或 OTLP Collector。
   - [ ] 對外部呼叫（資料庫、HTTP 服務）自動注入 Trace Context。

4. **告警**
   - [ ] 設定 95/99 latency、error rate 等告警規則於 Prometheus Alertmanager。

---

### 技術筆記 (Technical Notes)

- 選用輕量方案：`grafana/loki` + `promtail` + `prometheus` + `grafana` + `jaeger-all-in-one` in docker-compose。
- 為避免影響開發效率，可在 `DEV_MODE` 關閉 Tracing。
- // FE NOTE: 此 Story 僅後端，前端無改動。 