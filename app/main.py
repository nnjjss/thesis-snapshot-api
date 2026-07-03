"""Thesis Snapshot API — FastAPI 엔트리포인트.

실행: uvicorn app.main:app --reload --port 8000
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import db
from app.config import settings
from app.routers import billing, reports, users


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
# Day 6: 대시보드가 백엔드를 직접 호출(캐시미스 리포트는 1~2분 — Next rewrites 프록시가
# 장시간 요청을 끊는 문제 프로덕션 실측). 허용 오리진은 앱 도메인+로컬 dev만.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.app_base_url, "http://localhost:3200"],
    allow_methods=["GET", "POST"],
    allow_headers=["content-type", "x-api-key"],
)
app.include_router(reports.router)
app.include_router(users.router)
app.include_router(billing.router)


@app.get("/health")
async def health():
    return {"status": "ok"}
