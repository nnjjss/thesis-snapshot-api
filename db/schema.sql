-- Thesis Snapshot API — PostgreSQL schema (Day 1)
-- 실행: psql $DATABASE_URL -f db/schema.sql

CREATE EXTENSION IF NOT EXISTS vector;      -- pgvector (v2: BGE-M3 임베딩용, Day 1에는 미사용)
CREATE EXTENSION IF NOT EXISTS pgcrypto;    -- gen_random_uuid()

-- ---------------------------------------------------------------
-- 기본 리포트 캐시 (강세/약세 논거) — 단위 경제의 핵심
-- 동일 티커 24h 내 재요청 시 이 테이블에서 반환
-- ---------------------------------------------------------------
CREATE TABLE IF NOT EXISTS base_reports (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    ticker          TEXT NOT NULL,
    as_of           DATE NOT NULL,
    report          JSONB NOT NULL,          -- BaseReport JSON (bull_case, bear_case, sources)
    research_notes  TEXT,                    -- Phase A 원본 리서치 노트 (논거 평가 컨텍스트로 재사용)
    model           TEXT NOT NULL,
    input_tokens    INTEGER NOT NULL DEFAULT 0,
    output_tokens   INTEGER NOT NULL DEFAULT 0,
    web_searches    INTEGER NOT NULL DEFAULT 0,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
    -- v2: embedding vector(1024)  -- BGE-M3, 유사 논거 검색용
);

CREATE INDEX IF NOT EXISTS idx_base_reports_ticker_created
    ON base_reports (ticker, created_at DESC);

-- ---------------------------------------------------------------
-- 사용자 논거 평가 기록 — v2 "논거 히스토리" 기능의 씨앗
-- ---------------------------------------------------------------
CREATE TABLE IF NOT EXISTS thesis_evals (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    base_report_id  UUID NOT NULL REFERENCES base_reports(id) ON DELETE CASCADE,
    user_id         UUID,                    -- Day 4 인증 붙기 전까지 NULL 허용
    thesis_text     TEXT NOT NULL,
    thesis_struct   JSONB,                   -- Haiku 전처리 결과 (claims/assumptions/horizon)
    evaluation      JSONB NOT NULL,          -- ThesisEval JSON
    input_tokens    INTEGER NOT NULL DEFAULT 0,
    output_tokens   INTEGER NOT NULL DEFAULT 0,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_thesis_evals_user
    ON thesis_evals (user_id, created_at DESC);

-- ---------------------------------------------------------------
-- 사용자 & 사용량 (Day 4 Stripe 연동 시 확장)
-- ---------------------------------------------------------------
CREATE TABLE IF NOT EXISTS users (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email           TEXT UNIQUE NOT NULL,
    plan            TEXT NOT NULL DEFAULT 'free',   -- free | pro
    stripe_customer_id TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS usage_events (
    id              BIGSERIAL PRIMARY KEY,
    user_id         UUID REFERENCES users(id),
    ticker          TEXT NOT NULL,
    kind            TEXT NOT NULL,           -- base_report | thesis_eval
    cache_hit       BOOLEAN NOT NULL DEFAULT FALSE,
    input_tokens    INTEGER NOT NULL DEFAULT 0,
    output_tokens   INTEGER NOT NULL DEFAULT 0,
    web_searches    INTEGER NOT NULL DEFAULT 0,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_usage_events_user_created
    ON usage_events (user_id, created_at DESC);
