# 資料庫遷移系統使用說明

## 概述

本系統已建立完整的資料庫遷移管理機制，使用 Alembic 進行版本控制，確保資料庫結構與代碼同步。

## 自動遷移機制

系統啟動時會自動執行以下檢查和遷移：

1. **資料庫連接檢查**：確認資料庫可正常連接
2. **表格完整性檢查**：檢查所有必要表格是否存在
3. **欄位完整性檢查**：檢查關鍵欄位是否存在
4. **版本一致性檢查**：比對當前版本與最新版本
5. **自動遷移執行**：如發現問題則自動執行遷移

## 手動遷移工具

使用 `manage_migrations.py` 工具進行手動管理：

### 檢查狀態
```bash
cd backend
python manage_migrations.py status
```

### 執行遷移
```bash
python manage_migrations.py migrate
```

### 驗證資料庫結構
```bash
python manage_migrations.py validate
```

### 創建新遷移
```bash
python manage_migrations.py create
```

### 查看遷移歷史
```bash
python manage_migrations.py history
```

### 重置資料庫（危險操作）
```bash
python manage_migrations.py reset
```

## Alembic 原生命令

如需使用原生 Alembic 命令：

### 查看當前版本
```bash
cd backend
python -m alembic current
```

### 查看遷移歷史
```bash
python -m alembic history
```

### 創建新遷移
```bash
python -m alembic revision --autogenerate -m "描述"
```

### 升級到最新版本
```bash
python -m alembic upgrade head
```

### 降級到特定版本
```bash
python -m alembic downgrade <版本號>
```

## 檔案結構

```
backend/
├── alembic.ini                 # Alembic 設定檔
├── migrations/                 # 遷移腳本目錄
│   ├── env.py                 # 遷移環境設定
│   ├── script.py.mako         # 遷移腳本模板
│   └── versions/              # 版本腳本目錄
│       └── 6a67a812f326_complete_database_schema.py
├── core/
│   └── migration_manager.py   # 遷移管理器
└── manage_migrations.py       # 手動遷移工具
```

## 開發工作流程

### 1. 修改資料模型

當您修改 `models/paper.py` 中的資料模型時：

```python
# 例如：添加新欄位
class Paper(Base):
    # ... 現有欄位 ...
    new_field = Column(String, nullable=True)  # 新增欄位
```

### 2. 創建遷移腳本

```bash
cd backend
python manage_migrations.py create
# 輸入描述：Add new_field to papers table
```

### 3. 檢查生成的遷移腳本

檢查 `migrations/versions/` 目錄下新生成的腳本，確認遷移操作正確。

### 4. 執行遷移

```bash
python manage_migrations.py migrate
```

### 5. 驗證結果

```bash
python manage_migrations.py validate
```

## 系統啟動整合

遷移檢查已整合到主應用程式的啟動流程中（`main.py`）：

```python
# 執行自動遷移檢查和執行
from .core.migration_manager import ensure_database_schema
schema_ok = await ensure_database_schema()
```

## 故障排除

### 問題：遷移失敗

1. 檢查資料庫連接設定
2. 確認資料庫權限足夠
3. 查看詳細錯誤日誌
4. 檢查遷移腳本語法

### 問題：版本不一致

```bash
# 查看當前狀態
python manage_migrations.py status

# 強制更新到最新版本
python -m alembic stamp head
```

### 問題：自動遷移被跳過

檢查日誌中的詳細訊息，可能原因：
- 資料庫連接失敗
- 權限不足
- 遷移腳本錯誤

## 最佳實踐

1. **提交前測試**：每次修改資料模型後都要測試遷移
2. **版本控制**：遷移腳本應與代碼一起提交到版本控制
3. **備份資料**：在生產環境執行遷移前先備份資料庫
4. **漸進式遷移**：大型變更應分解為多個小的遷移步驟
5. **文檔化**：在遷移腳本中添加清晰的描述和註釋

## 安全注意事項

- 生產環境的遷移應在維護時段進行
- 重要操作前應先在測試環境驗證
- 避免直接修改已發布的遷移腳本
- 定期備份資料庫和遷移歷史 