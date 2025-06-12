# BACKLOG-FIX-03: 手動端到端測試案例

## 概述

本文件定義了 BACKLOG-FIX-03「端到端流程驗證」的完整手動測試案例，確保整個使用者查詢流程從前端到後端都能正常運作，特別針對 `definitions` 類型的查詢進行驗證。

## 前置條件

### 系統環境
- ✅ Docker 和 Docker Compose 已安裝並運行
- ✅ 前端服務運行在 `http://localhost:3000`
- ✅ 後端服務運行在 `http://localhost:8001`
- ✅ 資料庫已初始化且有測試資料

### 測試資料
- 📄 **測試文件**: `docs/test.pdf`（如果存在）或任何包含定義的學術論文
- 🔍 **測試查詢**: `"What is the definition of adaptive expertise?"`

---

## 測試案例 TC-01: 完整端到端流程

### 測試目標
驗證從論文上傳到查詢結果顯示的完整流程，特別是 `definitions` 查詢的處理。

### 測試步驟

#### 步驟 1: 環境準備
```bash
# 1.1 確認 Docker 容器狀態
docker-compose ps

# 1.2 檢查後端健康狀態
curl http://localhost:8001/health

# 1.3 檢查前端可訪問性
curl http://localhost:3000
```

**預期結果:**
- 所有容器處於 `Up` 狀態
- 後端回傳健康檢查成功
- 前端頁面正常載入

#### 步驟 2: 論文上傳與處理
```bash
# 2.1 開啟瀏覽器訪問前端
open http://localhost:3000

# 2.2 在前端介面上傳測試論文
# （手動操作）上傳 docs/test.pdf 或其他包含定義的論文

# 2.3 等待論文處理完成
# 觀察左側論文列表，確認檔案狀態變為「已完成」並顯示勾選框
```

**預期結果:**
- 論文成功上傳
- 系統完成論文解析和章節分析
- 左側列表顯示論文狀態為「已完成」
- 論文前方出現可勾選的複選框

#### 步驟 3: 論文選取
```bash
# 3.1 勾選已處理完成的論文
# （手動操作）點擊論文前的複選框

# 3.2 驗證後端狀態更新
curl "http://localhost:8001/api/papers/selected"
```

**預期結果:**
- 前端複選框顯示為選中狀態
- 後端 API 回傳包含選中論文的清單
- 聊天輸入框從「論文處理中，請稍候...」變為「輸入你的查詢...」

#### 步驟 4: 執行 Definitions 查詢
```bash
# 4.1 在聊天輸入框輸入測試查詢
# 輸入: "What is the definition of adaptive expertise?"
# （手動操作）點擊發送按鈕

# 4.2 監控後端日誌
docker logs backend --tail 50 -f
```

**預期結果:**
- 查詢成功提交到後端
- 後端日誌顯示查詢處理流程：
  - ✅ 接收到查詢請求
  - ✅ 獲取選中論文資料
  - ✅ 調用 intelligent_section_selection
  - ✅ 檢測到 focus_type="definitions"
  - ✅ 執行關鍵詞提取
  - ✅ 從資料庫獲取章節句子
  - ✅ 篩選 OD/CD 定義句子
  - ✅ 調用 unified_content_analysis
  - ✅ 返回包含引用標記的結果

#### 步驟 5: 驗證查詢結果
**檢查項目:**

1. **結果結構完整性**
   - 前端顯示查詢結果
   - 結果包含有意義的文字內容
   - 不是錯誤訊息或假資料

2. **引用標記存在**
   - 結果中包含 `[[ref:...]]` 格式的引用標記
   - 引用標記可點擊並顯示來源資訊

3. **內容相關性**
   - 結果內容與「定義」查詢相關
   - 提到了論文中的實際定義內容

4. **來源可追溯**
   - 顯示引用來源的論文名稱、章節、頁數
   - 引用內容與原文相符

---

## 測試案例 TC-02: 系統容錯性測試

### 測試目標
驗證系統在各種異常情況下的處理能力。

### 測試步驟

#### 步驟 2.1: 無論文選取的情況
```bash
# 2.1.1 確保沒有論文被選中
curl -X POST "http://localhost:8001/api/papers/deselect_all"

# 2.1.2 嘗試發送查詢
# 在前端輸入查詢並發送
```

**預期結果:**
- 前端阻止查詢提交或顯示適當錯誤訊息
- 後端回傳明確的錯誤說明

#### 步驟 2.2: N8N 服務不可用的情況
```bash
# 2.2.1 模擬 N8N 服務故障
# （可選）暫時停止 N8N 容器或修改配置

# 2.2.2 發送查詢
# 在前端輸入查詢並發送
```

**預期結果:**
- 系統回傳錯誤訊息但不崩潰
- 降級處理機制啟動（如果有實作）

---

## 測試案例 TC-03: 不同查詢類型測試

### 測試目標
驗證系統對不同類型查詢的處理能力。

### 測試步驟

#### 步驟 3.1: 非定義類查詢
```bash
# 測試查詢
queries = [
    "What are the main findings of this research?",
    "How was the study conducted?", 
    "What are the limitations of this work?",
    "Compare the results across different papers."
]
```

**預期結果:**
- 系統能識別不同的 focus_type
- 相應地調用不同的內容提取策略
- 回傳結構化的分析結果

---

## 驗收標準檢查清單

根據 BACKLOG-FIX-03 的驗收標準，以下項目必須全部通過：

### ✅ AC-1: 整合測試存在且通過
- [ ] `test_unified_query_service_integration.py` 檔案存在
- [ ] 所有整合測試通過（success_rate = 100%）
- [ ] 測試覆蓋 `definitions` 處理流程的所有步驟

### ✅ AC-2: selected_content 資料結構符合設計
- [ ] 傳遞給 `unified_content_analysis` 的資料格式正確
- [ ] `definitions` content_type 包含必要欄位：
  - [ ] `text`: 定義句子內容
  - [ ] `type`: "OD" 或 "CD"
  - [ ] `page_num`: 頁碼
  - [ ] `id`: 唯一識別碼
- [ ] 資料結構與 `docs/user_query_flowchart.md` 中的範例一致

### ✅ AC-3: 手動端到端測試成功
- [ ] 成功上傳測試論文
- [ ] 論文選取功能正常運作
- [ ] 查詢 "What is the definition of adaptive expertise?" 成功執行
- [ ] 前端顯示包含 `[[ref:...]]` 引用標記的結果
- [ ] 引用來源可追溯且正確

---

## 測試執行記錄

### 測試執行資訊
- **執行日期**: ___________
- **執行者**: ___________
- **環境版本**: ___________
- **測試開始時間**: ___________
- **測試結束時間**: ___________

### 測試結果摘要

| 測試案例 | 狀態 | 備註 |
|---------|------|------|
| TC-01: 完整端到端流程 | ⬜ PASS / ❌ FAIL | |
| TC-02: 系統容錯性測試 | ⬜ PASS / ❌ FAIL | |
| TC-03: 不同查詢類型測試 | ⬜ PASS / ❌ FAIL | |

### 詳細問題記錄

如發現問題，請記錄：

1. **問題描述**: 
2. **重現步驟**:
3. **預期行為**:
4. **實際行為**:
5. **錯誤日誌**:
6. **影響範圍**:
7. **修復優先級**: 🔥 高 / 🟡 中 / 🟢 低

---

## 附錄

### A. 相關 API 端點

```bash
# 論文管理
GET    /api/papers                    # 獲取所有論文
GET    /api/papers/selected           # 獲取選中論文
POST   /api/papers/{id}/select        # 選中特定論文
POST   /api/papers/select_all         # 全選論文
POST   /api/papers/deselect_all       # 取消全選

# 查詢功能
POST   /api/unified-query             # 執行統一查詢
GET    /api/papers/sentences/all      # 獲取所有選中論文的句子

# 系統狀態
GET    /health                        # 健康檢查
```

### B. 調試命令

```bash
# 檢查容器狀態
docker-compose ps
docker logs backend --tail 50
docker logs frontend --tail 50

# 檢查 API 可用性
curl http://localhost:8001/health
curl http://localhost:8001/api/papers

# 檢查資料庫連接
docker exec -it postgres psql -U username -d database_name -c "\dt"
```

### C. 測試資料範例

```json
{
  "expected_selected_content_format": {
    "paper_name": "smith2023.pdf",
    "section_type": "introduction", 
    "content_type": "definitions",
    "content": [
      {
        "text": "Adaptive expertise is the ability to flexibly apply knowledge to novel situations.",
        "type": "CD",
        "page_num": 2,
        "id": "smith2023_introduction_2_5",
        "reason": "This provides a conceptual definition."
      }
    ]
  }
}
``` 