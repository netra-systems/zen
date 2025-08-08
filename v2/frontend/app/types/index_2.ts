export interface Corpus {
  id: string;
  name: string;
  description: string;
  status: string;
  created_at: string;
  updated_at: string;
}

export interface User {
  id: string;
  email: string;
  full_name: string;
  picture: string;
}

export interface AuthEndpoints {
  login: string;
  logout: string;
  token: string;
  user: string;
}

export interface AuthConfigResponse {
  google_client_id: string;
  endpoints: AuthEndpoints;
  development_mode: boolean;
  user: User | null;
}


// --- WebSocket Service Types ---

export enum WebSocketStatus {
    Connecting,
    Open,
    Closing,
    Closed,
    Error,
}

export interface WebSocketMessage {
  type: string;
  payload: any;
}

export interface AnalysisRequest {
  settings: {
    debug_mode: boolean;
  };
  request: {
    user_id: string;
    query: string;
    workloads: any[];
    references: any[];
  };
}

const config = {
  api: {
    wsBaseUrl: process.env.NEXT_PUBLIC_WEBSOCKET_URL || 'ws://localhost:8000',
  },
};

export default config;