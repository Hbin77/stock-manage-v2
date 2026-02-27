import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // 프로덕션 빌드 최적화 (NAS Docker용)
  output: process.env.BUILD_STANDALONE === "true" ? "standalone" : undefined,

  async rewrites() {
    // 프로덕션(NAS): nginx가 /api/* 처리 → rewrite 불필요
    if (process.env.NODE_ENV === "production") return [];
    // 로컬 개발: Next.js dev 서버에서 백엔드로 프록시
    const backendUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
    return [
      {
        source: "/api/:path*",
        destination: `${backendUrl}/api/:path*`,
      },
    ];
  },
};

export default nextConfig;
