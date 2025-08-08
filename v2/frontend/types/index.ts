
export interface Corpus {
  id: string;
  name: string;
  description: string;
  status: string;
  created_at: string;
  updated_at: string;
}

export interface WebSocketMessage {
  event: string;
  data: any;
  run_id: string;
}

export interface RunCompleteMessage extends WebSocketMessage {
  event: 'run_complete';
}

export interface ErrorData {
  type: string;
  message: string;
}

export interface ErrorMessage extends WebSocketMessage {
  event: 'error';
  data: ErrorData;
}

export interface StreamEventMessage extends WebSocketMessage {
  event: 'stream_event';
  event_type: string;
}
