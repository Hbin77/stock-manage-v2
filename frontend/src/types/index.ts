export interface MarketStatus {
  is_open: boolean;
  is_trading_day: boolean;
  current_time_est: string;
  market_open: string;
  market_close: string;
  message: string;
}

export interface RecommendationItem {
  ticker: string;
  tech_score: number;
  news_score: number;
  combined_score: number;
  sentiment: string;
  key_catalysts: string[];
  reasoning: string;
  signal: string;
}

export interface RecommendationResponse {
  success: boolean;
  market_status: MarketStatus;
  recommendations: RecommendationItem[];
  count: number;
  error?: string;
}

export interface HoldingItem {
  id: number;
  ticker: string;
  name: string;
  sector?: string;
  quantity: number;
  avg_buy_price: number;
  total_invested: number;
  current_price?: number;
  unrealized_pnl?: number;
  unrealized_pnl_pct?: number;
  first_bought_at?: string;
}

export interface SellSignalItem {
  ticker: string;
  name: string;
  signal_type: string;
  signal: string;
  combined_score: number;
  tech_score: number;
  news_score: number;
  pnl_pct?: number;
  current_price?: number;
  avg_buy_price: number;
  reasoning: string;
}
