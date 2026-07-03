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

    # Langfuse (선택 — 키 없으면 트레이싱 자동 비활성)
    langfuse_public_key: str = ""
    langfuse_secret_key: str = ""
    langfuse_host: str = "https://us.cloud.langfuse.com"


settings = Settings()
