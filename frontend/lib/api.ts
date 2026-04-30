import axios from 'axios';

const API_URL = 'http://127.0.0.1:8000';
const WS_URL = 'ws://127.0.0.1:8000';

const api = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

export interface Instrument {
  id: number;
  symbol: string;
  name: string;
  currency: string;
  exchange: string;
  data_role: string;
  updated_at: string | null;
}

export const MarketAPI = {
  getAll: async () => {
    const response = await api.get<Instrument[]>('/market/instruments/');
    return response.data;
  },

  add: async (symbol: string, data_role: string = 'TRADE') => {
    const response = await api.post<Instrument>('/market/instruments/', {
      symbol,
      data_role,
    });
    return response.data;
  },

  delete: async (symbol: string) => {
    const response = await api.delete(`/instruments/${symbol}`);
    return response.data;
  },
};

export interface BotState {
  id: number;
  name: string;
  status: 'STOPPED' | 'RUNNING' | 'SLEEPING' | 'ERROR';
  last_run_at: string | null;
  next_run_at: string | null;
  info_message: string | null;
  config: { [key: string]: string };
  is_auto_run: boolean;
  run_interval_mins: number;
  run_at_time: string;
}

export const SystemAPI = {
  getBots: async () => {
    const response = await api.get<BotState[]>('/bots/');
    return response.data;
  },

  startBot: async (botName: string) => {
    const response = await api.post(`/bot/${botName}/start/`);
    return response.data;
  },

  stopBot: async (botName: string) => {
    const response = await api.post(`/bot/${botName}/stop/`);
    return response.data;
  },

  runBot: async (botName: string) => {
    const response = await api.post(`/bots/${botName}/run/`);
    return response.data;
  },

  updateBotConfig: async (
    botName: string,
    config: { is_auto_run: boolean; run_interval_mins: number },
  ) => {
    const response = await api.patch<BotState>(
      `/system/bot/${botName}/config`,
      config,
    );
    return response.data;
  },

  getLogSocket: () => new WebSocket(`${WS_URL}/ws/logs`),
  getLogs: async (limit: number = 100) => {
    const response = await api.get<LogEntry[]>(`/bots/logs?limit=${limit}`);
    return response.data;
  },
};

export interface FundamentalData {
  symbol: string;
  pe_ratio: number | null;
  peg_ratio: number | null;
  market_cap: number | null;
  div_yield: number | null;
  price_to_book: number | null;
  roe: number | null;
  current_iv: number | null;
  iv_rank: number | null;
  updated_at: string;
}

export const AnalysisAPI = {
  getFundamentals: async () => {
    const response = await api.get<FundamentalData[]>('/analysis/fundamentals');
    return response.data;
  },
};

export interface DashboardSummary {
  connected: boolean;
  total_value: number;
  available_cash: { currency: string; value: number }[];
  positions: { symbol: string; position: number; pnl: number }[];
  total_positions_count: number;
}

export const DashboardAPI = {
  getSummary: async () => {
    const response = await api.get<DashboardSummary>('/dashboard/summary');
    return response.data;
  },
};

export interface TradeSignal {
  id: number;
  symbol: string;
  bot_name: string;
  signal_price: number;
  score: number;
  reason: string;
  status: string;
  is_favorite: boolean;
  created_at: string;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  signal_data: any;
}

export const SignalsAPI = {
  getAll: async () => {
    const response = await api.get<TradeSignal[]>('/signals/');
    return response.data;
  },
  toggleFavorite: async (id: number) => {
    await api.post(`/signals/${id}/toggle_favorite`);
  },
  archive: async (id: number) => {
    await api.post(`/signals/${id}/archive`);
  },
};

export type LogType = 'INFO' | 'SUCCESS' | 'WARNING' | 'ERROR';

export interface LogEntry {
  time: string;
  module: string;
  type: LogType;
  msg: string;
}

export interface WatchlistEntry {
  id: number;
  ticker: string;
  source: 'Auto' | 'Manual';
  added_at: string;
  last_signal_at: string | null;
  fundamental_score: number | null;
  current_state: 'Watching' | 'Alert' | 'Action';
}

export const WatchlistAPI = {
  getAll: async () => {
    const response = await api.get<WatchlistEntry[]>('/watchlist/');
    return response.data;
  },

  add: async (ticker: string) => {
    const response = await api.post<WatchlistEntry>('/watchlist/', { ticker });
    return response.data;
  },

  delete: async (id: number) => {
    const response = await api.delete(`/watchlist/${id}`);
    return response.data;
  }
};

export default api;
