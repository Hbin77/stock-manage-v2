import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "주식 추천 시스템",
  description: "S&P 500 AI 기반 주식 매수/매도 추천 및 포트폴리오 관리",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="ko">
      <body className="min-h-screen bg-gray-950 text-gray-100">
        <nav className="border-b border-gray-800 bg-gray-900 px-6 py-4">
          <div className="mx-auto flex max-w-7xl items-center justify-between">
            <a href="/" className="text-xl font-bold text-blue-400">
              주식 추천 시스템
            </a>
            <div className="flex gap-6 text-sm">
              <a href="/" className="text-gray-300 hover:text-white transition-colors">
                대시보드
              </a>
              <a href="/recommendations" className="text-gray-300 hover:text-white transition-colors">
                매수 추천
              </a>
              <a href="/portfolio" className="text-gray-300 hover:text-white transition-colors">
                포트폴리오
              </a>
              <a href="/sell-signals" className="text-gray-300 hover:text-white transition-colors">
                매도 신호
              </a>
            </div>
          </div>
        </nav>
        <main className="mx-auto max-w-7xl px-6 py-8">
          {children}
        </main>
      </body>
    </html>
  );
}
