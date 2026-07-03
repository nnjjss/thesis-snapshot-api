"""리포트 API 라우터."""
import anthropic
import asyncpg
from fastapi import APIRouter, Depends, HTTPException

from app.auth import resolve_user
from app.models import CostMeta, ReportRequest, ReportResponse
from app.services import report_service

router = APIRouter(prefix="/v1")


def _classify(e: Exception, stage: str) -> HTTPException:
    """Day 5: 에러 분류 — 원인별 정확한 상태코드(재시도 판단 근거를 클라이언트에)."""
    if isinstance(e, anthropic.RateLimitError):
        return HTTPException(status_code=429, detail=f"{stage}: 상류(LLM) 레이트리밋 — 잠시 후 재시도")
    if isinstance(e, anthropic.APIStatusError) and e.status_code >= 500:
        return HTTPException(status_code=503, detail=f"{stage}: 상류(LLM) 일시 장애 — 재시도 가능")
    if isinstance(e, anthropic.APIConnectionError):
        return HTTPException(status_code=503, detail=f"{stage}: 상류(LLM) 연결 실패 — 재시도 가능")
    if isinstance(e, asyncpg.PostgresError):
        return HTTPException(status_code=503, detail=f"{stage}: DB 오류 — 재시도 가능")
    return HTTPException(status_code=502, detail=f"{stage}: {e}")


@router.post("/reports", response_model=ReportResponse)
async def create_report(req: ReportRequest, user=Depends(resolve_user)) -> ReportResponse:
    try:
        report, notes, base_id, meta = await report_service.get_or_create_base_report(
            req.ticker, user=user)
    except HTTPException:
        raise  # 401/429(쿼터) 등 의도된 상태코드는 그대로 통과 (502로 뭉개지 않음)
    except Exception as e:
        raise _classify(e, "report generation")

    thesis_eval = None
    if req.thesis and req.thesis.strip():
        try:
            thesis_eval, eval_meta = await report_service.evaluate_thesis(
                report, notes, base_id, req.thesis.strip(), user=user
            )
            meta = CostMeta(
                cache_hit=meta.cache_hit,
                input_tokens=meta.input_tokens + eval_meta.input_tokens,
                output_tokens=meta.output_tokens + eval_meta.output_tokens,
                web_searches=meta.web_searches,
            )
        except HTTPException:
            raise
        except Exception as e:
            raise _classify(e, "thesis evaluation")

    return ReportResponse(report=report, thesis_eval=thesis_eval, meta=meta)
