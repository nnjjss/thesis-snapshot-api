"""Day 4: 가입 — 이메일 → API 키 발급 (free 플랜). Day 7: IP 레이트리밋."""
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, EmailStr, Field

from app import auth, db

router = APIRouter(prefix="/v1")


class SignupRequest(BaseModel):
    email: EmailStr


class SignupResponse(BaseModel):
    email: str
    plan: str
    api_key: str = Field(description="이번 응답에서만 노출 — 분실 시 재발급 필요")


@router.post("/signup", response_model=SignupResponse)
async def signup(req: SignupRequest, request: Request) -> SignupResponse:
    # Day 7: IP 레이트리밋 — Railway 뒤라 클라이언트 IP는 X-Forwarded-For 첫 값
    ip = (request.headers.get("x-forwarded-for") or "").split(",")[0].strip() \
        or (request.client.host if request.client else "unknown")
    auth.check_signup_rate(ip)
    key, key_hash = auth.new_api_key()
    user = await db.create_user(req.email.lower(), key_hash)
    if user is None:
        raise HTTPException(status_code=409, detail="이미 가입된 이메일입니다")
    return SignupResponse(email=user["email"], plan=user["plan"], api_key=key)
