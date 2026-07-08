"""리포트 생성 파이프라인.

get_or_create_base_report:
    캐시 히트  → DB의 JSON 그대로 반환 (한계비용 ≈ 0)
    캐시 미스  → Phase A(리서치, web search) → Phase B(구조화) → 캐시 저장

evaluate_thesis:
    Haiku 전처리(논거 구조화) → Fable 5 평가 (캐시된 리포트+노트를 컨텍스트로)
"""
from __future__ import annotations

import json
from datetime import date

from app import auth, db, quality
from app.config import settings
from app.llm import client as llm
from app.llm import prompts
from app.models import (REPORT_SCHEMA_VERSION, BaseReport, CostMeta,
                        ThesisEval, ThesisStruct, strict_schema)


async def get_or_create_base_report(ticker: str, user=None) -> tuple[BaseReport, str, object, CostMeta]:
    """returns (report, eval_context_notes, base_report_id, meta)

    두 번째 반환값은 '논거 평가용 컨텍스트' — Day 2부터 Haiku 압축본이 있으면
    압축본(평가 1회당 절감 > 압축 1회 비용, 손익분기 0.8회 실측), 없으면 원본.
    user(Day 4): 쿼터는 캐시 미스(유료 호출) 직전에만 검사 — 캐시 히트는 무제한 정책.
    """
    ticker = ticker.strip().upper()
    user_id = user["id"] if user else None

    cached = await db.get_cached_base_report(ticker, REPORT_SCHEMA_VERSION)
    if cached:
        report = BaseReport.model_validate_json(cached["report"])
        meta = CostMeta(cache_hit=True)
        await db.record_usage(ticker, "base_report", True, 0, 0, 0, user_id=user_id)
        notes = cached["research_notes_compressed"] or cached["research_notes"] or ""
        return report, notes, cached["id"], meta

    await auth.enforce_quota(user)  # 유료 경로 진입 직전 (free 24h 상한, 초과 시 429)

    # --- Phase A: 리서치 (Fable 5 + web search) ---
    research = await llm.research(
        system=prompts.RESEARCH_SYSTEM.format(today=date.today().isoformat()),
        user=prompts.research_user_prompt(ticker),
    )

    # --- Phase B: 구조화 (JSON Schema 강제) — structure_model(Sonnet, 비용 레버 2026-07-08) ---
    structured = await llm.structured(
        model=settings.structure_model,
        system=prompts.STRUCTURE_SYSTEM,
        user=prompts.structure_user_prompt(ticker, research.text),
        schema=strict_schema(BaseReport),
    )
    report = BaseReport.model_validate(llm.parse_json(structured.text))

    # --- Day 2: 노트 압축 (Haiku, fail-open — 실패해도 리포트 생성은 진행) ---
    compressed_text = None
    try:
        comp = await llm.compress(prompts.COMPRESS_SYSTEM, research.text)
        # prep_model(Haiku) 호출이라 Fable 단가인 base_report와 섞지 않고 별도 kind로 기록
        await db.record_usage(ticker, "compress", False,
                              comp.usage.input_tokens, comp.usage.output_tokens, 0)
        # 효과 가드: Haiku가 비결정적으로 압축에 실패(재포맷으로 오히려 팽창)하는
        # 케이스 실측(3,730→3,740자) — 원본의 90% 미만으로 줄었을 때만 채택
        if len(comp.text) < 0.9 * len(research.text):
            compressed_text = comp.text
    except Exception:
        pass  # 압축은 최적화일 뿐 — 평가는 원본 노트로 fail-open

    total_in = research.usage.input_tokens + structured.usage.input_tokens
    total_out = research.usage.output_tokens + structured.usage.output_tokens
    searches = research.usage.web_searches

    base_report_id = await db.insert_base_report(
        ticker=ticker, as_of=report.as_of, report=report.model_dump(),
        research_notes=research.text, model=settings.report_model,
        input_tokens=total_in, output_tokens=total_out, web_searches=searches,
        schema_version=REPORT_SCHEMA_VERSION,
        research_notes_compressed=compressed_text,
    )
    await db.record_usage(ticker, "base_report", False, total_in, total_out, searches, user_id=user_id)

    # Day 5: 결정론 품질 채점 (컴플라이언스=버그 게이트·출처 grounding). fail-open이되
    # 위반은 즉시 로그 — "매수/매도 표현이 출력에 등장하면 버그로 취급"(CLAUDE.md).
    try:
        scores = await quality.score_report(base_report_id, report.model_dump(), research.text)
        if scores["compliance"] < 1.0 or scores["grounding"] < 1.0:
            print(f"⚠ quality: {ticker} compliance={scores['compliance']} "
                  f"grounding={scores['grounding']:.2f} — quality_scores 참조")
    except Exception as e:
        print(f"⚠ quality 채점 실패(발행은 진행): {e}")

    meta = CostMeta(cache_hit=False, input_tokens=total_in,
                    output_tokens=total_out, web_searches=searches)
    return report, compressed_text or research.text, base_report_id, meta


async def evaluate_thesis(report: BaseReport, research_notes: str,
                          base_report_id, thesis_text: str, user=None) -> tuple[ThesisEval, CostMeta]:
    thesis_text = thesis_text.strip()
    user_id = user["id"] if user else None

    # 0) Day 2: 동일 리포트+동일 논거 재평가 캐시 (base_report_id 종속이라 리포트 갱신 시 자연 무효화)
    cached = await db.get_cached_thesis_eval(base_report_id, thesis_text)
    if cached:
        result = ThesisEval.model_validate_json(cached["evaluation"])
        await db.record_usage(report.ticker, "thesis_eval", True, 0, 0, 0, user_id=user_id)
        return result, CostMeta(cache_hit=True)

    await auth.enforce_quota(user)  # 평가도 유료 경로(캐시 미스) 직전에만 검사

    # 1) Haiku 전처리: 논거 → claims/assumptions/horizon
    prep = await llm.structured(
        model=settings.prep_model,
        system=prompts.THESIS_STRUCT_SYSTEM,
        user=thesis_text,
        schema=strict_schema(ThesisStruct),
        max_tokens=4000,  # Haiku(비추론)라 위험 낮지만 절단 클래스 동일 — 여유 상한
    )
    thesis_struct = llm.parse_json(prep.text)

    # 2) Fable 5 평가 — 캐시된 리포트/노트가 컨텍스트라 짧고 저렴한 호출
    evaluation = await llm.structured(
        model=settings.report_model,
        system=prompts.THESIS_EVAL_SYSTEM,
        user=prompts.thesis_eval_user_prompt(
            base_report_json=json.dumps(report.model_dump(), ensure_ascii=False),
            research_notes=research_notes,
            thesis_text=thesis_text,
            thesis_struct_json=json.dumps(thesis_struct, ensure_ascii=False),
        ),
        schema=strict_schema(ThesisEval),
        # max_tokens 기본(16000) 사용 — 2000 오버라이드는 Fable 내부추론 선소비로
        # 논거에 따라 절단됨(실측: "중국 수출 규제" 논거서 재현). 상한이라 과금 무관.
    )
    result = ThesisEval.model_validate(llm.parse_json(evaluation.text))

    # 인덱스 범위 검증 (스키마는 형태만 보장, 의미는 여기서 방어)
    result.supporting = [i for i in result.supporting if 0 <= i < len(report.bull_case)]
    result.contradicting = [i for i in result.contradicting if 0 <= i < len(report.bear_case)]

    total_in = prep.usage.input_tokens + evaluation.usage.input_tokens
    total_out = prep.usage.output_tokens + evaluation.usage.output_tokens

    await db.insert_thesis_eval(base_report_id, thesis_text, thesis_struct,
                                result.model_dump(), total_in, total_out,
                                user_id=user_id)
    await db.record_usage(report.ticker, "thesis_eval", False, total_in, total_out, 0, user_id=user_id)

    # Day 5: 평가문 컴플라이언스 채점 (fail-open)
    try:
        scores = await quality.score_eval(base_report_id, result.model_dump())
        if scores["compliance"] < 1.0:
            print(f"⚠ quality: {report.ticker} eval compliance 위반 — quality_scores 참조")
    except Exception as e:
        print(f"⚠ quality 채점 실패(발행은 진행): {e}")

    return result, CostMeta(cache_hit=False, input_tokens=total_in, output_tokens=total_out)
