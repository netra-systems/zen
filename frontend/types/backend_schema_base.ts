/* tslint:disable */
/* eslint-disable */
/**
 * AUTHORITATIVE SOURCE FOR BACKEND SCHEMA TYPES
 * 
 * This file was automatically generated from pydantic models by running pydantic2ts.
 * Do not modify it by hand - just update the pydantic models and then re-run the script
 * 
 * SINGLE SOURCE OF TRUTH for:
 * - SubAgentState, SubAgentStatus, BaseMessage, Message
 * - All backend schema types that mirror Python Pydantic models
 * 
 * For frontend UI-specific types, see './chat-store.ts'
 */

// Base types and enums
export type MessageType = "user" | "agent" | "system" | "error" | "tool";
export type SubAgentLifecycle = "pending" | "running" | "completed" | "failed" | "shutdown";
export type ToolStatus = "success" | "error" | "partial_success" | "in_progress" | "complete";

// Core message interfaces
export interface AgentCompleted {
  run_id: string;
  result: unknown;
}

export interface AgentErrorMessage {
  run_id: string;
  message: string;
}

export interface AgentMessage {
  text: string;
}

export interface AgentStarted {
  run_id: string;
}

/**
 * Base abstract message class.
 *
 * Messages are the inputs and outputs of ChatModels.
 */
export interface BaseMessage {
  content:
    | string
    | (
        | string
        | {
            [k: string]: unknown;
          }
      )[];
  additional_kwargs?: {
    [k: string]: unknown;
  };
  response_metadata?: {
    [k: string]: unknown;
  };
  type: string;
  name?: string | null;
  id?: string | null;
  [k: string]: unknown;
}

export interface AgentState {
  messages: BaseMessage[];
  next_node: string;
  tool_results?:
    | {
        [k: string]: unknown;
      }[]
    | null;
}

export interface SubAgentState {
  messages: BaseMessage[];
  next_node: string;
  tool_results?:
    | {
        [k: string]: unknown;
      }[]
    | null;
  lifecycle?: SubAgentLifecycle;
  start_time?: string | null;
  end_time?: string | null;
  error_message?: string | null;
  agent_id?: string;
  status?: SubAgentLifecycle;
  result?: unknown | null;
  error?: string | null;
}

export interface SubAgentStatus {
  agent_name: string;
  tools: string[];
  status: string;
  agents?: SubAgentState[];
}

export interface SubAgentUpdate {
  sub_agent_name: string;
  state: SubAgentState;
}

export interface StreamEvent {
  event_type: string;
  data: {
    [k: string]: unknown;
  };
}

export interface RunComplete {
  run_id: string;
  result: unknown;
}

export interface StopAgent {
  run_id: string;
}

// Message interfaces
export interface Message {
  id?: string;
  created_at?: string;
  content: string;
  type: MessageType;
  sub_agent_name?: string | null;
  tool_info?: {
    [k: string]: unknown;
  } | null;
  raw_data?: {
    [k: string]: unknown;
  } | null;
  displayed_to_user?: boolean;
}

export interface MessageToUser {
  sender: string;
  content: string;
  references?: string[] | null;
  raw_json?: {
    [k: string]: unknown;
  } | null;
  error?: string | null;
}

export interface UserMessage {
  text: string;
  references?: string[];
}

export interface StartAgentMessage {
  action: string;
  payload: StartAgentPayload;
}

export interface StartAgentPayload {
  settings: Settings;
  request: RequestModel;
}

export interface Settings {
  debug_mode: boolean;
}

// Request and analysis types
export interface AnalysisRequest {
  request_model: RequestModel;
}

export interface RequestModel {
  id?: string;
  user_id: string;
  query: string;
  workloads: Workload[];
  constraints?: unknown;
}

export interface Workload {
  run_id: string;
  query: string;
  data_source: DataSource;
  time_range: TimeRange;
}

export interface DataSource {
  source_table: string;
  filters?: {
    [k: string]: unknown;
  } | null;
}

export interface TimeRange {
  start_time: string;
  end_time: string;
}

export interface AnalysisResult {
  id: string;
  analysis_id: string;
  data: {
    [k: string]: unknown;
  };
  created_at: string;
}

// WebSocket types
export interface WebSocketError {
  message: string;
}

export interface WebSocketMessage {
  type: string;
  payload: {
    [k: string]: unknown;
  };
  sender?: string | null;
}

// Response types
export interface Response {
  response: {
    [k: string]: unknown;
  };
  completion: {
    [k: string]: unknown;
  };
  tool_calls: {
    [k: string]: unknown;
  };
  usage: {
    [k: string]: unknown;
  };
  system: {
    [k: string]: unknown;
  };
}

export interface UnifiedLogEntry {
  message: string;
}

// Performance and metrics
export interface Performance {
  latency_ms: {
    [k: string]: number;
  };
}

export interface BaselineMetrics {
  data: {
    [k: string]: string;
  };
}

export interface EnrichedMetrics {
  data: {
    [k: string]: string;
  };
}

export interface CostComparison {
  data: {
    [k: string]: string;
  };
}

export interface EventMetadata {
  log_schema_version: string;
  event_id: string;
  timestamp_utc: string;
  ingestion_source: string;
}

export interface FinOps {
  attribution: {
    [k: string]: string;
  };
  cost: {
    [k: string]: number;
  };
  pricing_info: {
    [k: string]: string;
  };
}

export interface TraceContext {
  trace_id: string;
  span_id: string;
  span_name: string;
  span_kind: string;
}

export interface ModelIdentifier {
  provider: string;
  model_name: string;
}
