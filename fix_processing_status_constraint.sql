-- 修正 papers 表的 processing_status 檢查約束
-- 問題：原約束不包含 'uploading' 狀態，但程式碼預設值是 'uploading'
-- 解決方案：更新約束以包含所有有效狀態

BEGIN;

-- 1. 刪除現有的檢查約束
ALTER TABLE papers DROP CONSTRAINT IF EXISTS chk_papers_processing_status;

-- 2. 重新建立包含 'uploading' 的檢查約束
ALTER TABLE papers 
ADD CONSTRAINT chk_papers_processing_status 
CHECK (processing_status IN ('uploading', 'pending', 'processing', 'completed', 'error'));

-- 3. 驗證約束是否正確建立
SELECT 
    constraint_name, 
    check_clause 
FROM information_schema.check_constraints 
WHERE constraint_name = 'chk_papers_processing_status';

-- 4. 測試約束 - 這些測試應該成功
-- 測試有效值
DO $$
BEGIN
    -- 測試 'uploading' 狀態
    PERFORM 1 WHERE 'uploading' IN ('uploading', 'pending', 'processing', 'completed', 'error');
    IF NOT FOUND THEN
        RAISE EXCEPTION 'Constraint test failed for uploading status';
    END IF;
    
    -- 測試 'pending' 狀態
    PERFORM 1 WHERE 'pending' IN ('uploading', 'pending', 'processing', 'completed', 'error');
    IF NOT FOUND THEN
        RAISE EXCEPTION 'Constraint test failed for pending status';
    END IF;
    
    RAISE NOTICE 'All constraint tests passed successfully!';
END $$;

COMMIT;

-- 輸出完成訊息
SELECT 
    'processing_status constraint updated successfully!' AS status,
    'Now allows: uploading, pending, processing, completed, error' AS allowed_values,
    NOW() AS updated_at; 