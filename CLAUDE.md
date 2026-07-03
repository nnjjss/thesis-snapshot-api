# CLAUDE.md — Thesis Snapshot API

한국어 투자 논거 검증 리포트 API. FastAPI + PostgreSQL(pgvector) + Claude API.

## 아키텍처 원칙 (변경 금지)

1. **2-Phase 생성**: 리서치(Fable 5 + web search, 자유 텍스트) → 구조화(output_config json_schema).
   web search와 grammar 제약을 한 호출에 섞지 않는다.
2. **캐시 우선**: base_reports는 24h TTL 캐시. 논거 평가는 캐시된 리포트+노트를
   컨텍스트로 쓰는 증분 호출. 이 분리가 단위 경제의 핵심 — 무너뜨리지 말 것.
3. **스키마 단일 소스**: JSON 구조는 `app/models.py`의 Pydantic 모델이 유일한 정의.
   LLM 스키마는 `strict_schema()`로 파생. 스키마를 프롬프트에 하드코딩 금지.

## 컴플라이언스 (절대 규칙)

- 프롬프트의 `COMPLIANCE_RULES` 블록 삭제/완화 금지
- 매수/매도/목표가 표현이 출력에 등장하면 버그로 취급
- `DISCLAIMER_KO`는 모든 응답에 자동 포함 — 제거 금지

## 코드 규약

- Python 3.12, async 우선. DB는 asyncpg 평문 SQL (ORM 도입 금지 — Day 3 프론트가 Prisma를 쓰더라도 백엔드는 유지)
- 모델명은 `app/config.py`에서만. 코드에 모델 문자열 하드코딩 금지
- 새 LLM 호출 추가 시 반드시 `LLMUsage`로 토큰/검색 집계 → usage_events 기록

## 자주 쓰는 명령

```bash
make db-up && make db-schema   # 최초 1회
make dev                        # 서버
make smoke TICKER=NVDA          # 캐시 미스 경로 테스트
make smoke TICKER=NVDA          # 한 번 더 → cache_hit=True 확인
make smoke-thesis TICKER=NVDA THESIS="..."
```

## 현재 단계: Day 2 완료 (Day 3 = Next.js 대시보드)

- [x] Day 1: smoke 한국어 리포트·cache_hit=True·원가 기록(캐시미스 $1.62)
- [x] Day 2 캐시 정교화: schema_version 캐시 태깅 / thesis_evals 캐시(같은 리포트+같은 논거 재평가 = $0) / compress 사용량 별도 kind 기록
- [x] Day 2 Haiku 압축: 실험(scripts/compress_experiment.py) → 손익분기 0.8회로 배선. **효과 가드 필수** — Haiku가 비결정적으로 압축 실패(팽창)하는 케이스 실측, 원본 90% 미만일 때만 채택
- [x] 부수 수정: 평가 호출 max_tokens=2000 절단 버그(Fable 내부추론 선소비 — 명시 오버라이드가 기본 상향을 우회하고 있었음)

## 로드맵 (초안 문서 참조)

Day 2: 캐시 정교화 + Haiku 압축 실험 / Day 3: Next.js 대시보드 /
Day 4: Stripe / Day 5: Langfuse 평가 / Day 6: 배포 / Day 7: 채널 공개
