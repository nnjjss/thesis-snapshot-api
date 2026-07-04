"""환경 설정. .env 파일 또는 환경변수에서 로드."""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    anthropic_api_key: str
    database_url: str = "postgresql://thesis:thesis@localhost:5433/thesis"

    # 모델 라우팅 — 비용/품질 실험 시 env로 교체
    report_model: str = "claude-fable-5"            # 리서치 + 구조화 + 논거 평가
    prep_model: str = "claude-haiku-4-5-20251001"   # 논거 전처리 (저비용)

    cache_ttl_hours: int = 24
    max_web_searches: int = 6

    # Day 4: 인증·쿼터·Stripe
    auth_required: bool = False       # True면 /v1/reports에 X-API-Key 필수 (로컬 dev/smoke는 off)
    free_daily_limit: int = 10        # free 플랜: 최근 24h 유료 호출(캐시미스) 상한. 캐시 히트는 무제한(한계비용≈0)

    # Day 7: 공개 런치 가드
    signup_rate_limit_per_hour: int = 5   # IP당 시간당 가입 상한(이메일 무한 생성=쿼터 우회 차단)
    global_daily_paid_limit: int = 50     # 전체 서비스 24h 유료 호출(캐시미스) 상한 — 비용 폭주 최후 방어선(캐시미스 1건≈$1.6)
    stripe_secret_key: str = ""       # sk_test_... — 없으면 결제 엔드포인트 503
    stripe_price_id: str = ""         # pro 구독 Price ID (price_...)
    stripe_webhook_secret: str = ""   # whsec_... — 웹훅 서명 검증용
    app_base_url: str = "http://localhost:3200"  # checkout 성공/취소 리다이렉트 대상

    # Langfuse (선택 — 키 없으면 트레이싱 자동 비활성)
    langfuse_public_key: str = ""
    langfuse_secret_key: str = ""
    langfuse_host: str = "https://us.cloud.langfuse.com"


settings = Settings()
