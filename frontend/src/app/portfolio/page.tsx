"use client";
import { useState, useEffect } from "react";
import { api } from "@/lib/api";
import { formatCurrency, formatPercent } from "@/lib/utils";
import type { HoldingItem } from "@/types";

export default function PortfolioPage() {
  const [holdings, setHoldings] = useState<HoldingItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [buyForm, setBuyForm] = useState({ ticker: "", quantity: "", price: "", note: "" });
  const [submitting, setSubmitting] = useState(false);
  const [message, setMessage] = useState<{ type: "success" | "error"; text: string } | null>(null);

  const fetchPortfolio = async () => {
    try {
      const data = await api.getPortfolio() as any;
      setHoldings(data.holdings || []);
    } catch (e: any) {
      setMessage({ type: "error", text: e.message });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchPortfolio(); }, []);

  const handleBuy = async (e: React.FormEvent) => {
    e.preventDefault();
    const qty = parseFloat(buyForm.quantity);
    const price = parseFloat(buyForm.price);
    if (!buyForm.ticker.trim()) {
      setMessage({ type: "error", text: "티커를 입력하세요." });
      return;
    }
    if (!buyForm.quantity || isNaN(qty) || qty <= 0) {
      setMessage({ type: "error", text: "수량은 0보다 커야 합니다." });
      return;
    }
    if (!buyForm.price || isNaN(price) || price <= 0) {
      setMessage({ type: "error", text: "매수가는 0보다 커야 합니다." });
      return;
    }
    setSubmitting(true);
    try {
      await api.buyStock({
        ticker: buyForm.ticker.toUpperCase(),
        quantity: qty,
        price: price,
        note: buyForm.note || undefined,
      });
      setMessage({ type: "success", text: `${buyForm.ticker.toUpperCase()} 매수 완료` });
      setBuyForm({ ticker: "", quantity: "", price: "", note: "" });
      fetchPortfolio();
    } catch (e: any) {
      setMessage({ type: "error", text: e.message });
    } finally {
      setSubmitting(false);
    }
  };

  const handleSell = async (ticker: string) => {
    if (!confirm(`${ticker}를 매도하시겠습니까?`)) return;
    try {
      const result = await api.sellStock(ticker) as any;
      setMessage({ type: "success", text: `${ticker} 매도 완료. 실현손익: ${formatCurrency(result.realized_pnl)}` });
      fetchPortfolio();
    } catch (e: any) {
      setMessage({ type: "error", text: e.message });
    }
  };

  const totalInvested = holdings.reduce((sum, h) => sum + h.total_invested, 0);
  const totalValue = holdings.reduce((sum, h) => sum + (h.current_price || h.avg_buy_price) * h.quantity, 0);

  return (
    <div className="space-y-8">
      <h1 className="text-3xl font-bold text-white">포트폴리오 관리</h1>

      {message && (
        <div className={`rounded-xl border px-5 py-4 ${
          message.type === "success"
            ? "border-green-700 bg-green-900/20 text-green-300"
            : "border-red-700 bg-red-900/20 text-red-300"
        }`}>
          {message.text}
          <button className="ml-4 text-xs opacity-60 hover:opacity-100" onClick={() => setMessage(null)}>닫기</button>
        </div>
      )}

      {/* 요약 */}
      <div className="grid grid-cols-3 gap-4">
        <div className="rounded-xl border border-gray-700 bg-gray-800/50 p-5">
          <p className="text-sm text-gray-400">총 투자금액</p>
          <p className="mt-1 text-2xl font-bold text-white">{formatCurrency(totalInvested)}</p>
        </div>
        <div className="rounded-xl border border-gray-700 bg-gray-800/50 p-5">
          <p className="text-sm text-gray-400">평가금액</p>
          <p className="mt-1 text-2xl font-bold text-white">{formatCurrency(totalValue)}</p>
        </div>
        <div className="rounded-xl border border-gray-700 bg-gray-800/50 p-5">
          <p className="text-sm text-gray-400">평가손익</p>
          <p className={`mt-1 text-2xl font-bold ${totalValue - totalInvested >= 0 ? "text-green-400" : "text-red-400"}`}>
            {formatCurrency(totalValue - totalInvested)}
          </p>
        </div>
      </div>

      {/* 매수 폼 */}
      <div className="rounded-xl border border-gray-700 bg-gray-800/50 p-6">
        <h2 className="mb-4 text-lg font-semibold text-white">종목 매수</h2>
        <form onSubmit={handleBuy} className="grid grid-cols-2 gap-4 md:grid-cols-5">
          {[
            { key: "ticker", label: "티커 (예: AAPL)", type: "text", placeholder: "AAPL" },
            { key: "quantity", label: "수량", type: "number", placeholder: "10" },
            { key: "price", label: "매수가 ($)", type: "number", placeholder: "150.00" },
            { key: "note", label: "메모 (선택)", type: "text", placeholder: "추천 매수" },
          ].map((field) => (
            <div key={field.key}>
              <label className="mb-1 block text-xs text-gray-400">{field.label}</label>
              <input
                type={field.type}
                placeholder={field.placeholder}
                value={buyForm[field.key as keyof typeof buyForm]}
                onChange={(e) => setBuyForm({ ...buyForm, [field.key]: e.target.value })}
                className="w-full rounded-lg border border-gray-600 bg-gray-700 px-3 py-2 text-sm text-white
                           placeholder-gray-500 focus:border-blue-500 focus:outline-none"
                step={field.type === "number" ? "any" : undefined}
              />
            </div>
          ))}
          <div className="flex items-end">
            <button
              type="submit"
              disabled={submitting}
              className="w-full rounded-lg bg-blue-600 py-2 text-sm font-semibold text-white
                         hover:bg-blue-500 disabled:opacity-50"
            >
              {submitting ? "처리 중..." : "매수"}
            </button>
          </div>
        </form>
      </div>

      {/* 보유 종목 목록 */}
      <div className="rounded-xl border border-gray-700 bg-gray-800/50 p-6">
        <h2 className="mb-4 text-lg font-semibold text-white">
          보유 종목 <span className="text-sm font-normal text-gray-400">({holdings.length}개)</span>
        </h2>
        {loading ? (
          <p className="py-8 text-center text-gray-500">불러오는 중...</p>
        ) : holdings.length === 0 ? (
          <p className="py-8 text-center text-gray-500">보유 종목이 없습니다.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-700 text-left text-gray-400">
                  {["종목", "수량", "평균단가", "현재가", "평가금액", "손익", "수익률", ""].map((h) => (
                    <th key={h} className="pb-3 font-medium text-right first:text-left">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-700/50">
                {holdings.map((h) => (
                  <tr key={h.ticker} className="text-gray-300">
                    <td className="py-3">
                      <span className="font-bold text-white">{h.ticker}</span>
                      <span className="ml-2 text-xs text-gray-500">{h.name}</span>
                    </td>
                    <td className="py-3 text-right">{h.quantity}</td>
                    <td className="py-3 text-right">{formatCurrency(h.avg_buy_price)}</td>
                    <td className="py-3 text-right">{formatCurrency(h.current_price)}</td>
                    <td className="py-3 text-right">{formatCurrency((h.current_price || h.avg_buy_price) * h.quantity)}</td>
                    <td className={`py-3 text-right ${(h.unrealized_pnl || 0) >= 0 ? "text-green-400" : "text-red-400"}`}>
                      {formatCurrency(h.unrealized_pnl)}
                    </td>
                    <td className={`py-3 text-right ${(h.unrealized_pnl_pct || 0) >= 0 ? "text-green-400" : "text-red-400"}`}>
                      {formatPercent(h.unrealized_pnl_pct)}
                    </td>
                    <td className="py-3 text-right">
                      <button
                        onClick={() => handleSell(h.ticker)}
                        className="rounded-lg border border-red-700 px-3 py-1 text-xs text-red-400
                                   hover:bg-red-900/30 transition-colors"
                      >
                        매도
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
