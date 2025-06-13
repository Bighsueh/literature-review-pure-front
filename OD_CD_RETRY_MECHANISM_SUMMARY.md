# OD/CD 檢測重試機制改進總結

## 🎯 問題描述

原系統存在單個N8N API調用失敗會影響整個批次處理的問題，需要確保個別請求的失敗不會導致整個處理流程中斷。

## 🔧 解決方案

### 1. 修改 `_detect_od_cd` 方法（`backend/services/processing_service.py`）

#### 主要改進：
- **個別重試機制**：每個句子獨立重試最多3次
- **漸進式等待**：重試間隔遞增（1秒、2秒、3秒）
- **錯誤隔離**：單個句子失敗不影響其他句子的處理
- **詳細狀態追蹤**：記錄檢測狀態、重試次數、錯誤信息

#### 重試邏輯：
```python
async def detect_single_sentence_with_retry(idx: int, sentence_data: Dict[str, Any], max_retries: int = 3):
    for attempt in range(max_retries):
        try:
            result = await n8n_service.detect_od_cd(sentence, cache_key)
            if "error" not in result and "defining_type" in result:
                return success_result
        except Exception as e:
            if attempt < max_retries - 1:
                await asyncio.sleep(1 * (attempt + 1))  # 遞增等待
                continue
            else:
                return error_result
```

### 2. 資料庫結構更新

#### 新增欄位到 `paper_sentences` 表：
- `detection_status`: 檢測狀態（success、error、unknown）
- `error_message`: 錯誤信息（檢測失敗時記錄）
- `retry_count`: 重試次數
- `explanation`: 檢測結果的詳細解釋

#### 資料庫升級腳本：
- 檔案：`backend/database/upgrade_sentences_table.sql`
- 安全地為現有資料庫添加新欄位
- 自動遷移現有數據

### 3. 增強的錯誤處理

#### 處理結果分類：
```python
# 成功檢測
{
    "detection_status": "success",
    "od_cd_type": "CD",
    "confidence": 1.0,
    "explanation": "檢測為概念型定義",
    "retry_count": 0
}

# 檢測失敗
{
    "detection_status": "error", 
    "od_cd_type": "ERROR",
    "confidence": 0.0,
    "explanation": "API調用失敗，經過 3 次重試",
    "retry_count": 3,
    "error_message": "連接超時"
}
```

## 📊 效果評估

### 改進前：
- 單個API失敗導致整個批次中斷
- 缺乏錯誤追蹤和重試機制
- 難以診斷具體失敗原因

### 改進後：
- ✅ 個別失敗不影響批次處理
- ✅ 自動重試機制提高成功率
- ✅ 詳細的錯誤記錄便於診斷
- ✅ 漸進式等待避免API過載

## 🧪 測試驗證

創建了完整的測試套件（`backend/test_od_cd_retry_mechanism.py`）：

1. **成功處理測試**：驗證所有句子正常處理
2. **部分重試測試**：驗證失敗後重試成功的情況
3. **完全失敗測試**：驗證重試耗盡後的錯誤處理
4. **混合場景測試**：驗證複雜的成功/失敗組合

## 🚀 使用方式

### 運行資料庫升級：
```bash
# 在資料庫中執行升級腳本
sqlite3 your_database.db < backend/database/upgrade_sentences_table.sql
```

### 運行測試：
```bash
cd backend
python test_od_cd_retry_mechanism.py
```

## 📈 性能特點

- **併發控制**：使用 Semaphore 限制同時進行的API調用
- **智能重試**：只重試網路/服務錯誤，不重試業務邏輯錯誤
- **資源效率**：失敗的請求及時標記，避免無限重試
- **監控友好**：詳細的日誌記錄便於系統監控

## 💡 後續建議

1. **監控告警**：基於 `detection_status` 和 `retry_count` 建立告警機制
2. **效能分析**：定期分析重試率，優化API穩定性
3. **動態調整**：根據API回應時間動態調整重試間隔
4. **降級策略**：考慮添加本地備用檢測規則

## 結論

此次改進確保了OD/CD檢測系統的穩定性和可靠性，單個API調用失敗不再影響整個批次處理，同時提供了完善的錯誤追蹤和診斷能力。 