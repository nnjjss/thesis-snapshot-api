"""Thesis Snapshot API — FastAPI 엔트리포인트.

실행: uvicorn app.main:app --reload --port 8000
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app import db
from app.routers import reports


@asynccontextmanager
async def lifespan(app: FastAPI):
    await db.init_pool()
    yield
    await db.close_pool()


app = FastAPI(
    title="Thesis Snapshot API",
    version="0.1.0",
    description="한국어 투자 논거 검증 리포트 API (정보 제공 목적, 투자 자문 아님)",
    lifespan=lifespan,
)
app.include_router(reports.router)


@app.get("/health")
async def health():
    return {"status": "ok"}
