"""Day 4: API 키 인증 + 무료 플랜 쿼터.

설계:
- 키 형식: ts_ + 32바이트 urlsafe — DB에는 sha256 해시만 저장(유출 시 원문 복구 불가)
- auth_required=False(기본, 로컬 dev/smoke): 키 없으면 익명 통과(user=None) — Day 1~3 동작 보존
- auth_required=True(운영): 키 없거나 무효면 401
- 쿼터: free 플랜은 최근 24h '유료' 호출(캐시미스) free_daily_limit건 — 캐시 히트는
  한계비용≈0이라 무제한(단위 경제 원칙 그대로). pro는 무제한. 초과 시 429.
"""
from __future__ import annotations

import hashlib
import secrets
from typing import Optional

from fastapi import Header, HTTPException

from app import db
from app.config import settings

API_KEY_PREFIX = "ts_"


def new_api_key() -> tuple[str, str]:
    """(원문 키, sha256 해시) — 원문은 발급 응답에서 1회만 노출."""
    key = API_KEY_PREFIX + secrets.token_urlsafe(32)
    return key, hash_key(key)


def hash_key(key: str) -> str:
    return hashlib.sha256(key.encode()).hexdigest()


async def resolve_user(x_api_key: Optional[str] = Header(default=None)):
    """FastAPI 의존성 — 헤더의 키를 사용자로 해석. 반환: asyncpg.Record | None."""
    if not x_api_key:
        if settings.auth_required:
            raise HTTPException(status_code=401, detail="X-API-Key required — POST /v1/signup 으로 발급")
        return None
    user = await db.get_user_by_key_hash(hash_key(x_api_key))
    if user is None:
        raise HTTPException(status_code=401, detail="invalid API key")
    return user


async def enforce_quota(user) -> None:
    """유료 호출(캐시미스) 발생 '전' 호출 — 글로벌 서킷브레이커 + free 플랜 24h 상한.

    주의: 리포트 캐시 히트 경로에서는 부르지 않는다(캐시는 무제한이 정책).
    익명(user=None)은 auth_required=False 로컬 모드뿐이므로 개인 쿼터 미적용.
    """
    # Day 7: 글로벌 일일 상한 — 플랜 무관, 비용 폭주 최후 방어선(캐시미스 1건≈$1.6).
    # 초과 시 503(서비스 용량)이지 사용자 잘못(429)이 아님 — 캐시 조회는 계속 동작.
    total = await db.count_global_paid_usage_24h()
    if total >= settings.global_daily_paid_limit:
        raise HTTPException(
            status_code=503,
            detail="오늘의 신규 생성 용량이 소진되었습니다 — 캐시된 리포트 조회는 계속 가능합니다. 내일 다시 시도해 주세요.",
        )

    if user is None or user["plan"] == "pro":
        return
    used = await db.count_paid_usage_24h(user["id"])
    if used >= settings.free_daily_limit:
        raise HTTPException(
            status_code=429,
            detail=f"free 플랜 24시간 상한({settings.free_daily_limit}건) 초과 — "
                   "캐시된 리포트 조회는 계속 무료입니다. Pro 업그레이드: POST /v1/billing/checkout",
        )


# Day 7: signup IP 레이트리밋 — 이메일 무한 생성으로 free 쿼터를 우회하는 벡터 차단.
# 단일 인스턴스 전제의 in-memory 슬라이딩 윈도우(현 배포 구조와 일치). 다중 인스턴스 시 Redis 전환.
_signup_hits: dict[str, list[float]] = {}


def check_signup_rate(ip: str) -> None:
    import time
    now = time.time()
    window = [t for t in _signup_hits.get(ip, []) if now - t < 3600]
    if len(window) >= settings.signup_rate_limit_per_hour:
        raise HTTPException(status_code=429, detail="가입 시도가 너무 잦습니다 — 1시간 후 다시 시도해 주세요.")
    window.append(now)
    _signup_hits[ip] = window
    if len(_signup_hits) > 10_000:  # 무한 성장 방지(오래된 IP 정리)
        for k in [k for k, v in _signup_hits.items() if all(now - t >= 3600 for t in v)]:
            del _signup_hits[k]
