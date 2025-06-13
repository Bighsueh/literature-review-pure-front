-- 升級 sentences 表，添加錯誤處理相關欄位
-- 這個腳本可以安全地在現有PostgreSQL資料庫上執行

-- 添加 detection_status 欄位（PostgreSQL語法）
ALTER TABLE sentences ADD COLUMN IF NOT EXISTS detection_status VARCHAR(20) DEFAULT 'unknown';

-- 添加 error_message 欄位
ALTER TABLE sentences ADD COLUMN IF NOT EXISTS error_message TEXT;

-- 添加 retry_count 欄位
ALTER TABLE sentences ADD COLUMN IF NOT EXISTS retry_count INTEGER DEFAULT 0;

-- 添加 explanation 欄位
ALTER TABLE sentences ADD COLUMN IF NOT EXISTS explanation TEXT;

-- 創建新的索引（PostgreSQL語法）
CREATE INDEX IF NOT EXISTS idx_sentences_detection_status ON sentences(detection_status);
CREATE INDEX IF NOT EXISTS idx_sentences_retry_count ON sentences(retry_count);

-- 更新現有記錄，將已有的成功記錄標記為 'success'
UPDATE sentences 
SET detection_status = 'success' 
WHERE defining_type IS NOT NULL AND defining_type != '' AND defining_type != 'UNKNOWN';

-- 將explanation設置為現有的analysis_reason（如果存在的話）
UPDATE sentences 
SET explanation = COALESCE(
    CASE 
        WHEN defining_type = 'OD' THEN '檢測為操作型定義'
        WHEN defining_type = 'CD' THEN '檢測為概念型定義'  
        WHEN defining_type = 'OTHER' THEN '檢測為其他類型句子'
        ELSE '檢測完成'
    END, 
    '檢測完成'
)
WHERE detection_status = 'success'; 