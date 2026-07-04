# Thesis Snapshot — 투자 논거 검증

**미국 티커 → 한국어 강세/약세 논거 리포트, 그리고 "내 투자 논거가 최신 데이터로 버티는지" 검증.**

> ⚠️ 본 서비스의 모든 출력물은 정보 제공 목적이며 투자 자문이 아닙니다.
> 매수/매도/목표가를 제시하지 않으며, 그런 표현이 출력되면 버그로 취급합니다.

## 🌐 라이브

- 대시보드: https://web-production-b0a48.up.railway.app
- API: https://backend-production-d867.up.railway.app

## 어떻게 다른가

1. **논거 검증에 집중** — "오를까요?"가 아니라 "내 논거의 근거와 가정이 아직 유효한가"에 답합니다.
   verdict는 4단계(유효/부분 유효/약화됨/근거 부족)이고, 논거의 생사를 가를 관찰 포인트를 함께 제시합니다.
2. **모든 논거에 출처** — 리포트의 각 논거는 웹 리서치 원문 URL이 붙고, 출처가 리서치 노트에
   실재하는지 기계 검사(grounding)를 통과해야 합니다. 컴플라이언스(매매 지시 표현 금지)도 기계 게이트.
3. **캐시 단위경제** — 같은 티커의 리포트는 24시간 캐시. 캐시 조회는 무제한 무료,
   신규 생성(웹 리서치 1~2분)만 쿼터를 씁니다.

## 사용법

### 웹
대시보드에서 이메일로 무료 API 키 발급(24h당 신규 생성 10건) → 티커 입력 → 논거는 선택.

### API
```bash
# 1) 가입 — API 키 발급 (1회만 표시)
curl -X POST https://backend-production-d867.up.railway.app/v1/signup \
  -H 'content-type: application/json' -d '{"email":"you@example.com"}'

# 2) 리포트 + 논거 검증
curl -X POST https://backend-production-d867.up.railway.app/v1/reports \
  -H 'content-type: application/json' -H 'X-API-Key: ts_...' \
  -d '{"ticker":"NVDA","thesis":"데이터센터 수요 덕분에 실적 성장이 이어질 것이다"}'
```

## 요금

| 플랜 | 내용 |
|------|------|
| Free | 24시간당 신규 생성 10건 · 캐시 조회 무제한 |
| Pro | 무제한 생성 (Stripe 결제 연동 준비 중) |

## 셀프 호스트

```bash
python3.12 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # ANTHROPIC_API_KEY 입력
make db-up && make db-schema  # Postgres(5433) + 스키마
make dev                      # API :8000
make web-dev                  # 대시보드 :3200
```

## 아키텍처 (요약)

```
티커 → [캐시 24h?] ── 히트 ──→ 저장된 리포트 (무료·즉시)
          │ 미스
          ├ Phase A: Claude Fable 5 + web search → 리서치 노트(출처 포함)
          ├ Phase B: 구조화 출력(json_schema) → 리포트 JSON
          ├ Haiku 압축(평가 컨텍스트 최적화) + 품질 게이트(컴플라이언스·grounding)
          └ 캐시 저장
논거 → Haiku 구조화 → Fable 5 평가(캐시 컨텍스트, 증분 호출) → verdict + 관찰 포인트
```

기술: FastAPI · PostgreSQL · Next.js 16 · Claude API(구조화 출력·web search) · Langfuse(트레이싱)

## 개발 기록

7일 빌드 로그는 `CLAUDE.md`의 단계별 완료 기록 참조 (Day 1 파이프라인 → Day 2 캐시/압축 →
Day 3 대시보드 → Day 4 인증/결제 → Day 5 품질 평가/트레이싱 → Day 6 배포 → Day 7 공개).
