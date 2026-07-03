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
# ⚠ 포트 3200: 이 머신은 3000을 TIO 대시보드(Cloudflare Access 뒤, 루프백 바인딩)가 점유 —
#   3000 접속 시 "Forbidden: Cloudflare Access required"는 TIO의 응답이지 이 앱이 아님.
web-dev:
	cd web && npm run dev -- -p 3200

web-build:
	cd web && npm run build
