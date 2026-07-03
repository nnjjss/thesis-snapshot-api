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

## 현재 단계: Day 1 완료 기준

- [ ] `make smoke TICKER=NVDA` → 한국어 JSON 리포트 출력
- [ ] 두 번째 실행에서 cache_hit=True
- [ ] scripts/smoke_test.py의 토큰 단가 상수를 실제 가격으로 갱신, 원가 1건 기록

## 로드맵 (초안 문서 참조)

Day 2: 캐시 정교화 + Haiku 압축 실험 / Day 3: Next.js 대시보드 /
Day 4: Stripe / Day 5: Langfuse 평가 / Day 6: 배포 / Day 7: 채널 공개
