# Backlog: DB-01 - 建立使用者與工作區核心表格

- **Epic:** 會員系統與多工作區功能導入
- **狀態:** To Do
- **優先級:** Highest
- **估算 (Story Points):** 3

---

### 使用者故事 (User Story)

**身為** 一位系統架構師，
**我想要** 建立專門的 `users` 和 `workspaces` 資料庫表格，
**以便** 為實現個人化的多租戶（multi-tenant）應用程式打下堅實的基礎。

---

### 驗收標準 (Acceptance Criteria)

1.  **`users` 資料表已成功建立：**
    -   [ ] 包含 `id` (PK), `google_id` (UNIQUE), `email` (UNIQUE), `name`, `picture_url`, `created_at`, `updated_at` 欄位。
    -   [ ] 欄位資料類型與約束符合設計規格。

2.  **`workspaces` 資料表已成功建立：**
    -   [ ] 包含 `id` (PK), `user_id` (FK), `name`, `created_at`, `updated_at` 欄位。
    -   [ ] 欄位資料類型與約束符合設計規格。

3.  **關聯已正確設定：**
    -   [ ] `workspaces.user_id` 欄位有外鍵 (Foreign Key) 約束，指向 `users.id`。
    -   [ ] 此外鍵設定了 `ON DELETE CASCADE`，確保當使用者被刪除時，其擁有的所有工作區也會被一併刪除。

4.  **後端模型已建立：**
    -   [ ] 在 `backend/models/` 路徑下，已建立對應的 SQLAlchemy 模型 `User` 和 `Workspace`。
    -   [ ] 模型定義與資料庫表格結構完全一致。

---

### 技術筆記 (Technical Notes)

-   此任務是後續所有資料庫隔離工作的先決條件。
-   `google_id` 應被視為使用者身份的主要外部識別碼。
-   Alembic 遷移腳本需要正確處理這兩張新表的建立順序。 