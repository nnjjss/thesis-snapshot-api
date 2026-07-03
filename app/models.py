"""리포트 데이터 모델 — 단일 진실 소스.

이 Pydantic 모델에서:
1. FastAPI 응답 스키마
2. Claude 구조화 출력(output_config)용 JSON Schema
를 모두 파생시킨다. 스키마가 두 군데서 어긋나는 사고 방지.
"""
from __future__ import annotations

from datetime import date
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field

DISCLAIMER_KO = (
    "본 리포트는 정보 제공 목적으로 작성되었으며 투자 자문이 아닙니다. "
    "모든 투자 판단과 그 결과에 대한 책임은 투자자 본인에게 있습니다."
)


class Confidence(str, Enum):
    high = "high"
    medium = "medium"
    low = "low"


class Verdict(str, Enum):
    valid = "valid"                    # 데이터가 논거를 대체로 지지
    partially_valid = "partially_valid"  # 일부 지지, 일부 반박
    weakened = "weakened"              # 최근 데이터가 논거를 훼손
    insufficient_data = "insufficient_data"


class CaseItem(BaseModel):
    """강세/약세 논거 1건."""
    claim: str = Field(description="논거 요지 (한국어, 1~2문장)")
    evidence: str = Field(description="근거가 되는 구체적 사실/수치 (한국어, 출처 문장 기반)")
    source_url: str = Field(description="근거 출처 URL")
    confidence: Confidence = Field(description="근거의 확실성")


class SourceItem(BaseModel):
    title: str
    url: str


class BaseReport(BaseModel):
    """티커별 기본 리포트 — 캐시 대상."""
    ticker: str
    as_of: str = Field(description="기준일 YYYY-MM-DD")
    company_summary_ko: str = Field(description="회사/현황 3문장 요약 (한국어)")
    bull_case: list[CaseItem] = Field(
        min_length=2, max_length=4, description="강세 논거 2~4개"
    )
    bear_case: list[CaseItem] = Field(
        min_length=2, max_length=4, description="약세 논거 2~4개"
    )
    sources: list[SourceItem]


class ThesisEval(BaseModel):
    """사용자 논거 평가 — 캐시된 BaseReport 위에서 증분 생성."""
    thesis_restated: str = Field(description="사용자 논거를 중립적으로 재진술 (한국어)")
    supporting: list[int] = Field(description="지지하는 bull_case 인덱스 (0-base)")
    contradicting: list[int] = Field(description="반박하는 bear_case 인덱스 (0-base)")
    verdict: Verdict
    reasoning_ko: str = Field(description="판정 근거 3~5문장 (한국어)")
    watch_items_ko: list[str] = Field(
        description="논거 유지/기각을 가를 관찰 포인트 2~3개", max_length=3
    )


class ThesisStruct(BaseModel):
    """Haiku 전처리: 자연어 논거 → 구조화 (평가 품질 향상용)."""
    claims: list[str] = Field(description="핵심 주장들")
    assumptions: list[str] = Field(description="암묵적 가정들")
    horizon: str = Field(description="시계열 가정 (예: '6~12개월', '불명확')")


# ------------------------------------------------------------------
# API 요청/응답
# ------------------------------------------------------------------
class ReportRequest(BaseModel):
    ticker: str = Field(pattern=r"^[A-Za-z.\-]{1,10}$", examples=["NVDA"])
    thesis: Optional[str] = Field(
        default=None, max_length=2000,
        description="검증받고 싶은 투자 논거 (선택)",
        examples=["데이터센터 수요로 NVDA는 계속 상승한다"],
    )


class CostMeta(BaseModel):
    cache_hit: bool
    input_tokens: int = 0
    output_tokens: int = 0
    web_searches: int = 0


class ReportResponse(BaseModel):
    report: BaseReport
    thesis_eval: Optional[ThesisEval] = None
    disclaimer: str = DISCLAIMER_KO
    meta: CostMeta


def strict_schema(model: type[BaseModel]) -> dict:
    """Pydantic 모델 → Claude output_config용 JSON Schema.

    구조화 출력 grammar 제약에 맞춰 파생 스키마를 새니타이즈:
    - minItems/maxItems·minLength/maxLength 제거 — API 미지원(minItems는 0/1만 허용,
      실측 400: "minItems values other than 0 or 1 are not supported"). 공식 SDK의
      parse() 경로와 동일하게 전송 스키마에서만 제거하고, 검증은 Pydantic 파싱
      (클라이언트 측)에 남긴다. 개수 의도는 Field description으로 모델에 전달.
    - 모든 object 노드에 additionalProperties=false — 문서상 전 객체 필수
      ($defs 중첩 모델 포함. 종전엔 루트만 설정돼 있었음).
    문서상 스키마 복잡도 제한이 있으므로(중첩/유니온 과다 금지) 모델은 평평하게 유지할 것.
    """
    UNSUPPORTED = ("minItems", "maxItems", "minLength", "maxLength")

    def sanitize(node):
        if isinstance(node, dict):
            for k in UNSUPPORTED:
                node.pop(k, None)
            if node.get("type") == "object" or "properties" in node:
                node["additionalProperties"] = False
            for v in node.values():
                sanitize(v)
        elif isinstance(node, list):
            for v in node:
                sanitize(v)

    schema = model.model_json_schema()
    sanitize(schema)
    return schema
