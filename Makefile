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
