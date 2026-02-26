"use client";
import { useState, useEffect } from "react";
import { api } from "@/lib/api";
import { useSSE } from "@/hooks/useSSE";
import { formatCurrency, formatPercent, getScoreColor, formatScore } from "@/lib/utils";
import type { MarketStatus, RecommendationItem, HoldingItem } from "@/types";

export default function DashboardPage() {
  const { isConnected, lastEvent } = useSSE();
  const [marketStatus, setMarketStatus] = useState<MarketStatus | null>(null);
  const [portfolio, setPortfolio] = useState<HoldingItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [notification, setNotification] = useState<string | null>(null);

  useEffect(() => {
    api.getMarketStatus().then((data: any) => setMarketStatus(data));
    api.getPortfolio().then((data: any) => setPortfolio(data.holdings || []));
  }, []);

  // SSE 이벤트 처리
  useEffect(() => {
    if (lastEvent?.type === "sell_signals" && Array.isArray(lastEvent.data)) {
      const signals = lastEvent.data as any[];
      if (signals.length > 0) {
        setNotification(`매도 신호: ${signals.map((s: any) => s.ticker).join(", ")}`);
        setTimeout(() => setNotification(null), 10000);
      }
    }
  }, [lastEvent]);

  const totalInvested = portfolio.reduce((sum, h) => sum + h.total_invested, 0);
  const totalValue = portfolio.reduce((sum, h) => sum + (h.current_price || h.avg_buy_price) * h.quantity, 0);
  const totalPnl = totalValue - totalInvested;
  const totalPnlPct = totalInvested > 0 ? (totalPnl / totalInvested) * 100 : 0;

  return (
    <div className="space-y-8">
      {/* 알림 배너 */}
      {notification && (
        <div className="rounded-lg border border-red-500 bg-red-900/30 px-4 py-3 text-red-300">
          ⚠️ {notification}
        </div>
      )}

      {/* 헤더 */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-white">대시보드</h1>
          <p className="mt-1 text-gray-400">S&P 500 AI 기반 주식 분석 시스템</p>
        </div>
        <div className="flex items-center gap-3">
          <div className={`flex items-center gap-2 rounded-full px-4 py-2 text-sm font-medium ${
            isConnected ? "bg-green-900/40 text-green-400" : "bg-gray-800 text-gray-400"
          }`}>
            <span className={`h-2 w-2 rounded-full ${isConnected ? "bg-green-400 animate-pulse" : "bg-gray-500"}`} />
            {isConnected ? "실시간 연결" : "연결 중..."}
          </div>
          {marketStatus && (
            <div className={`rounded-full px-4 py-2 text-sm font-medium ${
              marketStatus.is_open ? "bg-blue-900/40 text-blue-400" : "bg-gray-800 text-gray-400"
            }`}>
              {marketStatus.message}
            </div>
          )}
        </div>
      </div>

      {/* 포트폴리오 요약 */}
      <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
        {[
          { label: "총 투자금액", value: formatCurrency(totalInvested) },
          { label: "현재 평가금액", value: formatCurrency(totalValue) },
          {
            label: "총 손익",
            value: formatCurrency(totalPnl),
            color: totalPnl >= 0 ? "text-green-400" : "text-red-400"
          },
          {
            label: "수익률",
            value: formatPercent(totalPnlPct),
            color: totalPnlPct >= 0 ? "text-green-400" : "text-red-400"
          },
        ].map((item) => (
          <div key={item.label} className="rounded-xl border border-gray-700 bg-gray-800/50 p-5">
            <p className="text-sm text-gray-400">{item.label}</p>
            <p className={`mt-1 text-2xl font-bold ${item.color || "text-white"}`}>
              {item.value}
            </p>
          </div>
        ))}
      </div>

      {/* 보유 종목 */}
      <div className="rounded-xl border border-gray-700 bg-gray-800/50 p-6">
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-lg font-semibold text-white">보유 종목</h2>
          <a href="/portfolio" className="text-sm text-blue-400 hover:text-blue-300">
            전체 관리 →
          </a>
        </div>
        {portfolio.length === 0 ? (
          <p className="py-8 text-center text-gray-500">보유 종목이 없습니다.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-700 text-left text-gray-400">
                  <th className="pb-3 font-medium">종목</th>
                  <th className="pb-3 font-medium text-right">수량</th>
                  <th className="pb-3 font-medium text-right">평균단가</th>
                  <th className="pb-3 font-medium text-right">현재가</th>
                  <th className="pb-3 font-medium text-right">손익</th>
                  <th className="pb-3 font-medium text-right">수익률</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-700/50">
                {portfolio.map((h) => (
                  <tr key={h.ticker} className="text-gray-300">
                    <td className="py-3">
                      <span className="font-semibold text-white">{h.ticker}</span>
                      <span className="ml-2 text-xs text-gray-500">{h.name}</span>
                    </td>
                    <td className="py-3 text-right">{h.quantity}</td>
                    <td className="py-3 text-right">{formatCurrency(h.avg_buy_price)}</td>
                    <td className="py-3 text-right">{formatCurrency(h.current_price)}</td>
                    <td className={`py-3 text-right ${h.unrealized_pnl && h.unrealized_pnl >= 0 ? "text-green-400" : "text-red-400"}`}>
                      {formatCurrency(h.unrealized_pnl)}
                    </td>
                    <td className={`py-3 text-right ${h.unrealized_pnl_pct && h.unrealized_pnl_pct >= 0 ? "text-green-400" : "text-red-400"}`}>
                      {formatPercent(h.unrealized_pnl_pct)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* 빠른 링크 */}
      <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
        {[
          {
            href: "/recommendations",
            title: "매수 추천 받기",
            desc: "S&P 500 AI 분석으로 Top 3 매수 종목 확인",
            color: "from-blue-600 to-blue-800",
          },
          {
            href: "/portfolio",
            title: "포트폴리오 관리",
            desc: "보유 종목 추가, 조회, 매도 처리",
            color: "from-purple-600 to-purple-800",
          },
          {
            href: "/sell-signals",
            title: "매도 신호 확인",
            desc: "보유 종목 매도 신호 즉시 분석",
            color: "from-orange-600 to-orange-800",
          },
        ].map((item) => (
          <a
            key={item.href}
            href={item.href}
            className={`rounded-xl bg-gradient-to-br ${item.color} p-6 transition-opacity hover:opacity-90`}
          >
            <h3 className="text-lg font-semibold text-white">{item.title}</h3>
            <p className="mt-1 text-sm text-white/70">{item.desc}</p>
          </a>
        ))}
      </div>
    </div>
  );
}
