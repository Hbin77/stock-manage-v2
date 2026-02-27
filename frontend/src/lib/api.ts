// 빈 문자열: nginx가 /api/* 프록시 (NAS 프로덕션) or next.config.ts rewrite (로컬 개발)
// URL 지정: 해당 주소로 직접 요청 (로컬 개발 명시)
const API_BASE = process.env.NEXT_PUBLIC_API_URL || "";

async function fetchAPI<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: "알 수 없는 오류" }));
    throw new Error(error.detail || `HTTP ${response.status}`);
  }
  return response.json();
}

export const api = {
  getRecommendations: () => fetchAPI("/api/v1/recommendations"),
  getPortfolio: () => fetchAPI("/api/v1/portfolio"),
  buyStock: (data: { ticker: string; quantity: number; price: number; note?: string }) =>
    fetchAPI("/api/v1/portfolio/buy", { method: "POST", body: JSON.stringify(data) }),
  sellStock: (ticker: string) =>
    fetchAPI(`/api/v1/portfolio/${ticker}`, { method: "DELETE" }),
  getSellSignals: () => fetchAPI("/api/v1/sell-signals"),
  getSellSignalHistory: (limit = 50) => fetchAPI(`/api/v1/sell-signals/history?limit=${limit}`),
  getStockScore: (ticker: string) => fetchAPI(`/api/v1/scores/${ticker}`),
  getMarketStatus: () => fetchAPI("/api/v1/market-status"),
  getTransactions: () => fetchAPI("/api/v1/portfolio/transactions"),
  getTickers: () => fetchAPI("/api/v1/tickers"),
};
