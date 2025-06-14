"""
調試 API 端點
用於測試和修復系統問題
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any

from ..core.database import get_db
from ..services.db_service import db_service
from ..services.processing_service import ProcessingService
from ..core.logging import get_logger

router = APIRouter(prefix="/debug", tags=["debug"])
logger = get_logger("debug_api")

@router.post("/reprocess-od-cd/{paper_id}")
async def reprocess_od_cd(
    paper_id: str,
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """重新處理論文的 OD/CD 檢測"""
    try:
        processing_service = ProcessingService()
        
        # 獲取論文的所有句子
        sentences_data = await db_service.get_sentences_for_paper(db, paper_id)
        
        if not sentences_data:
            raise HTTPException(status_code=404, detail=f"論文 {paper_id} 沒有找到句子資料")
        
        logger.info(f"開始重新處理論文 {paper_id} 的 OD/CD 檢測，句子數量: {len(sentences_data)}")
        
        # 執行 OD/CD 檢測（使用修復後的邏輯）
        od_cd_results = await processing_service._detect_od_cd(sentences_data, {})
        
        # 儲存結果到資料庫
        await db_service.save_od_cd_results(
            db,
            paper_id=paper_id,
            od_cd_results=od_cd_results,
            status="completed"
        )
        await db.commit()
        
        # 統計結果
        successful_count = sum(1 for r in od_cd_results if r.get("detection_status") == "success")
        od_count = sum(1 for r in od_cd_results if r.get("has_objective"))
        cd_count = sum(1 for r in od_cd_results if r.get("has_dataset") or r.get("has_contribution"))
        error_count = sum(1 for r in od_cd_results if r.get("detection_status") == "error")
        
        return {
            "success": True,
            "paper_id": paper_id,
            "total_sentences": len(od_cd_results),
            "successful_detections": successful_count,
            "error_detections": error_count,
            "od_sentences": od_count,
            "cd_sentences": cd_count,
            "message": f"重新處理完成，成功檢測 {successful_count}/{len(od_cd_results)} 個句子"
        }
        
    except Exception as e:
        logger.error(f"重新處理論文 {paper_id} 失敗: {e}", exc_info=True)
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"重新處理失敗: {str(e)}")

@router.get("/verify-od-cd/{paper_id}")
async def verify_od_cd(
    paper_id: str,
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """驗證論文的 OD/CD 檢測結果"""
    try:
        from sqlalchemy import text
        
        result = await db.execute(text("""
            SELECT 
                COUNT(*) as total_sentences,
                COUNT(CASE WHEN has_objective = true THEN 1 END) as has_objective_count,
                COUNT(CASE WHEN has_dataset = true THEN 1 END) as has_dataset_count,
                COUNT(CASE WHEN has_contribution = true THEN 1 END) as has_contribution_count,
                COUNT(CASE WHEN detection_status = 'success' THEN 1 END) as success_count,
                COUNT(CASE WHEN detection_status = 'error' THEN 1 END) as error_count
            FROM sentences 
            WHERE paper_id = :paper_id
        """), {"paper_id": paper_id})
        
        stats = result.fetchone()
        
        if stats[0] == 0:
            raise HTTPException(status_code=404, detail=f"論文 {paper_id} 沒有找到句子資料")
        
        return {
            "paper_id": paper_id,
            "total_sentences": stats[0],
            "has_objective": stats[1],
            "has_dataset": stats[2],
            "has_contribution": stats[3],
            "successful_detections": stats[4],
            "error_detections": stats[5],
            "od_cd_total": stats[1] + stats[2] + stats[3]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"驗證論文 {paper_id} 失敗: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"驗證失敗: {str(e)}") 