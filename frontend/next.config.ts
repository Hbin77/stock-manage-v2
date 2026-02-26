import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // 프로덕션 빌드 최적화 (NAS Docker용)
  output: process.env.BUILD_STANDALONE === "true" ? "standalone" : undefined,

  async rewrites() {
    const apiUrl = process.env.NEXT_PUBLIC_API_URL;
    // NEXT_PUBLIC_API_URL이 비어있으면 nginx가 /api/* 라우팅 담당 → rewrite 불필요
    if (!apiUrl) return [];
    return [
      {
        source: "/api/:path*",
        destination: `${apiUrl}/api/:path*`,
      },
    ];
  },
};

export default nextConfig;
