// API 베이스 해석(Day 6): 프로덕션은 백엔드 직접 호출 — Next rewrites 프록시가
// 장시간(캐시미스 1~2분) 요청을 끊는 문제의 해법. 빌드타임 인라인(NEXT_PUBLIC_*)이
// Railpack에서 미동작 실측 → /api/config 런타임 조회로 전환. 로컬 dev는 프록시 폴백.
let _base: string | null = null;

export async function apiBase(): Promise<string> {
  if (_base !== null) return _base;
  try {
    const r = await fetch("/api/config");
    const j = (await r.json()) as { backendUrl: string | null };
    _base = j.backendUrl || "/api/backend";
  } catch {
    _base = "/api/backend";
  }
  return _base;
}

export async function apiUrl(path: string): Promise<string> {
  return `${await apiBase()}${path}`;
}
