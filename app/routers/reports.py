"""리포트 API 라우터."""
from fastapi import APIRouter, HTTPException

from app.models import CostMeta, ReportRequest, ReportResponse
from app.services import report_service

router = APIRouter(prefix="/v1")


@router.post("/reports", response_model=ReportResponse)
async def create_report(req: ReportRequest) -> ReportResponse:
    try:
        report, notes, base_id, meta = await report_service.get_or_create_base_report(req.ticker)
    except Exception as e:  # Day 1: 단순 매핑, Day 5에 에러 분류 정교화
        raise HTTPException(status_code=502, detail=f"report generation failed: {e}")

    thesis_eval = None
    if req.thesis and req.thesis.strip():
        try:
            thesis_eval, eval_meta = await report_service.evaluate_thesis(
                report, notes, base_id, req.thesis.strip()
            )
            meta = CostMeta(
                cache_hit=meta.cache_hit,
                input_tokens=meta.input_tokens + eval_meta.input_tokens,
                output_tokens=meta.output_tokens + eval_meta.output_tokens,
                web_searches=meta.web_searches,
            )
        except Exception as e:
            raise HTTPException(status_code=502, detail=f"thesis evaluation failed: {e}")

    return ReportResponse(report=report, thesis_eval=thesis_eval, meta=meta)
