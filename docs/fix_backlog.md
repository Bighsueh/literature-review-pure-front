# 系統修正計畫：使用者查詢流程重構

此修正計劃已經執行完成，留存於此作為修正過後的紀錄參照。
**文件作者：** Gemini (AI Software Engineering Manager)
**日期：** 2024-07-26
**狀態：** 規劃中

---

## 1. 總覽與背景 (Overview & Context)

經深入分析，當前的「使用者查詢流程」實作與 `docs/user_query_flowchart.md` 中的設計存在嚴重偏差。核心問題在於功能開發不完整、前後端脫鉤，以及關鍵資料流中斷，導致整個查詢功能處於不可用的「半成品」狀態。

本文件旨在定義一個清晰、分階段的修復計畫，將系統功能拉回正軌，使其符合原始設計目標：一個由 AI 驅動、高效、精準且可追溯的論文分析工具。

## 2. 整體目標 (Overall Goal)

**我們的目標是：** 交付一個完整、可靠且符合設計規範的使用者查詢功能。

這意味著使用者應該能夠：
1.  在前端介面自由**選取**一篇或多篇論文。
2.  輸入一個自然語言**查詢**。
3.  系統能夠**智能地**理解查詢意圖，並**精準地**從選定的論文中提取相關內容（特別是針對「定義」類查詢）。
4.  最終在前端看到一個**有意義、附帶引用來源**的分析結果。

## 3. 開發待辦清單 (Backlogs)

我們將修復工作拆分為三個獨立但有依賴順序的 Backlog，遵循「**前端 -> 後端 -> 整合**」的策略。

---

### **BACKLOG-FIX-01: [前端] 論文選取功能實作**

- **問題陳述:** 使用者在前端沒有任何介面可以選取要查詢的論文，而後端 `/unified-query` API 又強制要求必須有論文被選取，導致查詢功能從一開始就被阻斷。
- **此 Backlog 的目標:** 建立一個穩定、直觀的論文選取機制，並確保使用者的選擇能夠正確地同步到後端。這是整個修復計畫的**最高優先級**任務。
- **驗收標準 (Acceptance Criteria):**
    - [ ] 論文列表中的每篇論文前都有一個可點擊的複選框。
    - [ ] 介面上有「全選」和「取消全選」的功能。
    - [ ] 當使用者勾選/取消勾選論文時，後端資料庫中對應論文的 `is_selected` 狀態會被即時、正確地更新。
    - [ ] 在發起查詢前，前端會確保至少有一篇論文被選中。
- **開發任務 (Tasks):**
    - [ ] **UI 組件:** 在前端論文列表組件 (`PaperList.vue` 或類似檔案) 中，為每個項目增加 Checkbox。
    - [ ] **狀態管理:** 使用前端狀態管理器 (如 Pinia/Vuex) 來維護一個 `selectedPaperIds` 的列表。
    *   [ ] **API 整合:**
        *   當勾選/取消勾選時，觸發對後端 `POST /papers/{paper_id}/select` API 的呼叫。
        *   「全選/取消全選」按鈕應呼叫後端的 `POST /papers/select_all` 和 `POST /papers/deselect_all` API。
    - [ ] **使用者體驗優化:** 在「發送查詢」按鈕的邏輯中加入檢查，若沒有選中任何論文，則禁用按鈕或顯示提示訊息。
- **依賴關係:** 無。此為起始任務。

---

### **BACKLOG-FIX-02: [後端] 重建核心查詢與內容提取邏輯**

- **問題陳述:** 後端 `UnifiedQueryProcessor` 的實作完全偏離設計。內容提取方法 `_extract_content_from_summary` 是一個返回無效假資料的佔位符，且完全沒有針對 `definitions` 類型的特殊處理邏輯，破壞了整個分析流程。
- **此 Backlog 的目標:** 徹底移除無效的佔位邏輯，並根據設計文件 `user_query_flowchart.md` 完整地、正確地實作內容提取的業務邏輯。
- **驗收標準 (Acceptance Criteria):**
    - [ ] `_extract_content_from_summary` 方法已被完全刪除。
    - [ ] `UnifiedQueryProcessor` 中存在一個新的 `_extract_content` 方法，其內部有基於 `focus_type` 的條件分支。
    - [ ] 當 `focus_type` 為 `definitions` 時，系統會：
        1.  成功呼叫 `n8n_service.query_keyword_extraction`。
        2.  根據 `section` 資訊從資料庫中撈取所有相關的 `Sentence` 物件。
        3.  在後端成功過濾出匹配關鍵字且 `defining_type` 為 'OD' 或 'CD' 的句子。
        4.  組裝出符合 `unified_content_analysis` API 輸入格式的 `selected_content` 結構。
- **開發任務 (Tasks):**
    - [ ] **程式碼清理:** 刪除 `UnifiedQueryProcessor` 中的 `_extract_content_from_summary` 方法。
    - [ ] **結構重構:** 建立 `_extract_content` 方法，並在 `process_query` 中呼叫它。
    - [ ] **`definitions` 處理器開發:**
        - 在 `_extract_content` 中增加 `if section['focus_type'] == 'definitions':` 的邏輯分支。
        - 實作對 `n8n_service.query_keyword_extraction` 的呼叫。
        - 實作對 `db_service.get_sentences_by_section` 的呼叫。
        - 撰寫 Python 版本的 `findMatchingSentences` 和 `filterDefinitionSentences` 邏輯。
        - 根據設計文件，將處理完的句子格式化為 `definitions` content_type。
    - [ ] **一般處理器開發:**
        - 在 `_extract_content` 中為 `key_sentences` 和 `full_section` 建立初步的處理框架（即使只是拋出 `NotImplementedError` 也比假資料好）。
- **依賴關係:** `BACKLOG-FIX-01`。需要前端能夠正確設定 `is_selected` 狀態，以便後端 `get_selected_papers` 能取得正確的論文列表。

---

### **BACKLOG-FIX-03: [整合測試] 端到端流程驗證**

- **問題陳述:** 前後端各自修復後，需要確保它們能無縫協作，並且整個資料流從使用者輸入到最終分析結果的呈現是暢通且正確的。
- **此 Backlog 的目標:** 驗證整個使用者查詢流程的功能完整性與正確性，確保最終交付的產品穩定可靠。
- **驗收標準 (Acceptance Criteria):**
    - [ ] 存在一個針對 `UnifiedQueryProcessor` 的整合測試，該測試能驗證 `definitions` 處理流程的正確輸出。
    - [ ] 針對 `definitions` 查詢，傳遞給 `unified_content_analysis` N8N 節點的 `selected_content` 資料結構，與設計文件中的範例完全相符。
    - [ ] **手動端到端測試成功：**
        1.  上傳 `docs/test.pdf`。
        2.  在前端勾選該論文。
        3.  輸入查詢 "What is the definition of adaptive expertise?"。
        4.  前端成功渲染出包含引用標記 `[[ref:...]]` 的分析結果。
- **開發任務 (Tasks):**
    - [ ] **撰寫整合測試:** 建立 `test_unified_query_service_integration.py`，使用測試資料庫和 Mock 的 N8N 回應，驗證 `process_query` 的完整流程。
    - [ ] **手動測試案例編寫:** 在團隊內部文件中，詳細記錄端到端測試的步驟、輸入資料和預期輸出。
    - [ ] **執行與除錯:** 執行手動測試，記錄所有遇到的問題，並協調前後端開發人員進行修復，直到測試案例能穩定通過。
- **依賴關係:** `BACKLOG-FIX-02`。必須在後端邏輯重建完成後才能進行有效的整合測試。 