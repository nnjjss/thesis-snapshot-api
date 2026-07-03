"""Day 4: Stripe 결제 — Checkout(구독) + Webhook(플랜 전환).

키 미설정 환경(로컬/셀프호스트)에서는 checkout이 503으로 정직하게 안내하고
나머지 앱 기능은 전부 동작한다. 웹훅은 서명 검증 필수(stripe_webhook_secret).
"""
from fastapi import APIRouter, Header, HTTPException, Request
from pydantic import BaseModel, EmailStr

from app import db
from app.config import settings

router = APIRouter(prefix="/v1/billing")


class CheckoutRequest(BaseModel):
    email: EmailStr


class CheckoutResponse(BaseModel):
    url: str


def _stripe():
    """지연 임포트 + 키 주입 — 미설정이면 503 (앱 기동은 Stripe 없이도 되어야 함)."""
    if not settings.stripe_secret_key or not settings.stripe_price_id:
        raise HTTPException(status_code=503,
                            detail="Stripe 미설정 — STRIPE_SECRET_KEY/STRIPE_PRICE_ID 필요")
    import stripe
    stripe.api_key = settings.stripe_secret_key
    return stripe


@router.post("/checkout", response_model=CheckoutResponse)
async def create_checkout(req: CheckoutRequest) -> CheckoutResponse:
    stripe = _stripe()
    try:
        session = stripe.checkout.Session.create(
            mode="subscription",
            line_items=[{"price": settings.stripe_price_id, "quantity": 1}],
            customer_email=req.email.lower(),
            success_url=f"{settings.app_base_url}/?upgraded=1",
            cancel_url=f"{settings.app_base_url}/?canceled=1",
        )
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"stripe checkout failed: {e}")
    return CheckoutResponse(url=session.url)


@router.post("/webhook")
async def stripe_webhook(request: Request,
                         stripe_signature: str = Header(default="", alias="Stripe-Signature")):
    if not settings.stripe_webhook_secret:
        raise HTTPException(status_code=503, detail="Stripe webhook 미설정")
    import json

    from stripe import WebhookSignature
    payload = await request.body()
    try:
        # 서명만 stripe로 검증(위조/재전송 5분 허용오차) — 원문 바이트 그대로.
        # 데이터 접근은 원문 JSON dict로 직접: v15 StripeObject는 .get()이 없어
        # (KeyError:'get' 실측) 버전 결합을 피한다.
        WebhookSignature.verify_header(
            payload.decode("utf-8"), stripe_signature,
            settings.stripe_webhook_secret, tolerance=300)
    except Exception:
        raise HTTPException(status_code=400, detail="invalid signature")

    event = json.loads(payload)
    kind = event.get("type", "")
    obj = (event.get("data") or {}).get("object") or {}

    if kind == "checkout.session.completed":
        email = (obj.get("customer_email")
                 or (obj.get("customer_details") or {}).get("email"))
        if email:
            await db.set_user_plan(email.lower(), "pro", obj.get("customer"))
    elif kind == "customer.subscription.deleted":
        # 구독 해지 → free 강등. customer id로 이메일 역조회
        customer_id = obj.get("customer")
        if customer_id:
            row = await db.pool().fetchrow(
                "SELECT email FROM users WHERE stripe_customer_id = $1", customer_id)
            if row:
                await db.set_user_plan(row["email"], "free")
    # 그 외 이벤트는 200으로 무시(스트라이프 재전송 방지)
    return {"received": True}
