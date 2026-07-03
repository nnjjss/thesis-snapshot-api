import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // FastAPI 백엔드 프록시 — 브라우저는 동일 오리진(/api/backend/*)만 호출해 CORS 불필요.
  // 배포 시 BACKEND_URL 환경변수로 교체 (Day 6).
  async rewrites() {
    const backend = process.env.BACKEND_URL ?? "http://127.0.0.1:8000";
    return [{ source: "/api/backend/:path*", destination: `${backend}/:path*` }];
  },
};

export default nextConfig;
