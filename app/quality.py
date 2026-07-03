"""Day 5: 결정론 품질 평가 — LLM 없이 항상 실행되는 기계 검사.

두 축:
1. compliance — CLAUDE.md 절대 규칙("매수/매도/목표가 표현 = 버그로 취급")의 기계화.
   고정밀 패턴만 사용(오탐 최소화): '순매수/매수세' 같은 서술적 용법은 제외하고
   지시/권유 형태만 잡는다. 위반 0 = 1.0.
2. grounding — 리포트의 source_url이 실제 리서치 노트에 존재하는 URL인지.
   구조화 단계가 노트에 없는 출처를 지어내면(환각) 여기서 잡힌다. 전부 실재 = 1.0.

점수는 quality_scores 테이블에 영속(+Langfuse 활성 시 score로도 전송 — llm/tracing.py).
"""
from __future__ import annotations

import json
import re

from app import db

# 지시/권유 고정밀 패턴 — 서술 용법(순매수, 매수세, 매도 압력 등)은 잡지 않는다.
# 새 패턴 추가 시 반드시 tests의 무고(억울한 통과 문장) 케이스를 함께 늘릴 것.
COMPLIANCE_PATTERNS: list[tuple[str, str]] = [
    ("목표가", r"목표가|목표 주가|적정 주가|적정주가"),
    ("매수 권유", r"매수\s*(추천|권유|의견)|매수하(세요|시오|라)|지금\s*매수|적극\s*매수"),
    ("매도 권유", r"매도\s*(추천|권유|의견)|매도하(세요|시오|라)|지금\s*매도|전량\s*매도\s*권"),
    ("직접 지시", r"사세요|파세요|사라\b|팔아라"),
    ("수익 보장", r"수익(을|이)?\s*보장|반드시\s*(오른다|상승한다)|확실히\s*(오른다|상승)"),
]

_URL_RE = re.compile(r"https?://[^\s)>\]\"']+")


def check_compliance(text: str) -> tuple[float, list[dict]]:
    """(score, violations) — 위반 0건이면 1.0, 있으면 0.0 (등급 아닌 게이트 성격)."""
    violations = []
    for label, pattern in COMPLIANCE_PATTERNS:
        for m in re.finditer(pattern, text):
            start = max(0, m.start() - 20)
            violations.append({"rule": label, "match": m.group(0),
                               "context": text[start:m.end() + 20]})
    return (0.0 if violations else 1.0), violations


def check_grounding(report_dict: dict, research_notes: str) -> tuple[float, list[dict]]:
    """리포트 case들의 source_url이 리서치 노트의 URL 집합에 실재하는가.

    비교는 정규화(꼬리 구두점 제거) 후 정확 일치 — 부분 일치는 도메인만 같아도
    통과시키는 구멍이라 쓰지 않는다.
    """
    def norm(u: str) -> str:
        return u.rstrip(".,;:)]}\"'").rstrip("/")

    note_urls = {norm(u) for u in _URL_RE.findall(research_notes)}
    missing = []
    total = 0
    for side in ("bull_case", "bear_case"):
        for i, case in enumerate(report_dict.get(side, [])):
            total += 1
            url = norm(case.get("source_url", ""))
            if url not in note_urls:
                missing.append({"side": side, "index": i, "url": case.get("source_url", "")})
    if total == 0:
        return 0.0, [{"side": "-", "index": -1, "url": "(케이스 없음)"}]
    return (total - len(missing)) / total, missing


async def score_report(base_report_id, report_dict: dict, research_notes: str) -> dict:
    """리포트 생성 직후 호출 — 두 축 채점·영속(+Langfuse score). 반환: {compliance, grounding}."""
    from app.llm import tracing  # 순환 방지 지연 임포트(quality←service←llm)
    full_text = json.dumps(report_dict, ensure_ascii=False)
    c_score, c_viol = check_compliance(full_text)
    g_score, g_missing = check_grounding(report_dict, research_notes)
    await db.insert_quality_score(base_report_id, "report_compliance", c_score, c_viol)
    await db.insert_quality_score(base_report_id, "report_grounding", g_score, g_missing)
    sid = str(base_report_id)
    tracing.score("report_compliance", c_score, sid,
                  f"{len(c_viol)}건 위반" if c_viol else "")
    tracing.score("report_grounding", g_score, sid,
                  f"{len(g_missing)}건 미실재" if g_missing else "")
    return {"compliance": c_score, "grounding": g_score}


async def score_eval(base_report_id, eval_dict: dict) -> dict:
    """논거 평가 직후 호출 — 평가문(reasoning 등)의 컴플라이언스만(출처는 리포트 소관)."""
    from app.llm import tracing
    full_text = json.dumps(eval_dict, ensure_ascii=False)
    c_score, c_viol = check_compliance(full_text)
    await db.insert_quality_score(base_report_id, "eval_compliance", c_score, c_viol)
    tracing.score("eval_compliance", c_score, str(base_report_id),
                  f"{len(c_viol)}건 위반" if c_viol else "")
    return {"compliance": c_score}
