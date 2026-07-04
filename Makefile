.PHONY: db-up db-schema dev smoke smoke-thesis

db-up:
	docker compose up -d db

db-schema:
	psql postgresql://thesis:thesis@localhost:5433/thesis -f db/schema.sql

dev:
	uvicorn app.main:app --reload --port 8000

# 사용: make smoke TICKER=NVDA
smoke:
	python -m scripts.smoke_test $(TICKER)

# 사용: make smoke-thesis TICKER=NVDA THESIS="데이터센터 수요로 계속 상승한다"
smoke-thesis:
	python -m scripts.smoke_test $(TICKER) --thesis "$(THESIS)"

# Day 3: Next.js 대시보드 (백엔드 make dev와 함께 띄울 것)
# 포트 3200 사용 — 3000은 다른 로컬 서비스와 충돌하는 환경이 흔해 기본으로 피함.
web-dev:
	cd web && npm run dev -- -p 3200

web-build:
	cd web && npm run build
