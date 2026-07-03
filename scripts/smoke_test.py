"""Day 1 스모크 테스트 겸 원가 실측 스크립트.

사용법:
    python -m scripts.smoke_test NVDA
    python -m scripts.smoke_test NVDA --thesis "데이터센터 수요로 계속 상승한다"

출력:
    - 리포트 JSON (한국어)
    - 토큰/검색 사용량과 추정 원가 (USD)
      * 실제 단가는 Anthropic 가격 페이지에서 확인 후 아래 상수 갱신
"""
import argparse
import asyncio
import json
import sys

from app import db
from app.services import report_service

# Fable 5 실가격 (2026-07-04 확인, claude-fable-5 = $10/$50 per MTok)
PRICE_PER_MTOK_INPUT = 10.00   # Fable 5 input $/MTok
PRICE_PER_MTOK_OUTPUT = 50.00  # Fable 5 output $/MTok
PRICE_PER_SEARCH = 0.01        # $10 / 1,000 searches (문서 확인됨)


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("ticker")
    parser.add_argument("--thesis", default=None)
    args = parser.parse_args()

    await db.init_pool()
    try:
        report, notes, base_id, meta = await report_service.get_or_create_base_report(args.ticker)
        print("=" * 60)
        print(json.dumps(report.model_dump(), ensure_ascii=False, indent=2))

        if args.thesis:
            ev, ev_meta = await report_service.evaluate_thesis(report, notes, base_id, args.thesis)
            print("-" * 60)
            print(json.dumps(ev.model_dump(), ensure_ascii=False, indent=2))
            meta.input_tokens += ev_meta.input_tokens
            meta.output_tokens += ev_meta.output_tokens

        print("=" * 60)
        print(f"cache_hit={meta.cache_hit}  in={meta.input_tokens:,}  "
              f"out={meta.output_tokens:,}  searches={meta.web_searches}")
        search_cost = meta.web_searches * PRICE_PER_SEARCH
        if PRICE_PER_MTOK_INPUT and PRICE_PER_MTOK_OUTPUT:
            token_cost = (meta.input_tokens / 1e6) * PRICE_PER_MTOK_INPUT \
                       + (meta.output_tokens / 1e6) * PRICE_PER_MTOK_OUTPUT
            print(f"추정 원가: ${token_cost + search_cost:.4f} "
                  f"(tokens ${token_cost:.4f} + search ${search_cost:.4f})")
        else:
            print(f"검색 원가: ${search_cost:.4f} — 토큰 단가 상수를 채우면 총원가 계산됨")
    finally:
        await db.close_pool()


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
