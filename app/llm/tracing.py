"""Day 5: Langfuse 트레이싱 — 키 없으면 완전 no-op, 있어도 요청 경로를 절대 막지 않는다.

실측(langfuse 4.13): 익스포트는 OTel 배치 백그라운드라 죽은 호스트/가짜 키여도
요청 경로에 예외가 전파되지 않음. 그래도 생성/기록 호출부는 전부 방어적으로 감싼다.
"""
from __future__ import annotations

from typing import Optional

from app.config import settings

_client = None
_init_done = False


def _get():
    """지연 싱글톤 — 키 미설정이면 None(트레이싱 비활성)."""
    global _client, _init_done
    if _init_done:
        return _client
    _init_done = True
    if not (settings.langfuse_public_key and settings.langfuse_secret_key):
        return None
    try:
        from langfuse import Langfuse
        _client = Langfuse(public_key=settings.langfuse_public_key,
                           secret_key=settings.langfuse_secret_key,
                           host=settings.langfuse_host)
    except Exception:
        _client = None  # 트레이싱은 관측일 뿐 — 초기화 실패가 앱을 막지 않는다
    return _client


class Gen:
    """LLM 호출 1건 = generation 관측 1건. 사용법: g = gen(...); ...; g.done(result)"""

    def __init__(self, name: str, model: str, input_summary: str):
        self._obs = None
        lf = _get()
        if lf is None:
            return
        try:
            self._obs = lf.start_observation(
                name=name, as_type="generation",
                input=input_summary, metadata={"model": model})
        except Exception:
            self._obs = None

    def done(self, output_summary: str, input_tokens: int, output_tokens: int,
             extra: Optional[dict] = None) -> None:
        if self._obs is None:
            return
        try:
            self._obs.update(output=output_summary,
                             usage_details={"input": input_tokens, "output": output_tokens},
                             metadata=extra or {})
            self._obs.end()
        except Exception:
            pass


def gen(name: str, model: str, input_summary: str) -> Gen:
    return Gen(name, model, input_summary)


def score(name: str, value: float, session_id: str, comment: str = "") -> None:
    """품질 점수 전송 — session_id=base_report_id로 리포트 단위 그룹핑."""
    lf = _get()
    if lf is None:
        return
    try:
        lf.create_score(name=name, value=value, session_id=session_id,
                        comment=comment or None)
    except Exception:
        pass
