"use client";
import { useState, useEffect } from "react";
import { api } from "@/lib/api";
import { formatScore, getScoreColor, getScoreBgColor, getSentimentLabel } from "@/lib/utils";
import type { RecommendationResponse, RecommendationItem } from "@/types";

interface TickerData {
  total: number;
  sp500_count: number;
  extra_count: number;
  sp500_tickers: string[];
  extra_groups: Record<string, string[]>;
}

const GROUP_COLORS: Record<string, string> = {
  "NASDAQ 100": "bg-purple-900/40 text-purple-300 border-purple-700/50",
  "AI/클라우드/사이버보안": "bg-blue-900/40 text-blue-300 border-blue-700/50",
  "핀테크/크립토": "bg-yellow-900/40 text-yellow-300 border-yellow-700/50",
  "미래기술": "bg-green-900/40 text-green-300 border-green-700/50",
  "글로벌 대형주": "bg-red-900/40 text-red-300 border-red-700/50",
};

function TickerPanel() {
  const [data, setData] = useState<TickerData | null>(null);
  const [open, setOpen] = useState(false);
  const [search, setSearch] = useState("");

  useEffect(() => {
    api.getTickers().then((d) => setData(d as TickerData)).catch(() => {});
  }, []);

  const filtered = search.trim().toUpperCase();
  const matchesSP500 = data?.sp500_tickers.filter((t) =>
    !filtered || t.includes(filtered)
  ) ?? [];
  const matchedGroups = data
    ? Object.entries(data.extra_groups).map(([name, tickers]) => ({
        name,
        tickers: tickers.filter((t) => !filtered || t.includes(filtered)),
      })).filter((g) => g.tickers.length > 0)
    : [];

  return (
    <div className="rounded-xl border border-gray-700 bg-gray-800/30">
      <button
        onClick={() => setOpen((v) => !v)}
        className="flex w-full items-center justify-between px-5 py-4 text-left"
      >
        <div className="flex items-center gap-3">
          <span className="font-semibold text-white">분석 대상 종목</span>
          {data && (
            <span className="rounded-full bg-gray-700 px-2.5 py-0.5 text-xs text-gray-300">
              총 {data.total}개 (S&P500 {data.sp500_count} + 추가 {data.extra_count})
            </span>
          )}
        </div>
        <svg
          className={`h-5 w-5 text-gray-400 transition-transform ${open ? "rotate-180" : ""}`}
          fill="none" viewBox="0 0 24 24" stroke="currentColor"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
      </button>

      {open && data && (
        <div className="border-t border-gray-700 px-5 pb-5 pt-4 space-y-4">
          {/* 검색 */}
          <input
            type="text"
            placeholder="티커 검색 (예: AAPL)"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full rounded-lg border border-gray-600 bg-gray-900 px-4 py-2 text-sm text-white placeholder-gray-500 focus:border-blue-500 focus:outline-none"
          />

          {/* 추가 종목 그룹 */}
          <div className="space-y-3">
            <p className="text-xs font-medium uppercase tracking-wider text-gray-500">추가 편입 종목</p>
            {matchedGroups.map(({ name, tickers }) => (
              <div key={name}>
                <p className="mb-1.5 text-xs font-medium text-gray-400">{name}</p>
                <div className="flex flex-wrap gap-1.5">
                  {tickers.map((t) => (
                    <span
                      key={t}
                      className={`rounded border px-2 py-0.5 text-xs font-mono font-medium ${GROUP_COLORS[name] ?? "bg-gray-700 text-gray-300 border-gray-600"}`}
                    >
                      {t}
                    </span>
                  ))}
                </div>
              </div>
            ))}
          </div>

          {/* S&P 500 기본 종목 */}
          <div>
            <p className="mb-1.5 text-xs font-medium uppercase tracking-wider text-gray-500">
              S&P 500 기본 편입 ({matchesSP500.length}개{filtered ? " 검색됨" : ""})
            </p>
            <div className="flex flex-wrap gap-1">
              {matchesSP500.map((t) => (
                <span
                  key={t}
                  className="rounded bg-gray-700/60 px-1.5 py-0.5 text-xs font-mono text-gray-400"
                >
                  {t}
                </span>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function ScoreBar({ label, score, color }: { label: string; score: number; color: string }) {
  return (
    <div className="space-y-1">
      <div className="flex justify-between text-xs text-gray-400">
        <span>{label}</span>
        <span className={color}>{formatScore(score)}점</span>
      </div>
      <div className="h-1.5 rounded-full bg-gray-700">
        <div
          className={`h-full rounded-full transition-all ${
            score >= 70 ? "bg-green-500" : score >= 50 ? "bg-yellow-500" : "bg-red-500"
          }`}
          style={{ width: `${score}%` }}
        />
      </div>
    </div>
  );
}

function RecommendationCard({ item, rank }: { item: RecommendationItem; rank: number }) {
  const rankColors = ["text-yellow-400", "text-gray-300", "text-amber-600"];
  const rankLabels = ["1위", "2위", "3위"];

  return (
    <div className={`rounded-xl border p-6 ${getScoreBgColor(item.combined_score)}`}>
      <div className="flex items-start justify-between">
        <div className="flex items-center gap-3">
          <span className={`text-2xl font-bold ${rankColors[rank]}`}>{rankLabels[rank]}</span>
          <div>
            <h3 className="text-xl font-bold text-white">{item.ticker}</h3>
            <span className={`text-sm font-medium ${
              item.sentiment === "매우긍정" || item.sentiment === "긍정"
                ? "text-green-400"
                : item.sentiment === "부정" || item.sentiment === "매우부정"
                ? "text-red-400"
                : "text-yellow-400"
            }`}>
              {getSentimentLabel(item.sentiment)}
            </span>
          </div>
        </div>
        <div className="text-right">
          <p className={`text-3xl font-bold ${getScoreColor(item.combined_score)}`}>
            {formatScore(item.combined_score)}
          </p>
          <p className="text-xs text-gray-400">통합 점수</p>
        </div>
      </div>

      <div className="mt-4 space-y-2">
        <ScoreBar label="기술적 점수 (60%)" score={item.tech_score} color={getScoreColor(item.tech_score)} />
        <ScoreBar label="뉴스 점수 (40%)" score={item.news_score} color={getScoreColor(item.news_score)} />
      </div>

      {item.key_catalysts.length > 0 && (
        <div className="mt-4">
          <p className="mb-2 text-xs font-medium text-gray-400">주요 촉매</p>
          <div className="flex flex-wrap gap-2">
            {item.key_catalysts.map((catalyst, i) => (
              <span
                key={i}
                className="rounded-full bg-blue-900/50 px-3 py-1 text-xs text-blue-300"
              >
                {catalyst}
              </span>
            ))}
          </div>
        </div>
      )}

      {item.reasoning && (
        <p className="mt-4 rounded-lg bg-gray-900/50 px-4 py-3 text-sm text-gray-300">
          {item.reasoning}
        </p>
      )}

      <div className="mt-4">
        <span className={`rounded-full px-4 py-1.5 text-sm font-semibold ${
          item.combined_score >= 70
            ? "bg-green-600 text-white"
            : "bg-gray-600 text-gray-300"
        }`}>
          {item.signal}
        </span>
      </div>
    </div>
  );
}

export default function RecommendationsPage() {
  const [result, setResult] = useState<RecommendationResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchRecommendations = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.getRecommendations() as RecommendationResponse;
      setResult(data);
    } catch (e: any) {
      setError(e.message || "추천 분석 중 오류가 발생했습니다.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-8">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-white">S&P 500 매수 추천</h1>
          <p className="mt-1 text-gray-400">
            기술적 분석(60%) + AI 뉴스 감성 분석(40%) 통합 점수 Top 3
          </p>
        </div>
        <button
          onClick={fetchRecommendations}
          disabled={loading}
          className="rounded-xl bg-blue-600 px-6 py-3 font-semibold text-white transition-all
                     hover:bg-blue-500 disabled:cursor-not-allowed disabled:opacity-50"
        >
          {loading ? (
            <span className="flex items-center gap-2">
              <svg className="h-4 w-4 animate-spin" viewBox="0 0 24 24" fill="none">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
              </svg>
              분석 중... (수 분 소요)
            </span>
          ) : (
            "Top 3 추천 받기"
          )}
        </button>
      </div>

      {/* 분석 종목 패널 */}
      <TickerPanel />

      {/* 안내 박스 */}
      <div className="rounded-xl border border-blue-800 bg-blue-900/20 p-5">
        <h3 className="font-semibold text-blue-300">분석 방식</h3>
        <div className="mt-3 grid gap-3 md:grid-cols-3 text-sm text-gray-300">
          <div>
            <p className="font-medium text-white">1단계: 기술적 분석</p>
            <p className="text-gray-400 mt-1">S&P 500 500여 개 전체 종목의 RSI, MACD, 볼린저밴드, 이동평균, 거래량 계산</p>
          </div>
          <div>
            <p className="font-medium text-white">2단계: AI 뉴스 분석</p>
            <p className="text-gray-400 mt-1">기술적 점수 상위 20개 종목의 최근 뉴스를 Claude AI로 감성 분석</p>
          </div>
          <div>
            <p className="font-medium text-white">3단계: 통합 점수</p>
            <p className="text-gray-400 mt-1">기술(60%) + 뉴스(40%) 가중 점수로 최종 Top 3 선정</p>
          </div>
        </div>
      </div>

      {error && (
        <div className="rounded-xl border border-red-700 bg-red-900/20 px-5 py-4 text-red-300">
          ⚠️ {error}
        </div>
      )}

      {result && (
        <>
          {/* 시장 상태 */}
          <div className="flex items-center gap-4 rounded-xl border border-gray-700 bg-gray-800/50 p-4">
            <div className={`h-3 w-3 rounded-full ${result.market_status.is_open ? "bg-green-400 animate-pulse" : "bg-gray-500"}`} />
            <div>
              <span className="font-medium text-white">{result.market_status.message}</span>
              <span className="ml-3 text-sm text-gray-400">{result.market_status.current_time_est}</span>
            </div>
          </div>

          {result.recommendations.length === 0 ? (
            <div className="rounded-xl border border-gray-700 bg-gray-800/50 p-12 text-center">
              <p className="text-gray-400">70점 이상 매수 추천 종목이 없습니다.</p>
              <p className="mt-1 text-sm text-gray-500">시장 상황을 다시 확인해 주세요.</p>
            </div>
          ) : (
            <div className="grid gap-6 md:grid-cols-1 lg:grid-cols-3">
              {result.recommendations.map((item, i) => (
                <RecommendationCard key={item.ticker} item={item} rank={i} />
              ))}
            </div>
          )}
        </>
      )}

      {!result && !loading && (
        <div className="rounded-xl border border-dashed border-gray-700 p-16 text-center">
          <p className="text-lg text-gray-500">위의 버튼을 클릭하여 분석을 시작하세요.</p>
          <p className="mt-2 text-sm text-gray-600">S&P 500 전체 종목 분석에 약 2-5분이 소요됩니다.</p>
        </div>
      )}
    </div>
  );
}
