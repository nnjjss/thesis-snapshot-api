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

## 현재 단계: Day 7 완료 — 7일 빌드 종료, 공개 준비 완료

- [x] Day 7 런치 가드: ① signup IP 레이트리밋(시간당 5회, in-memory 슬라이딩 윈도우 —
  이메일 무한 생성=쿼터 우회 차단) ② 글로벌 일일 유료호출 서킷브레이커
  (GLOBAL_DAILY_PAID_LIMIT=50 ≈ $80/일 상한, 초과 시 503·캐시 조회는 계속) — 둘 다 검증.
- [x] 공개용 README(라이브 URL·차별점·API 예시·요금) + docs/launch-post.md(게시 초안+체크리스트).
- 게시는 사용자 액션: launch-post.md 다듬어 채널 게시. Stripe/Langfuse 키도 사용자 주입 대기.

## 이전 단계 완료 기록 (Day 6)

- [x] Day 6 Railway 배포(프로젝트 thesis-snapshot): backend+Postgres+web.
  웹 https://web-production-b0a48.up.railway.app /
  API https://backend-production-d867.up.railway.app (AUTH_REQUIRED=true).
- 배포 함정(전부 실측): ① Procfile은 Railpack이 YAML 파싱 — 값 따옴표 필수
  ② 공개 엣지는 IPv4(0.0.0.0 바인드) — `::` 단일 바인드 시 502
  ③ 도메인 생성 시 -p 포트 명시(미지정 Target port '-' → 502)
  ④ 모노레포 서브디렉터리는 `railway up <dir> --path-as-root`
  ⑤ NEXT_PUBLIC_* 빌드타임 인라인 미동작 → /api/config 런타임 컨피그로 해소
  ⑥ Next rewrites 프록시가 장시간(1~2분) 요청 절단 → 브라우저가 백엔드
  직접 호출(CORS allow_origins=[앱 도메인]).
- Stripe/Langfuse 키는 아직 미설정(각각 503 graceful/no-op) — Day 7 전 주입.

## 이전 단계 완료 기록 (Day 5)

- [x] Day 5 품질 평가(결정론, LLM 무관·항상 실행): `app/quality.py` —
  ① compliance: 매수/매도/목표가 지시·권유 고정밀 패턴(서술 용법 '순매수·매수세'는
  무고 처리, 오탐 0·미탐 0 검증) ② grounding: 리포트 source_url이 리서치 노트에
  실재하는지(환각 출처 검출 검증). quality_scores 테이블 영속 + 위반 즉시 로그.
- [x] Day 5 Langfuse(4.x, OTel): `app/llm/tracing.py` — research/structured/compress
  3 호출 generation 관측 + 품질 점수 create_score(session_id=base_report_id 그룹핑).
  키 없으면 완전 no-op, 죽은 호스트/가짜 키도 요청 경로 미차단 실증(fail-open).
- [x] Day 5 에러 분류: 라우터 _classify — LLM 레이트리밋→429, 상류 5xx/연결→503,
  DB→503, 기타→502 (재시도 판단 근거를 클라이언트에).
- Langfuse 실서버 연동(계정 필요)만 미검증 — 키 넣으면 자동 활성.

## 이전 단계 완료 기록 (Day 4)

- [x] Day 4 인증: POST /v1/signup(이메일→API 키, sha256 해시만 저장) + X-API-Key
  의존성. AUTH_REQUIRED=false(기본)면 익명 허용 — 로컬 dev/smoke 무영향.
- [x] Day 4 쿼터: free 플랜 24h 신규 생성(캐시미스) 10건 — LLM 호출 '전' 차단(429),
  캐시 히트는 무제한(한계비용≈0 단위경제 원칙). pro 무제한.
- [x] Day 4 Stripe: /v1/billing/checkout(구독, 미설정 시 503) + /v1/billing/webhook
  (서명 검증→plan 전환: completed→pro, subscription.deleted→free).
  ⚠ stripe v15 함정: StripeObject는 .get() 없음(KeyError:'get') — 서명만
  WebhookSignature.verify_header로 검증하고 데이터는 원문 JSON dict로 접근.
- [x] 대시보드 AccountBox: 무료 키 발급/localStorage 저장/X-API-Key 자동 첨부/
  Pro 업그레이드(checkout 리다이렉트).
- Stripe 실키 연동(계정 필요)만 미검증 — 키 넣고 checkout→웹훅 E2E 1회 돌릴 것.

## 이전 단계 완료 기록 (Day 3)

- [x] Day 3: Next.js 16 대시보드(`web/`, App Router+Tailwind) — 티커/논거 폼 →
  리포트(강세/약세 카드·confidence 배지·출처 링크) + 논거 검증(verdict 배지·
  supporting/contradicting 카드 하이라이트) + disclaimer 상시 노출.
  백엔드는 next.config rewrites 프록시(/api/backend/* → :8000, CORS 불필요,
  배포 시 BACKEND_URL env). 실행: `make dev` + `make web-dev`.
  타입은 lib/types.ts가 Pydantic 미러(단일 소스는 백엔드).

## 이전 단계 완료 기록

- [x] Day 1: smoke 한국어 리포트·cache_hit=True·원가 기록(캐시미스 $1.62)
- [x] Day 2 캐시 정교화: schema_version 캐시 태깅 / thesis_evals 캐시(같은 리포트+같은 논거 재평가 = $0) / compress 사용량 별도 kind 기록
- [x] Day 2 Haiku 압축: 실험(scripts/compress_experiment.py) → 손익분기 0.8회로 배선. **효과 가드 필수** — Haiku가 비결정적으로 압축 실패(팽창)하는 케이스 실측, 원본 90% 미만일 때만 채택
- [x] 부수 수정: 평가 호출 max_tokens=2000 절단 버그(Fable 내부추론 선소비 — 명시 오버라이드가 기본 상향을 우회하고 있었음)

## 로드맵 (초안 문서 참조)

Day 2: 캐시 정교화 + Haiku 압축 실험 / Day 3: Next.js 대시보드 /
Day 4: Stripe / Day 5: Langfuse 평가 / Day 6: 배포 / Day 7: 채널 공개
