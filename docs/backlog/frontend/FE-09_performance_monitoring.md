# Backlog: FE-09 - 效能監控與優化

- **Epic:** 前端 UX 重構  
- **狀態:** To Do
- **優先級:** Medium
- **估算 (Story Points):** 3

---

### 技術故事 (Technical Story)

**身為** 一位負責前端效能的開發者，
**我想要** 建立完整的效能監控體系，追蹤 Core Web Vitals、Bundle 大小和使用者互動指標，
**以便** 及時發現效能瓶頸，確保應用在各種設備和網路環境下都能提供良好的使用者體驗。

---

### 驗收標準 (Acceptance Criteria)

1.  **Core Web Vitals 監控：**
    -   [ ] 整合 `web-vitals` 函式庫，追蹤 LCP、FID、CLS 等關鍵指標。
    -   [ ] 將效能資料發送到分析平台 (如 Google Analytics 或自建端點)。
    -   [ ] 在開發環境中提供效能警告，當指標超出閾值時顯示通知。

2.  **Bundle 分析與優化：**
    -   [ ] 使用 `webpack-bundle-analyzer` 或 `rollup-plugin-visualizer` 分析 bundle 大小。
    -   [ ] 設定 bundle 大小閾值，CI 中超出限制時會發出警告。
    -   [ ] 實現程式碼分割：按路由和工作區動態載入相關模組。

3.  **使用者行為分析：**
    -   [ ] 追蹤關鍵使用者操作：登入、工作區切換、檔案上傳、查詢次數。
    -   [ ] 記錄錯誤發生率和使用者流失點。
    -   [ ] 分析最常使用的功能，為 UX 優化提供數據支援。

4.  **效能優化實施：**
    -   [ ] 實現關鍵資源的預載入 (preload) 和預取 (prefetch)。
    -   [ ] 優化圖片和靜態資源：使用 WebP 格式、適當的壓縮等級。
    -   [ ] 實現 Service Worker 快取策略，提升重複訪問速度。

---

### 技術筆記 (Technical Notes)

-   **新增檔案**: `utils/performance.ts`, `utils/analytics.ts`, `public/sw.js`
-   **主要修改檔案**: `vite.config.ts` (bundle 分析), `main.tsx` (效能監控初始化)
-   可考慮使用 `@sentry/react` 進行錯誤追蹤和效能監控
-   Service Worker 策略建議使用 `workbox` 函式庫
-   此任務與使用者功能無直接關聯，但對整體體驗品質至關重要 