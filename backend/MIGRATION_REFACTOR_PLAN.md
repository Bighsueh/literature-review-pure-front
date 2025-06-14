# 資料庫遷移系統重構計劃

## 🎯 目標
將複雜的多重遷移系統簡化為單一的 Alembic 系統，確保與 ORM 模型完全一致，提高可靠性和可維護性。

## ❌ 現有問題

### 1. 多重遷移系統導致的問題
- **5種不同的遷移方式**造成維護複雜性
- **欄位名稱不一致**：`sentences` 表在不同地方使用 `content` 或 `sentence_text`
- **Schema 不同步**：手動SQL與ORM模型不匹配
- **Debug困難**：不確定哪個遷移系統生效

### 2. 欄位名稱衝突詳情
```sql
-- ORM 模型使用：
content TEXT NOT NULL

-- 舊 schema.sql 使用：
sentence_text TEXT NOT NULL

-- 這導致代碼中需要別名處理，增加複雜性
```

## ✅ 解決方案：單一 Alembic 系統

### 1. 系統設計
- **只保留 Alembic** 作為唯一遷移系統
- **基於 ORM 模型**自動生成遷移
- **統一欄位命名**：以 ORM 模型為準
- **自動化檢查**：啟動時自動執行遷移

### 2. 實施步驟

#### 步驟 1：清理舊系統
```bash
# 備份現有資料庫
pg_dump paper_analysis > backup_$(date +%Y%m%d_%H%M%S).sql

# 移除舊的遷移文件（保留作為參考）
mkdir -p backup/old_migrations
mv backend/database/migration_manager.py backup/old_migrations/
mv backend/database/migrations/ backup/old_migrations/
```

#### 步驟 2：生成新的初始遷移
```bash
cd backend

# 使用新的簡化系統
python create_initial_migration.py

# 檢查生成的遷移文件
ls migrations/versions/
```

#### 步驟 3：更新主程式
```python
# 在 main.py 中替換
from simplified_migration import ensure_database_schema

# 在啟動時調用
schema_ok = await ensure_database_schema()
```

#### 步驟 4：測試和驗證
```bash
# 檢查遷移狀態
python simplified_migration.py status

# 執行遷移（如果需要）
python simplified_migration.py migrate

# 檢查資料庫結構是否與ORM一致
python -c "
from models.paper import Base
from sqlalchemy import create_engine
engine = create_engine('postgresql://...')
Base.metadata.create_all(engine, checkfirst=True)
print('Schema validation passed')
"
```

## 📁 新的文件結構

```
backend/
├── simplified_migration.py       # 新的簡化遷移管理器
├── create_initial_migration.py   # 初始遷移生成工具
├── alembic.ini                   # Alembic 設定（保持不變）
├── migrations/                   # Alembic 遷移目錄（保持不變）
│   ├── env.py
│   ├── script.py.mako
│   └── versions/
│       └── [新的初始遷移].py
├── models/
│   └── paper.py                  # ORM模型（作為真實來源）
└── backup/
    └── old_migrations/           # 舊系統備份
```

## 🔧 使用方式

### 日常開發流程
```bash
# 1. 修改 ORM 模型
vim backend/models/paper.py

# 2. 生成遷移
python simplified_migration.py create -m "Add new field to papers"

# 3. 檢查生成的遷移
vim migrations/versions/[最新遷移].py

# 4. 執行遷移
python simplified_migration.py migrate

# 5. 驗證結果
python simplified_migration.py status
```

### 啟動時自動遷移
```python
# 在 main.py 中
from simplified_migration import ensure_database_schema

@app.on_event("startup")
async def startup_event():
    schema_ok = await ensure_database_schema()
    if not schema_ok:
        logger.error("資料庫結構檢查失敗")
        # 可以選擇是否要停止啟動
```

## 🛡️ 安全措施

### 1. 備份策略
```bash
# 重構前必須備份
pg_dump paper_analysis > pre_refactor_backup.sql

# 測試環境先行
# 在測試環境完整測試後才部署到生產環境
```

### 2. 回滾計劃
```bash
# 如果重構失敗，可以快速回滾
psql paper_analysis < pre_refactor_backup.sql

# 然後恢復舊的系統文件
```

### 3. 驗證檢查
```python
# 重構後驗證數據完整性
async def validate_data_integrity():
    # 檢查表格數量
    # 檢查重要欄位
    # 檢查資料一致性
    pass
```

## 📊 預期效果

### 1. 複雜度降低
- **從5個系統 → 1個系統**
- **移除欄位名稱別名處理**
- **統一的遷移流程**

### 2. 可靠性提升
- **基於ORM模型**確保一致性
- **自動化檢查**減少人為錯誤
- **標準化流程**便於維護

### 3. 開發效率
- **清晰的工作流程**
- **更少的debug時間**
- **更好的代碼可讀性**

## ⚠️ 注意事項

1. **重構前務必備份資料庫**
2. **在測試環境充分測試**
3. **確認所有服務都停止後再重構**
4. **重構後完整測試所有功能**

## 🚀 執行時間表

1. **準備階段**（1天）
   - 備份現有系統
   - 建立測試環境

2. **實施階段**（2天）
   - 執行重構步驟
   - 測試和驗證

3. **部署階段**（1天）
   - 生產環境部署
   - 監控和驗證

總計：約4個工作天 