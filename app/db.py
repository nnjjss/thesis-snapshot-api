"""asyncpg 기반 DB 레이어. Day 1은 캐시/기록만 — ORM 없이 평이한 SQL."""
from __future__ import annotations

import json
from datetime import date, timedelta
from typing import Optional

import asyncpg

from app.config import settings

_pool: Optional[asyncpg.Pool] = None


async def init_pool() -> None:
    global _pool
    if _pool is None:
        _pool = await asyncpg.create_pool(settings.database_url, min_size=1, max_size=5)


async def close_pool() -> None:
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None


def pool() -> asyncpg.Pool:
    assert _pool is not None, "DB pool not initialized — call init_pool() first"
    return _pool


# ------------------------------------------------------------------
# base_reports 캐시
# ------------------------------------------------------------------
async def get_cached_base_report(ticker: str) -> Optional[asyncpg.Record]:
    ttl = timedelta(hours=settings.cache_ttl_hours)
    return await pool().fetchrow(
        """
        SELECT id, report, research_notes, created_at
        FROM base_reports
        WHERE ticker = $1 AND created_at > now() - $2::interval
        ORDER BY created_at DESC
        LIMIT 1
        """,
        ticker, ttl,
    )


async def insert_base_report(ticker: str, as_of: str, report: dict,
                             research_notes: str, model: str,
                             input_tokens: int, output_tokens: int,
                             web_searches: int):
    return await pool().fetchval(
        """
        INSERT INTO base_reports
            (ticker, as_of, report, research_notes, model,
             input_tokens, output_tokens, web_searches)
        VALUES ($1, $2::date, $3::jsonb, $4, $5, $6, $7, $8)
        RETURNING id
        """,
        # asyncpg는 date 파라미터에 str 자동 캐스팅을 안 함(::date가 있어도 바인딩은 파이썬 타입 기준)
        ticker, date.fromisoformat(as_of), json.dumps(report, ensure_ascii=False),
        research_notes, model, input_tokens, output_tokens, web_searches,
    )


async def insert_thesis_eval(base_report_id, thesis_text: str,
                             thesis_struct: dict, evaluation: dict,
                             input_tokens: int, output_tokens: int) -> None:
    await pool().execute(
        """
        INSERT INTO thesis_evals
            (base_report_id, thesis_text, thesis_struct, evaluation,
             input_tokens, output_tokens)
        VALUES ($1, $2, $3::jsonb, $4::jsonb, $5, $6)
        """,
        base_report_id, thesis_text,
        json.dumps(thesis_struct, ensure_ascii=False),
        json.dumps(evaluation, ensure_ascii=False),
        input_tokens, output_tokens,
    )


async def record_usage(ticker: str, kind: str, cache_hit: bool,
                       input_tokens: int, output_tokens: int,
                       web_searches: int) -> None:
    await pool().execute(
        """
        INSERT INTO usage_events
            (ticker, kind, cache_hit, input_tokens, output_tokens, web_searches)
        VALUES ($1, $2, $3, $4, $5, $6)
        """,
        ticker, kind, cache_hit, input_tokens, output_tokens, web_searches,
    )
