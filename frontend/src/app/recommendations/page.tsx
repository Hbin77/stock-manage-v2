"use client";
import { useState } from "react";
import { api } from "@/lib/api";
import { formatScore, getScoreColor, getScoreBgColor, getSentimentLabel } from "@/lib/utils";
import type { RecommendationResponse, RecommendationItem } from "@/types";

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
