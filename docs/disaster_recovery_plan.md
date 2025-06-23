# 資料庫災難恢復計畫

## 概述

本文件描述論文分析系統的完整資料庫災難恢復程序，包含備份策略、回滾機制和緊急恢復流程。

## 🎯 恢復目標

- **RTO (恢復時間目標)**: 15 分鐘內恢復服務
- **RPO (恢復點目標)**: 最多損失 5 分鐘的資料
- **可用性目標**: 99.5% (每月停機時間 < 4 小時)

## 📋 災難情境分類

### 1. 輕微故障 (Level 1)
- **情境**: 單一表格損壞、部分資料不一致
- **影響**: 特定功能受影響，系統仍可運行
- **恢復時間**: < 5 分鐘
- **處理方式**: 部分資料修復、索引重建

### 2. 中度故障 (Level 2)  
- **情境**: 多個表格損壞、遷移失敗
- **影響**: 系統功能大幅受限
- **恢復時間**: < 15 分鐘
- **處理方式**: 回滾遷移、從最近備份恢復

### 3. 重大故障 (Level 3)
- **情境**: 完整資料庫損壞、容器無法啟動
- **影響**: 系統完全無法使用
- **恢復時間**: < 30 分鐘
- **處理方式**: 緊急恢復程序、從備份重建

## 🔄 備份策略

### 自動備份
```bash
# 每日自動備份 (透過 crontab)
0 2 * * * /path/to/scripts/backup/docker_backup.sh

# 每週完整備份
0 1 * * 0 /path/to/scripts/backup/docker_backup.sh --full
```

### 備份保留政策
- **每日備份**: 保留 7 天
- **每週備份**: 保留 4 週  
- **每月備份**: 保留 12 個月
- **年度備份**: 保留 3 年

### 備份驗證
```bash
# 每日驗證備份完整性
/path/to/scripts/backup/verify_backup.sh --latest
```

## ⚡ 緊急恢復程序

### Step 1: 故障評估
```bash
# 檢查系統狀態
docker ps
docker logs paper_analysis_db
docker logs paper_analysis_backend

# 檢查資料庫連線
docker exec paper_analysis_db pg_isready -U postgres
```

### Step 2: 確定故障級別
```bash
# 檢查關鍵表格
docker exec paper_analysis_db psql -U postgres -d paper_analysis -c "\dt"

# 檢查資料完整性
docker exec paper_analysis_db psql -U postgres -d paper_analysis -c "
SELECT tablename, n_live_tup as row_count 
FROM pg_stat_user_tables 
ORDER BY tablename;"
```

### Step 3: 執行相應恢復程序

#### Level 1 - 輕微故障
```bash
# 重啟服務
docker-compose restart

# 檢查並修復索引
docker exec paper_analysis_db psql -U postgres -d paper_analysis -c "REINDEX DATABASE paper_analysis;"
```

#### Level 2 - 中度故障  
```bash
# 回滾 Alembic 遷移
docker exec paper_analysis_backend bash -c "cd /app/backend && alembic downgrade -1"

# 如果回滾失敗，從最近備份恢復
./scripts/backup/docker_restore.sh --latest
```

#### Level 3 - 重大故障
```bash
# 緊急恢復模式
./scripts/backup/docker_restore.sh --emergency
```

## 🔍 遷移回滾程序

### 自動回滾
```bash
# 檢查當前遷移版本
docker exec paper_analysis_backend bash -c "cd /app/backend && alembic current"

# 回滾到上一版本
docker exec paper_analysis_backend bash -c "cd /app/backend && alembic downgrade -1"

# 回滾到特定版本
docker exec paper_analysis_backend bash -c "cd /app/backend && alembic downgrade <revision_id>"
```

### 手動回滾
如果自動回滾失敗：
```bash
# 1. 停止應用服務
docker-compose stop backend

# 2. 手動執行回滾 SQL
docker exec -i paper_analysis_db psql -U postgres -d paper_analysis < rollback_scripts/manual_rollback.sql

# 3. 重啟服務
docker-compose start backend
```

## 📞 緊急聯絡清單

### 技術團隊
- **系統架構師**: [聯絡資訊]
- **DevOps 工程師**: [聯絡資訊]  
- **資料庫管理員**: [聯絡資訊]

### 權責分工
- **系統架構師**: 技術決策、恢復策略制定
- **DevOps 工程師**: 執行恢復操作、監控系統狀態
- **資料庫管理員**: 資料完整性驗證、效能優化

## 📊 監控與告警

### 關鍵指標監控
```bash
# 資料庫連線數
docker exec paper_analysis_db psql -U postgres -d paper_analysis -c "
SELECT count(*) as active_connections 
FROM pg_stat_activity 
WHERE state = 'active';"

# 表格大小監控
docker exec paper_analysis_db psql -U postgres -d paper_analysis -c "
SELECT 
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size
FROM pg_tables 
WHERE schemaname='public' 
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;"
```

### 自動告警
- 連線數 > 80%: WARNING
- 連線數 > 95%: CRITICAL
- 磁碟使用率 > 85%: WARNING
- 磁碟使用率 > 95%: CRITICAL

## 🧪 恢復測試

### 定期測試計畫
- **每月**: 執行完整恢復測試
- **每季**: 災難恢復演練
- **每年**: 跨環境恢復測試

### 測試腳本
```bash
# 自動化恢復測試
./scripts/test/migration_test.sh

# 備份恢復測試
./scripts/test/backup_restore_test.sh
```

## 📝 事後檢討程序

### 故障報告
每次故障後需產生報告，包含：
1. 故障發生時間與持續時間
2. 根本原因分析
3. 恢復步驟記錄
4. 改進建議

### 檔案更新
根據事後檢討結果：
1. 更新恢復程序
2. 改進監控指標
3. 優化備份策略
4. 更新團隊培訓

## 🔧 維護檢查清單

### 每日檢查
- [ ] 備份成功執行
- [ ] 系統監控正常
- [ ] 磁碟空間充足
- [ ] 服務健康檢查通過

### 每週檢查  
- [ ] 備份檔案完整性驗證
- [ ] 效能指標檢查
- [ ] 日誌檔案輪替
- [ ] 安全更新檢查

### 每月檢查
- [ ] 執行完整恢復測試
- [ ] 檢查恢復程序文件
- [ ] 更新緊急聯絡資訊
- [ ] 審核存取權限

---

**重要提醒**: 
- 所有恢復操作都應在測試環境先行驗證
- 重大變更前必須執行完整備份
- 緊急情況下優先保證資料安全，再考慮服務恢復
- 定期檢討並更新此文件，確保程序的有效性 