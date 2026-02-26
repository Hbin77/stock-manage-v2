export function formatCurrency(value: number | undefined | null, currency = "USD"): string {
  if (value == null) return "-";
  return new Intl.NumberFormat("ko-KR", {
    style: "currency",
    currency,
    minimumFractionDigits: 2,
  }).format(value);
}

export function formatPercent(value: number | undefined | null): string {
  if (value == null) return "-";
  const sign = value >= 0 ? "+" : "";
  return `${sign}${value.toFixed(2)}%`;
}

export function formatScore(score: number): string {
  return score.toFixed(1);
}

export function getScoreColor(score: number): string {
  if (score >= 70) return "text-green-400";
  if (score >= 50) return "text-yellow-400";
  if (score >= 40) return "text-orange-400";
  return "text-red-400";
}

export function getScoreBgColor(score: number): string {
  if (score >= 70) return "bg-green-900/30 border-green-700";
  if (score >= 50) return "bg-yellow-900/30 border-yellow-700";
  if (score >= 40) return "bg-orange-900/30 border-orange-700";
  return "bg-red-900/30 border-red-700";
}

export function getPnlColor(pnl: number | undefined | null): string {
  if (pnl == null) return "text-gray-400";
  return pnl >= 0 ? "text-green-400" : "text-red-400";
}

export function getSentimentLabel(sentiment: string): string {
  const map: Record<string, string> = {
    "매우긍정": "매우 긍정적",
    "긍정": "긍정적",
    "중립": "중립",
    "부정": "부정적",
    "매우부정": "매우 부정적",
  };
  return map[sentiment] || sentiment;
}
