"""Day 2 — Haiku 압축 실험 (A/B 실측).

캐시된 리포트의 research_notes를 (A) 원본 그대로 vs (B) Haiku 압축본으로
동일한 논거 평가를 돌려 비용·판정 일치를 비교한다. DB에는 아무것도 쓰지 않는다
(운영 thesis_evals 캐시/기록 오염 방지 — llm 모듈 직접 호출).

사용: python -m scripts.compress_experiment NVDA --thesis "..."
"""
import argparse
import asyncio
import json
import re
import sys

from app import db
from app.config import settings
from app.llm import client as llm
from app.llm import prompts
from app.models import BaseReport, ThesisEval, ThesisStruct, strict_schema

# $/MTok (2026-07 실가격) — report_model=Fable 5, prep_model=Haiku 4.5
FABLE_IN, FABLE_OUT = 10.00, 50.00
HAIKU_IN, HAIKU_OUT = 1.00, 5.00

DEFAULT_THESIS = "데이터센터 수요 덕분에 앞으로도 실적 성장이 이어질 것이다"


def cost(usage, price_in, price_out) -> float:
    return usage.input_tokens / 1e6 * price_in + usage.output_tokens / 1e6 * price_out


async def eval_once(report: BaseReport, notes: str, thesis_text: str,
                    thesis_struct_json: str):
    """report_service.evaluate_thesis의 평가 호출과 동일 형상 — DB 기록만 없음."""
    return await llm.structured(
        model=settings.report_model,
        system=prompts.THESIS_EVAL_SYSTEM,
        user=prompts.thesis_eval_user_prompt(
            base_report_json=json.dumps(report.model_dump(), ensure_ascii=False),
            research_notes=notes,
            thesis_text=thesis_text,
            thesis_struct_json=thesis_struct_json,
        ),
        schema=strict_schema(ThesisEval),
        # 서비스와 형상 일치 — max_tokens 기본(16000), 2000은 Fable 추론 선소비로 절단됨
    )


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("ticker")
    parser.add_argument("--thesis", default=DEFAULT_THESIS)
    args = parser.parse_args()

    await db.init_pool()
    try:
        cached = await db.get_cached_base_report(args.ticker.upper())
        if not cached:
            print(f"캐시된 {args.ticker} 리포트 없음 — 먼저 make smoke TICKER={args.ticker}")
            return
        report = BaseReport.model_validate_json(cached["report"])
        notes = cached["research_notes"] or ""

        # 전처리(ThesisStruct)는 1회만 돌려 A/B 공통 입력으로 사용 (통제 변수)
        prep = await llm.structured(
            model=settings.prep_model, system=prompts.THESIS_STRUCT_SYSTEM,
            user=args.thesis, schema=strict_schema(ThesisStruct), max_tokens=4000)
        struct_json = json.dumps(llm.parse_json(prep.text), ensure_ascii=False)

        # ── A: 원본 노트 ──
        a = await eval_once(report, notes, args.thesis, struct_json)
        a_eval = ThesisEval.model_validate(llm.parse_json(a.text))
        a_cost = cost(a.usage, FABLE_IN, FABLE_OUT)

        # ── 압축 (Haiku) ──
        comp = await llm.compress(prompts.COMPRESS_SYSTEM, notes)
        comp_cost = cost(comp.usage, HAIKU_IN, HAIKU_OUT)

        # ── B: 압축 노트 ──
        b = await eval_once(report, comp.text, args.thesis, struct_json)
        b_eval = ThesisEval.model_validate(llm.parse_json(b.text))
        b_cost = cost(b.usage, FABLE_IN, FABLE_OUT)

        urls = lambda t: set(re.findall(r"https?://\S+", t))
        url_kept = len(urls(notes) & urls(comp.text))

        print("=" * 64)
        print(f"노트 길이: 원본 {len(notes):,}자 → 압축 {len(comp.text):,}자 "
              f"({len(comp.text)/max(len(notes),1)*100:.0f}%)  |  "
              f"URL 보존 {url_kept}/{len(urls(notes))}")
        print(f"압축 비용(Haiku 1회): in={comp.usage.input_tokens:,} "
              f"out={comp.usage.output_tokens:,} → ${comp_cost:.4f}")
        print("-" * 64)
        print(f"A(원본) 평가:  in={a.usage.input_tokens:,} out={a.usage.output_tokens:,} → ${a_cost:.4f}")
        print(f"B(압축) 평가:  in={b.usage.input_tokens:,} out={b.usage.output_tokens:,} → ${b_cost:.4f}")
        saving = a_cost - b_cost
        breakeven = comp_cost / saving if saving > 0 else float("inf")
        print(f"평가 1회당 절감: ${saving:.4f}  |  압축비 회수 손익분기: {breakeven:.1f}회")
        print("-" * 64)
        print(f"verdict:        A={a_eval.verdict}  B={b_eval.verdict}  "
              f"{'✅일치' if a_eval.verdict == b_eval.verdict else '⚠️불일치'}")
        print(f"supporting:     A={a_eval.supporting}  B={b_eval.supporting}")
        print(f"contradicting:  A={a_eval.contradicting}  B={b_eval.contradicting}")
        print(f"[A reasoning] {a_eval.reasoning_ko[:200]}")
        print(f"[B reasoning] {b_eval.reasoning_ko[:200]}")
    finally:
        await db.close_pool()


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
