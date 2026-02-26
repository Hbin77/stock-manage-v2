"use client";
import { useState, useEffect } from "react";
import { api } from "@/lib/api";
import { formatPercent, formatScore, getScoreColor } from "@/lib/utils";
import { useSSE } from "@/hooks/useSSE";

const SIGNAL_TYPE_LABEL: Record<string, string> = {
  SELL: "점수 미달",
  STOP_LOSS: "손절매",
  TAKE_PROFIT: "익절매",
  TIME_STOP: "타임스톱",
  TRAILING_STOP: "트레일링스톱",
  BREAKEVEN_STOP: "브레이크이븐",
};

const SIGNAL_TYPE_COLOR: Record<string, string> = {
  SELL: "border-orange-600 bg-orange-900/20",
  STOP_LOSS: "border-red-600 bg-red-900/20",
  TAKE_PROFIT: "border-green-600 bg-green-900/20",
  TIME_STOP: "border-yellow-600 bg-yellow-900/20",
  TRAILING_STOP: "border-blue-600 bg-blue-900/20",
  BREAKEVEN_STOP: "border-purple-600 bg-purple-900/20",
};

const SIGNAL_BADGE_COLOR: Record<string, string> = {
  SELL: "bg-orange-700 text-white",
  STOP_LOSS: "bg-red-700 text-white",
  TAKE_PROFIT: "bg-green-700 text-white",
  TIME_STOP: "bg-yellow-700 text-white",
  TRAILING_STOP: "bg-blue-700 text-white",
  BREAKEVEN_STOP: "bg-purple-700 text-white",
};

interface SellSignal {
  ticker: string;
  name: string;
  signal_type: string;
  signal: string;
  combined_score: number;
  tech_score: number;
  news_sell_score: number;
  pnl_pct: number | null;
  current_price: number | null;
  avg_buy_price: number;
  peak_price?: number | null;
  trailing_stop_price?: number | null;
  trading_days_held?: number;
  is_scalp_trade?: boolean;
  reasoning: string;
  tech_signals?: string[];
  news_action?: string;
  news_risk_factors?: string[];
  news_reasoning?: string;
}

interface HoldAnalysis {
  ticker: string;
  name: string;
  decision: "HOLD";
  strategy: "SCALP" | "SWING";
  pnl_pct: number;
  current_price: number | null;
  avg_buy_price: number;
  tech_score: number;
  news_sell_score: number;
  combined_score?: number;
  news_action?: string;
  news_reasoning?: string;
  hold_reasons: string[];
  tech_signals?: string[];
  peak_price?: number | null;
  trailing_stop_price?: number | null;
  trailing_stop_active?: boolean;
  breakeven_locked?: boolean;
  trading_days_held?: number;
}

export default function SellSignalsPage() {
  const { isConnected, lastEvent } = useSSE();
  const [signals, setSignals] = useState<SellSignal[]>([]);
  const [holdAnalysis, setHoldAnalysis] = useState<HoldAnalysis[]>([]);
  const [history, setHistory] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [lastAnalyzed, setLastAnalyzed] = useState<string | null>(null);
  const [analyzed, setAnalyzed] = useState(false);

  // SSE 자동 업데이트
  useEffect(() => {
    if (lastEvent?.type === "sell_signals" && Array.isArray(lastEvent.data)) {
      setSignals(lastEvent.data as SellSignal[]);
      setLastAnalyzed(new Date().toLocaleTimeString("ko-KR"));
      setAnalyzed(true);
    }
  }, [lastEvent]);

  // 초기 이력 로드
  useEffect(() => {
    api.getSellSignalHistory(20).then((data: any) => setHistory(data.signals || []));
  }, []);

  const analyze = async () => {
    setLoading(true);
    try {
      const result = await api.getSellSignals() as any;
      setSignals(result.signals || []);
      setHoldAnalysis(result.hold_analysis || []);
      setLastAnalyzed(new Date().toLocaleTimeString("ko-KR"));
      setAnalyzed(true);
      api.getSellSignalHistory(20).then((data: any) => setHistory(data.signals || []));
    } catch (e: any) {
      alert(e.message);
    } finally {
      setLoading(false);
    }
  };

  const allItems = signals.length + holdAnalysis.length;

  return (
    <div className="space-y-8">
      {/* 헤더 */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-white">매도 분석</h1>
          <p className="mt-1 text-gray-400">
            포트폴리오 종목별 보유/매도 판단 및 이유 (10분마다 자동 실행)
          </p>
        </div>
        <div className="flex items-center gap-4">
          <div className={`flex items-center gap-2 text-sm ${isConnected ? "text-green-400" : "text-gray-500"}`}>
            <span className={`h-2 w-2 rounded-full ${isConnected ? "bg-green-400 animate-pulse" : "bg-gray-500"}`} />
            {isConnected ? "자동 감지 중" : "연결 끊김"}
          </div>
          <button
            onClick={analyze}
            disabled={loading}
            className="rounded-xl bg-orange-600 px-5 py-2.5 font-semibold text-white
                       hover:bg-orange-500 disabled:opacity-50 transition-colors"
          >
            {loading ? "분석 중..." : "즉시 분석"}
          </button>
        </div>
      </div>

      {lastAnalyzed && (
        <div className="flex items-center gap-2 text-sm text-gray-500">
          <span>마지막 분석: {lastAnalyzed}</span>
          {allItems > 0 && (
            <span className="text-gray-600">
              · 매도 {signals.length}건 / 보유 {holdAnalysis.length}건
            </span>
          )}
        </div>
      )}

      {/* 미분석 상태 */}
      {!analyzed && !loading && (
        <div className="rounded-xl border border-dashed border-gray-700 p-12 text-center">
          <p className="text-gray-400 font-medium">즉시 분석 버튼을 눌러 포트폴리오를 분석하세요</p>
          <p className="mt-1 text-sm text-gray-600">각 종목의 보유 이유 또는 매도 이유를 확인할 수 있습니다.</p>
        </div>
      )}

      {/* 매도 신호 섹션 */}
      {analyzed && (
        <>
          {signals.length > 0 && (
            <div>
              <h2 className="mb-4 flex items-center gap-2 text-lg font-semibold text-white">
                <span className="h-2 w-2 rounded-full bg-red-400 animate-pulse" />
                매도 신호 ({signals.length}건)
              </h2>
              <div className="space-y-4">
                {signals.map((signal) => (
                  <SellSignalCard key={signal.ticker} signal={signal} />
                ))}
              </div>
            </div>
          )}

          {/* 보유 분석 섹션 */}
          {holdAnalysis.length > 0 && (
            <div>
              <h2 className="mb-4 flex items-center gap-2 text-lg font-semibold text-white">
                <span className="h-2 w-2 rounded-full bg-blue-400" />
                보유 유지 ({holdAnalysis.length}건)
              </h2>
              <div className="space-y-4">
                {holdAnalysis.map((item) => (
                  <HoldCard key={item.ticker} item={item} />
                ))}
              </div>
            </div>
          )}

          {/* 보유 종목 없음 */}
          {signals.length === 0 && holdAnalysis.length === 0 && (
            <div className="rounded-xl border border-dashed border-gray-700 p-12 text-center">
              <p className="text-gray-500">보유 종목이 없거나 분석 데이터가 없습니다.</p>
              <p className="mt-1 text-sm text-gray-600">포트폴리오 탭에서 종목을 추가해 보세요.</p>
            </div>
          )}
        </>
      )}

      {/* 이력 */}
      {history.length > 0 && (
        <div>
          <h2 className="mb-4 text-lg font-semibold text-white">최근 매도 신호 이력</h2>
          <div className="overflow-x-auto rounded-xl border border-gray-700">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-700 bg-gray-800/80 text-left text-gray-400">
                  {["종목", "신호 유형", "통합 점수", "수익률", "사유", "시간"].map((h) => (
                    <th key={h} className="px-4 py-3 font-medium">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-700/50">
                {history.map((s) => (
                  <tr key={s.id} className="text-gray-300 hover:bg-gray-800/30">
                    <td className="px-4 py-3 font-semibold text-white">{s.ticker}</td>
                    <td className="px-4 py-3">
                      <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${SIGNAL_BADGE_COLOR[s.signal_type] || "bg-gray-700 text-white"}`}>
                        {SIGNAL_TYPE_LABEL[s.signal_type] || s.signal_type}
                      </span>
                    </td>
                    <td className={`px-4 py-3 ${getScoreColor(s.combined_score)}`}>{formatScore(s.combined_score)}점</td>
                    <td className={`px-4 py-3 ${(s.pnl_pct || 0) >= 0 ? "text-green-400" : "text-red-400"}`}>
                      {s.pnl_pct != null ? formatPercent(s.pnl_pct) : "-"}
                    </td>
                    <td className="px-4 py-3 text-gray-400 max-w-xs truncate">{s.reasoning}</td>
                    <td className="px-4 py-3 text-gray-500 text-xs">
                      {new Date(s.signal_at).toLocaleString("ko-KR")}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}

function SellSignalCard({ signal }: { signal: SellSignal }) {
  const borderColor = SIGNAL_TYPE_COLOR[signal.signal_type] || "border-gray-700 bg-gray-800/30";
  const badgeColor = SIGNAL_BADGE_COLOR[signal.signal_type] || "bg-gray-700 text-white";

  return (
    <div className={`rounded-xl border p-5 ${borderColor}`}>
      {/* 헤더 */}
      <div className="flex items-start justify-between">
        <div>
          <div className="flex items-center gap-3 flex-wrap">
            <span className="text-xl font-bold text-white">{signal.ticker}</span>
            <span className={`rounded-full px-3 py-1 text-xs font-semibold ${badgeColor}`}>
              {SIGNAL_TYPE_LABEL[signal.signal_type] || signal.signal_type}
            </span>
            {signal.is_scalp_trade && (
              <span className="rounded-full bg-indigo-800 px-2 py-0.5 text-xs text-indigo-200">단타</span>
            )}
          </div>
          <p className="mt-1 text-sm text-gray-400">{signal.name}</p>
        </div>
        <div className="text-right shrink-0">
          {signal.pnl_pct != null && (
            <p className={`text-2xl font-bold ${signal.pnl_pct >= 0 ? "text-green-400" : "text-red-400"}`}>
              {formatPercent(signal.pnl_pct)}
            </p>
          )}
          <p className="text-xs text-gray-500 mt-0.5">
            {signal.avg_buy_price != null ? `평균가 $${signal.avg_buy_price.toFixed(2)}` : ""}
            {signal.current_price != null ? ` → $${signal.current_price.toFixed(2)}` : ""}
          </p>
        </div>
      </div>

      {/* 점수 바 */}
      <div className="mt-4 grid grid-cols-3 gap-3 text-sm">
        <div className="rounded-lg bg-gray-900/50 px-3 py-2">
          <p className="text-gray-500 text-xs">통합점수</p>
          <p className={`text-lg font-bold ${getScoreColor(signal.combined_score)}`}>{formatScore(signal.combined_score)}점</p>
        </div>
        <div className="rounded-lg bg-gray-900/50 px-3 py-2">
          <p className="text-gray-500 text-xs">기술점수</p>
          <p className={`text-lg font-bold ${getScoreColor(signal.tech_score)}`}>{formatScore(signal.tech_score)}점</p>
        </div>
        <div className="rounded-lg bg-gray-900/50 px-3 py-2">
          <p className="text-gray-500 text-xs">뉴스매도압력</p>
          <p className={`text-lg font-bold ${signal.news_sell_score >= 60 ? "text-red-400" : signal.news_sell_score >= 40 ? "text-yellow-400" : "text-green-400"}`}>
            {signal.news_sell_score?.toFixed(0)}점
          </p>
        </div>
      </div>

      {/* 단타 상태 */}
      {signal.is_scalp_trade && (
        <div className="mt-3 grid grid-cols-3 gap-2 text-xs text-gray-400">
          {signal.peak_price != null && (
            <span>고점 ${signal.peak_price.toFixed(2)}</span>
          )}
          {signal.trailing_stop_price != null && (
            <span>트레일 ${signal.trailing_stop_price.toFixed(2)}</span>
          )}
          {signal.trading_days_held != null && (
            <span>보유 {signal.trading_days_held}거래일</span>
          )}
        </div>
      )}

      {/* 매도 이유 */}
      <div className="mt-3 rounded-lg bg-gray-900/60 px-4 py-3">
        <p className="text-xs font-semibold text-red-400 mb-1">매도 이유</p>
        <p className="text-sm text-gray-300">{signal.reasoning}</p>
      </div>

      {/* 기술적 신호 */}
      {signal.tech_signals && signal.tech_signals.length > 0 && (
        <div className="mt-2 flex flex-wrap gap-2">
          {signal.tech_signals.map((s, i) => (
            <span key={i} className="rounded-full bg-orange-900/40 border border-orange-700/50 px-2 py-0.5 text-xs text-orange-300">
              {s}
            </span>
          ))}
        </div>
      )}

      {/* 뉴스 */}
      {signal.news_reasoning && (
        <p className="mt-2 text-xs text-gray-500 italic">{signal.news_reasoning}</p>
      )}
    </div>
  );
}

function HoldCard({ item }: { item: HoldAnalysis }) {
  return (
    <div className="rounded-xl border border-gray-700 bg-gray-800/20 p-5">
      {/* 헤더 */}
      <div className="flex items-start justify-between">
        <div>
          <div className="flex items-center gap-3 flex-wrap">
            <span className="text-xl font-bold text-white">{item.ticker}</span>
            <span className="rounded-full bg-gray-700 px-3 py-1 text-xs font-semibold text-gray-300">
              보유유지
            </span>
            <span className={`rounded-full px-2 py-0.5 text-xs ${item.strategy === "SCALP" ? "bg-indigo-800 text-indigo-200" : "bg-teal-800 text-teal-200"}`}>
              {item.strategy === "SCALP" ? "단타" : "스윙"}
            </span>
          </div>
          <p className="mt-1 text-sm text-gray-400">{item.name}</p>
        </div>
        <div className="text-right shrink-0">
          <p className={`text-2xl font-bold ${item.pnl_pct >= 0 ? "text-green-400" : "text-red-400"}`}>
            {formatPercent(item.pnl_pct)}
          </p>
          <p className="text-xs text-gray-500 mt-0.5">
            평균가 ${item.avg_buy_price.toFixed(2)}
            {item.current_price != null ? ` → $${item.current_price.toFixed(2)}` : ""}
          </p>
        </div>
      </div>

      {/* 점수 */}
      <div className="mt-4 grid grid-cols-3 gap-3 text-sm">
        {item.combined_score != null && (
          <div className="rounded-lg bg-gray-900/50 px-3 py-2">
            <p className="text-gray-500 text-xs">통합점수</p>
            <p className={`text-lg font-bold ${getScoreColor(item.combined_score)}`}>{formatScore(item.combined_score)}점</p>
          </div>
        )}
        <div className="rounded-lg bg-gray-900/50 px-3 py-2">
          <p className="text-gray-500 text-xs">기술점수</p>
          <p className={`text-lg font-bold ${getScoreColor(item.tech_score)}`}>{formatScore(item.tech_score)}점</p>
        </div>
        <div className="rounded-lg bg-gray-900/50 px-3 py-2">
          <p className="text-gray-500 text-xs">뉴스매도압력</p>
          <p className={`text-lg font-bold ${item.news_sell_score >= 60 ? "text-red-400" : item.news_sell_score >= 40 ? "text-yellow-400" : "text-green-400"}`}>
            {item.news_sell_score?.toFixed(0)}점
          </p>
        </div>
      </div>

      {/* 단타 상태 정보 */}
      {item.strategy === "SCALP" && (
        <div className="mt-3 grid grid-cols-4 gap-2 text-xs">
          {item.peak_price != null && (
            <div className="rounded bg-gray-900/50 px-2 py-1">
              <p className="text-gray-500">고점</p>
              <p className="text-white font-medium">${item.peak_price.toFixed(2)}</p>
            </div>
          )}
          {item.trailing_stop_price != null && (
            <div className="rounded bg-blue-900/30 px-2 py-1">
              <p className="text-blue-400">트레일스톱</p>
              <p className="text-white font-medium">${item.trailing_stop_price.toFixed(2)}</p>
            </div>
          )}
          {item.breakeven_locked && (
            <div className="rounded bg-purple-900/30 px-2 py-1">
              <p className="text-purple-400">브레이크이븐</p>
              <p className="text-white font-medium">활성화</p>
            </div>
          )}
          {item.trading_days_held != null && (
            <div className="rounded bg-gray-900/50 px-2 py-1">
              <p className="text-gray-500">보유</p>
              <p className="text-white font-medium">{item.trading_days_held}거래일</p>
            </div>
          )}
        </div>
      )}

      {/* 보유 이유 목록 */}
      <div className="mt-3 rounded-lg bg-gray-900/60 px-4 py-3">
        <p className="text-xs font-semibold text-blue-400 mb-2">보유 이유</p>
        <ul className="space-y-1">
          {item.hold_reasons.map((reason, i) => (
            <li key={i} className="flex items-start gap-2 text-sm text-gray-300">
              <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-blue-500" />
              {reason}
            </li>
          ))}
        </ul>
      </div>

      {/* 기술적 경고 신호 */}
      {item.tech_signals && item.tech_signals.length > 0 && (
        <div className="mt-2">
          <p className="text-xs text-gray-500 mb-1">기술적 경고</p>
          <div className="flex flex-wrap gap-2">
            {item.tech_signals.map((s, i) => (
              <span key={i} className="rounded-full bg-gray-800 border border-gray-600 px-2 py-0.5 text-xs text-gray-400">
                {s}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* 뉴스 요약 */}
      {item.news_action && (
        <p className="mt-2 text-xs text-gray-500">
          뉴스 판단: <span className="text-gray-400">{item.news_action}</span>
          {item.news_reasoning && ` · ${item.news_reasoning}`}
        </p>
      )}
    </div>
  );
}
