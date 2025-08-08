export interface User {
  id: string;
  email: string;
  full_name: string | null;
  picture: string | null;
}

export interface AuthEndpoints {
  login: string;
  logout: string;
  token: string;
  user: string;
  dev_login: string;
}

export interface AuthConfig {
  google_client_id: string;
  endpoints: AuthEndpoints;
  development_mode: boolean;
  user: User | null;
  authorized_javascript_origins: string[];
  authorized_redirect_uris: string[];
}

export interface WebSocketError {
  type: "error";
  message: string;
}

export interface RequestModel {
  id: string;
  user_id: string;
  query: string;
  workloads: any[]; // Replace with a proper Workload interface
  constraints: any;
}

export interface AnalysisRequest {
  type: "analysis_request";
  payload: RequestModel;
}

export interface WebSocketMessage {
  type: string;
  payload: AnalysisRequest | WebSocketError | Record<string, any>;
}
