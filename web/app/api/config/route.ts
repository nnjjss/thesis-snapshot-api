// 런타임 컨피그(Day 6): NEXT_PUBLIC_* 빌드타임 인라인이 Railpack에서 미동작 실측 →
// 서버 런타임 env(BACKEND_URL)를 노출해 클라이언트가 기동 시 1회 조회.
// 미설정(로컬 dev)이면 null → 클라이언트는 동일 오리진 프록시(/api/backend)로 폴백.
export const dynamic = "force-dynamic";

export async function GET() {
  return Response.json({ backendUrl: process.env.BACKEND_URL ?? null });
}
