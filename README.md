# Thesis Snapshot API

미국 티커 → 한국어 투자 논거 검증 리포트. Claude Fable 5 + web search + 구조화 출력.

> ⚠️ 본 프로젝트의 출력물은 정보 제공 목적이며 투자 자문이 아닙니다.

## 빠른 시작

```bash
# 0. 의존성
python3.12 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# 1. 환경변수
cp .env.example .env   # ANTHROPIC_API_KEY 입력

# 2. DB (pgvector 포함 Postgres, 포트 5433)
make db-up
make db-schema

# 3. Day 1 스모크 테스트 — 티커 → JSON 리포트
make smoke TICKER=NVDA
make smoke TICKER=NVDA   # 두 번째: cache_hit=True 확인

# 4. API 서버
make dev
curl -X POST localhost:8000/v1/reports \
  -H 'content-type: application/json' \
  -d '{"ticker":"NVDA","thesis":"데이터센터 수요로 계속 상승한다"}'
```

## 구조

```
app/
  models.py            # 리포트 JSON 스키마 (단일 진실 소스)
  config.py            # env 설정, 모델 라우팅
  db.py                # asyncpg 캐시/기록 레이어
  llm/
    client.py          # research() + structured() 래퍼
    prompts.py         # 프롬프트 v1 + 컴플라이언스 규칙
  services/
    report_service.py  # 캐시 → 리서치 → 구조화 → 논거 평가
  routers/reports.py   # POST /v1/reports
db/schema.sql          # base_reports 캐시, thesis_evals, usage_events
scripts/smoke_test.py  # Day 1 검증 + 원가 실측
```

## 파이프라인

```
POST /v1/reports {ticker, thesis?}
  ├─ 캐시 히트(24h) ─────────────→ 저장된 리포트
  └─ 미스:
       Phase A: Fable 5 + web_search → 리서치 노트(출처 포함)
       Phase B: Fable 5 + output_config(json_schema) → BaseReport JSON
       → base_reports 저장
  thesis 있으면:
       Haiku 4.5: 논거 구조화 → Fable 5: 평가(ThesisEval JSON, 증분 호출)
```

## Day 1 완료 기준

- [ ] `make smoke TICKER=NVDA` 성공 (한국어 리포트 JSON)
- [ ] 재실행 시 `cache_hit=True`
- [ ] smoke_test.py 토큰 단가 상수 갱신 → 캐시 미스 1건 원가 기록
