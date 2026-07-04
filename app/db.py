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
async def get_cached_base_report(ticker: str, schema_version: int) -> Optional[asyncpg.Record]:
    # schema_version 필터(Day 2): 형태가 다른 옛 캐시 행이 새 Pydantic 파싱을 깨지 않게
    ttl = timedelta(hours=settings.cache_ttl_hours)
    return await pool().fetchrow(
        """
        SELECT id, report, research_notes, research_notes_compressed, created_at
        FROM base_reports
        WHERE ticker = $1 AND created_at > now() - $2::interval
          AND schema_version = $3
        ORDER BY created_at DESC
        LIMIT 1
        """,
        ticker, ttl, schema_version,
    )


async def insert_base_report(ticker: str, as_of: str, report: dict,
                             research_notes: str, model: str,
                             input_tokens: int, output_tokens: int,
                             web_searches: int, schema_version: int,
                             research_notes_compressed: Optional[str] = None):
    return await pool().fetchval(
        """
        INSERT INTO base_reports
            (ticker, as_of, report, research_notes, research_notes_compressed,
             model, schema_version, input_tokens, output_tokens, web_searches)
        VALUES ($1, $2::date, $3::jsonb, $4, $5, $6, $7, $8, $9, $10)
        RETURNING id
        """,
        # asyncpg는 date 파라미터에 str 자동 캐스팅을 안 함(::date가 있어도 바인딩은 파이썬 타입 기준)
        ticker, date.fromisoformat(as_of), json.dumps(report, ensure_ascii=False),
        research_notes, research_notes_compressed, model, schema_version,
        input_tokens, output_tokens, web_searches,
    )


async def get_cached_thesis_eval(base_report_id, thesis_text: str) -> Optional[asyncpg.Record]:
    """동일 리포트+동일 논거의 기존 평가 — base_report_id가 리포트 세대에 종속이라
    리포트가 갱신되면(새 id) 자연 무효화됨. 별도 TTL 불필요."""
    return await pool().fetchrow(
        """
        SELECT evaluation FROM thesis_evals
        WHERE base_report_id = $1 AND md5(thesis_text) = md5($2) AND thesis_text = $2
        ORDER BY created_at DESC
        LIMIT 1
        """,
        base_report_id, thesis_text,
    )


async def insert_thesis_eval(base_report_id, thesis_text: str,
                             thesis_struct: dict, evaluation: dict,
                             input_tokens: int, output_tokens: int,
                             user_id=None) -> None:
    await pool().execute(
        """
        INSERT INTO thesis_evals
            (base_report_id, thesis_text, thesis_struct, evaluation,
             input_tokens, output_tokens, user_id)
        VALUES ($1, $2, $3::jsonb, $4::jsonb, $5, $6, $7)
        """,
        base_report_id, thesis_text,
        json.dumps(thesis_struct, ensure_ascii=False),
        json.dumps(evaluation, ensure_ascii=False),
        input_tokens, output_tokens, user_id,
    )


async def record_usage(ticker: str, kind: str, cache_hit: bool,
                       input_tokens: int, output_tokens: int,
                       web_searches: int, user_id=None) -> None:
    await pool().execute(
        """
        INSERT INTO usage_events
            (ticker, kind, cache_hit, input_tokens, output_tokens, web_searches, user_id)
        VALUES ($1, $2, $3, $4, $5, $6, $7)
        """,
        ticker, kind, cache_hit, input_tokens, output_tokens, web_searches, user_id,
    )


# ------------------------------------------------------------------
# Day 4: 사용자·플랜·쿼터
# ------------------------------------------------------------------
async def create_user(email: str, api_key_hash: str) -> Optional[asyncpg.Record]:
    """가입(멱등 아님 — 이메일 중복 시 None). 키 원문은 저장하지 않는다."""
    try:
        return await pool().fetchrow(
            """
            INSERT INTO users (email, api_key_hash) VALUES ($1, $2)
            RETURNING id, email, plan
            """,
            email, api_key_hash,
        )
    except asyncpg.UniqueViolationError:
        return None


async def get_user_by_key_hash(api_key_hash: str) -> Optional[asyncpg.Record]:
    return await pool().fetchrow(
        "SELECT id, email, plan, stripe_customer_id FROM users WHERE api_key_hash = $1",
        api_key_hash,
    )


async def set_user_plan(email: str, plan: str,
                        stripe_customer_id: Optional[str] = None) -> bool:
    """웹훅에서 호출 — Stripe checkout의 customer_email 기준으로 플랜 전환."""
    result = await pool().execute(
        """
        UPDATE users SET plan = $2,
               stripe_customer_id = COALESCE($3, stripe_customer_id)
        WHERE email = $1
        """,
        email, plan, stripe_customer_id,
    )
    return result.endswith("1")


async def insert_quality_score(base_report_id, kind: str, score: float,
                               details: list) -> None:
    """Day 5: 결정론 품질 점수 영속 (컴플라이언스 위반은 로그로도 즉시 가시화)."""
    await pool().execute(
        """
        INSERT INTO quality_scores (base_report_id, kind, score, details)
        VALUES ($1, $2, $3, $4::jsonb)
        """,
        base_report_id, kind, score, json.dumps(details, ensure_ascii=False),
    )


async def count_global_paid_usage_24h() -> int:
    """Day 7: 전체 서비스 24h 유료 호출 — 글로벌 서킷브레이커 분모(사용자 무관)."""
    return await pool().fetchval(
        """
        SELECT count(*) FROM usage_events
        WHERE cache_hit = FALSE AND kind IN ('base_report', 'thesis_eval')
          AND created_at > now() - interval '24 hours'
        """,
    )


async def count_paid_usage_24h(user_id) -> int:
    """쿼터 분모: 최근 24h '유료' 호출(캐시미스)만 — 캐시 히트는 한계비용≈0이라 미과금."""
    return await pool().fetchval(
        """
        SELECT count(*) FROM usage_events
        WHERE user_id = $1 AND cache_hit = FALSE
          AND created_at > now() - interval '24 hours'
        """,
        user_id,
    )
