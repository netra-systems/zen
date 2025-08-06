
export interface AnalysisRequest {
    user_request: string;
    user_id: string;
    settings: Record<string, unknown>;
}

export interface Message {
  role: 'user' | 'assistant';
  content: string;
}
