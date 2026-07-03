"""Anthropic API 래퍼.

두 종류의 호출만 노출한다:
- research(): Fable 5 + web_search 서버 도구 → 자유 텍스트 리서치 노트
- structured(): 임의 모델 + output_config(json_schema) → 스키마 보장 JSON

참고 스펙 (2026-07 기준):
- web search: tools=[{"type": "web_search_20250305", "name": "web_search", "max_uses": N}]
  사용량은 response.usage.server_tool_use.web_search_requests 로 확인. $10/1k searches.
  (최신 web_search_20260318 버전은 동적 필터링 지원 — v2에서 검토)
- 구조화 출력: output_config={"format": {"type": "json_schema", "schema": {...}}}
  GA 기능, 베타 헤더 불필요. Fable 5 / Haiku 4.5 지원.
  https://platform.claude.com/docs/en/build-with-claude/structured-outputs
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field

from anthropic import AsyncAnthropic

from app.config import settings

client = AsyncAnthropic(api_key=settings.anthropic_api_key)

WEB_SEARCH_TOOL = {
    "type": "web_search_20250305",
    "name": "web_search",
    "max_uses": settings.max_web_searches,
}


@dataclass
class LLMUsage:
    input_tokens: int = 0
    output_tokens: int = 0
    web_searches: int = 0

    def add(self, usage) -> None:
        self.input_tokens += getattr(usage, "input_tokens", 0) or 0
        self.output_tokens += getattr(usage, "output_tokens", 0) or 0
        stu = getattr(usage, "server_tool_use", None)
        if stu is not None:
            self.web_searches += getattr(stu, "web_search_requests", 0) or 0


@dataclass
class LLMResult:
    text: str
    usage: LLMUsage = field(default_factory=LLMUsage)


def _extract_text(message) -> str:
    """content 블록에서 text만 순서대로 이어붙인다 (web_search 결과 블록은 제외)."""
    parts = []
    for block in message.content:
        if getattr(block, "type", None) == "text":
            parts.append(block.text)
    return "".join(parts)


async def research(system: str, user: str) -> LLMResult:
    """Phase A: 웹 검색 동반 리서치. 자유 텍스트 노트 반환."""
    usage = LLMUsage()
    message = await client.messages.create(
        model=settings.report_model,
        max_tokens=4096,
        system=system,
        messages=[{"role": "user", "content": user}],
        tools=[WEB_SEARCH_TOOL],
    )
    usage.add(message.usage)
    # pause_turn: 서버 도구 장기 실행 시 턴이 일시정지될 수 있음 → 이어서 재요청
    turns = 0
    while message.stop_reason == "pause_turn" and turns < 3:
        turns += 1
        message = await client.messages.create(
            model=settings.report_model,
            max_tokens=4096,
            system=system,
            messages=[
                {"role": "user", "content": user},
                {"role": "assistant", "content": message.content},
            ],
            tools=[WEB_SEARCH_TOOL],
        )
        usage.add(message.usage)
    return LLMResult(text=_extract_text(message), usage=usage)


async def structured(model: str, system: str, user: str, schema: dict,
                     max_tokens: int = 16000) -> LLMResult:
    """Phase B / 논거 전처리·평가: JSON Schema 강제 출력.

    max_tokens 기본 16000: 종전 3000은 한국어 리포트 JSON에서 절단 실증
    (Unterminated string). Fable 5는 내부 추론이 max_tokens를 선소비하므로
    산출물 예상 크기의 1.5~2배 이상 여유 필수. 상한이라 미사용분 과금 없음.
    """
    usage = LLMUsage()
    kwargs = dict(
        model=model,
        max_tokens=max_tokens,
        system=system,
        messages=[{"role": "user", "content": user}],
    )
    output_config = {"format": {"type": "json_schema", "schema": schema}}
    try:
        message = await client.messages.create(**kwargs, output_config=output_config)
    except TypeError:
        # SDK가 output_config를 아직 모르는 구버전인 경우의 방어 — extra_body로 전달
        message = await client.messages.create(**kwargs, extra_body={"output_config": output_config})
    usage.add(message.usage)
    if message.stop_reason == "max_tokens":
        # 절단된 JSON은 하류에서 알 수 없는 파싱 에러로 표출 → 여기서 명확히 실패
        raise RuntimeError(
            f"structured() 출력이 max_tokens({max_tokens})에서 절단됨 — 상향 필요")
    return LLMResult(text=_extract_text(message), usage=usage)


def parse_json(text: str) -> dict:
    """구조화 출력은 스키마가 보장되지만, 방어적으로 코드펜스 제거 후 파싱."""
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        if cleaned.startswith("json"):
            cleaned = cleaned[4:]
    return json.loads(cleaned)
