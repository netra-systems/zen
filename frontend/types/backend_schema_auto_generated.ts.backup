/* tslint:disable */
/* eslint-disable */
/**
/* This file was automatically generated from pydantic models by running pydantic2ts.
/* Do not modify it by hand - just update the pydantic models and then re-run the script
*/

export type MessageType = "user" | "agent" | "system" | "error" | "tool";
export type SubAgentLifecycle = "pending" | "running" | "completed" | "failed" | "shutdown";
export type ToolStatus = "success" | "error" | "partial_success" | "in_progress" | "complete";

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
export interface AgentState {
  messages: BaseMessage[];
  next_node: string;
  tool_results?:
    | {
        [k: string]: unknown;
      }[]
    | null;
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
/**
 * Base configuration class.
 */
export interface AppConfig {
  environment?: string;
  google_cloud?: GoogleCloudConfig;
  oauth_config?: OAuthConfig;
  clickhouse_native?: ClickHouseNativeConfig;
  clickhouse_https?: ClickHouseHTTPSConfig;
  clickhouse_https_dev?: ClickHouseHTTPSDevConfig;
  clickhouse_logging?: ClickHouseLoggingConfig;
  langfuse?: LangfuseConfig;
  ws_config?: WebSocketConfig;
  secret_key?: string;
  algorithm?: string;
  access_token_expire_minutes?: number;
  fernet_key?: string;
  jwt_secret_key?: string;
  api_base_url?: string;
  database_url?: string;
  log_level?: string;
  log_secrets?: boolean;
  frontend_url?: string;
  redis?: RedisConfig;
  llm_configs?: {
    [k: string]: LLMConfig;
  };
}
export interface GoogleCloudConfig {
  project_id?: string;
  client_id?: string;
  client_secret?: string;
}
export interface OAuthConfig {
  client_id?: string;
  client_secret?: string;
  token_uri?: string;
  auth_uri?: string;
  userinfo_endpoint?: string;
  scopes?: string[];
  authorized_javascript_origins?: string[];
  authorized_redirect_uris?: string[];
}
export interface ClickHouseNativeConfig {
  host?: string;
  port?: number;
  user?: string;
  password?: string;
  database?: string;
}
export interface ClickHouseHTTPSConfig {
  host?: string;
  port?: number;
  user?: string;
  password?: string;
  database?: string;
}
export interface ClickHouseHTTPSDevConfig {
  host?: string;
  port?: number;
  user?: string;
  password?: string;
  database?: string;
  superuser?: boolean;
}
export interface ClickHouseLoggingConfig {
  enabled?: boolean;
  default_table?: string;
  default_time_period_days?: number;
  available_tables?: string[];
  default_tables?: {
    [k: string]: string;
  };
  available_time_periods?: number[];
}
export interface LangfuseConfig {
  secret_key?: string;
  public_key?: string;
  host?: string;
}
export interface WebSocketConfig {
  /**
   * The WebSocket URL for the frontend to connect to.
   */
  ws_url?: string;
}
export interface RedisConfig {
  host?: string;
  port?: number;
  username?: string;
  password?: string | null;
}
export interface LLMConfig {
  /**
   * The LLM provider (e.g., 'google', 'openai').
   */
  provider: string;
  /**
   * The name of the model.
   */
  model_name: string;
  /**
   * The API key for the LLM provider.
   */
  api_key?: string | null;
  /**
   * A dictionary of generation parameters, e.g., temperature, max_tokens.
   */
  generation_config?: {
    [k: string]: unknown;
  };
}
export interface AuthConfigResponse {
  google_client_id: string;
  endpoints: AuthEndpoints;
  development_mode: boolean;
  user?: User | null;
  authorized_javascript_origins: string[];
  authorized_redirect_uris: string[];
}
export interface AuthEndpoints {
  login: string;
  logout: string;
  token: string;
  user: string;
  dev_login: string;
}
export interface User {
  email: string;
  full_name?: string | null;
  picture?: string | null;
  id: string;
  is_active: boolean;
  is_superuser: boolean;
  hashed_password?: string | null;
  [k: string]: unknown;
}
export interface BaselineMetrics {
  data: {
    [k: string]: string;
  };
}
export interface ClickHouseCredentials {
  host: string;
  port: number;
  user: string;
  password: string;
  database: string;
}
export interface ClickHouseHTTPSConfig1 {
  host?: string;
  port?: number;
  user?: string;
  password?: string;
  database?: string;
}
export interface ClickHouseHTTPSDevConfig1 {
  host?: string;
  port?: number;
  user?: string;
  password?: string;
  database?: string;
  superuser?: boolean;
}
export interface ClickHouseLoggingConfig1 {
  enabled?: boolean;
  default_table?: string;
  default_time_period_days?: number;
  available_tables?: string[];
  default_tables?: {
    [k: string]: string;
  };
  available_time_periods?: number[];
}
export interface ClickHouseNativeConfig1 {
  host?: string;
  port?: number;
  user?: string;
  password?: string;
  database?: string;
}
export interface ContentCorpus {
  record_id: string;
  workload_type: string;
  prompt: string;
  response: string;
  created_at: string;
  [k: string]: unknown;
}
export interface ContentCorpusGenParams {
  /**
   * Number of samples to generate for each workload type.
   */
  samples_per_type?: number;
  /**
   * Controls randomness. Higher is more creative.
   */
  temperature?: number;
  /**
   * Nucleus sampling probability.
   */
  top_p?: number | null;
  /**
   * Top-k sampling control.
   */
  top_k?: number | null;
  /**
   * Max CPU cores to use.
   */
  max_cores?: number;
  /**
   * The name of the ClickHouse table to store the corpus in.
   */
  clickhouse_table?: string;
}
export interface ContentGenParams {
  /**
   * Number of samples to generate for each workload type.
   */
  samples_per_type?: number;
  /**
   * Controls randomness. Higher is more creative.
   */
  temperature?: number;
  /**
   * Nucleus sampling probability.
   */
  top_p?: number | null;
  /**
   * Top-k sampling control.
   */
  top_k?: number | null;
  /**
   * Max CPU cores to use.
   */
  max_cores?: number;
}
export interface Corpus {
  name: string;
  description?: string | null;
  id: string;
  status: string;
  created_by_id: string;
  created_at: string;
  updated_at: string;
  [k: string]: unknown;
}
export interface CorpusBase {
  name: string;
  description?: string | null;
}
export interface CorpusCreate {
  name: string;
  description?: string | null;
}
export interface CorpusInDBBase {
  name: string;
  description?: string | null;
  id: string;
  status: string;
  created_by_id: string;
  created_at: string;
  updated_at: string;
  [k: string]: unknown;
}
export interface CorpusUpdate {
  name: string;
  description?: string | null;
}
export interface CostComparison {
  data: {
    [k: string]: string;
  };
}
export interface DataIngestionParams {
  /**
   * The path to the data file to ingest.
   */
  data_path: string;
  /**
   * The name of the table to ingest the data into.
   */
  table_name: string;
}
export interface DefaultLogTableSettings {
  context: string;
  log_table: string;
}
export interface DevLoginRequest {
  email: string;
}
export interface DevUser {
  email?: string;
  full_name?: string;
  picture?: string | null;
  is_dev?: boolean;
}
/**
 * Development-specific settings can override defaults.
 */
export interface DevelopmentConfig {
  environment?: string;
  google_cloud?: GoogleCloudConfig1;
  oauth_config?: OAuthConfig;
  clickhouse_native?: ClickHouseNativeConfig2;
  clickhouse_https?: ClickHouseHTTPSConfig2;
  clickhouse_https_dev?: ClickHouseHTTPSDevConfig2;
  clickhouse_logging?: ClickHouseLoggingConfig2;
  langfuse?: LangfuseConfig1;
  ws_config?: WebSocketConfig;
  secret_key?: string;
  algorithm?: string;
  access_token_expire_minutes?: number;
  fernet_key?: string;
  jwt_secret_key?: string;
  api_base_url?: string;
  database_url?: string;
  log_level?: string;
  log_secrets?: boolean;
  frontend_url?: string;
  redis?: RedisConfig;
  llm_configs?: {
    [k: string]: LLMConfig;
  };
  debug?: boolean;
  dev_user_email?: string;
}
export interface GoogleCloudConfig1 {
  project_id?: string;
  client_id?: string;
  client_secret?: string;
}
export interface ClickHouseNativeConfig2 {
  host?: string;
  port?: number;
  user?: string;
  password?: string;
  database?: string;
}
export interface ClickHouseHTTPSConfig2 {
  host?: string;
  port?: number;
  user?: string;
  password?: string;
  database?: string;
}
export interface ClickHouseHTTPSDevConfig2 {
  host?: string;
  port?: number;
  user?: string;
  password?: string;
  database?: string;
  superuser?: boolean;
}
export interface ClickHouseLoggingConfig2 {
  enabled?: boolean;
  default_table?: string;
  default_time_period_days?: number;
  available_tables?: string[];
  default_tables?: {
    [k: string]: string;
  };
  available_time_periods?: number[];
}
export interface LangfuseConfig1 {
  secret_key?: string;
  public_key?: string;
  host?: string;
}
export interface DiscoveredPattern {
  /**
   * The ID of the pattern.
   */
  pattern_id: string;
  /**
   * A description of the pattern.
   */
  description: string;
}
export interface EnrichedMetrics {
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
export interface GoogleCloudConfig2 {
  project_id?: string;
  client_id?: string;
  client_secret?: string;
}
/**
 * Represents the user information received from Google's OAuth service.
 */
export interface GoogleUser {
  email: string;
  name?: string | null;
  picture?: string | null;
}
export interface LangfuseConfig2 {
  secret_key?: string;
  public_key?: string;
  host?: string;
}
export interface LearnedPolicy {
  /**
   * The name of the pattern.
   */
  pattern_name: string;
  /**
   * The name of the optimal supply option.
   */
  optimal_supply_option_name: string;
}
export interface LogGenParams {
  /**
   * The ID of the content corpus to use for generation.
   */
  corpus_id: string;
  /**
   * Number of log entries to generate.
   */
  num_logs?: number;
  /**
   * Max CPU cores to use.
   */
  max_cores?: number;
}
export interface LogTableSettings {
  log_table: string;
}
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
export interface ModelIdentifier {
  provider: string;
  model_name: string;
}
export interface Performance {
  latency_ms: {
    [k: string]: number;
  };
}
export interface PredictedOutcome {
  /**
   * The name of the supply option.
   */
  supply_option_name: string;
  /**
   * The explanation of the outcome.
   */
  explanation: string;
}
/**
 * Production-specific settings.
 */
export interface ProductionConfig {
  environment?: string;
  google_cloud?: GoogleCloudConfig3;
  oauth_config?: OAuthConfig;
  clickhouse_native?: ClickHouseNativeConfig3;
  clickhouse_https?: ClickHouseHTTPSConfig3;
  clickhouse_https_dev?: ClickHouseHTTPSDevConfig3;
  clickhouse_logging?: ClickHouseLoggingConfig3;
  langfuse?: LangfuseConfig3;
  ws_config?: WebSocketConfig;
  secret_key?: string;
  algorithm?: string;
  access_token_expire_minutes?: number;
  fernet_key?: string;
  jwt_secret_key?: string;
  api_base_url?: string;
  database_url?: string;
  log_level?: string;
  log_secrets?: boolean;
  frontend_url?: string;
  redis?: RedisConfig;
  llm_configs?: {
    [k: string]: LLMConfig;
  };
  debug?: boolean;
}
export interface GoogleCloudConfig3 {
  project_id?: string;
  client_id?: string;
  client_secret?: string;
}
export interface ClickHouseNativeConfig3 {
  host?: string;
  port?: number;
  user?: string;
  password?: string;
  database?: string;
}
export interface ClickHouseHTTPSConfig3 {
  host?: string;
  port?: number;
  user?: string;
  password?: string;
  database?: string;
}
export interface ClickHouseHTTPSDevConfig3 {
  host?: string;
  port?: number;
  user?: string;
  password?: string;
  database?: string;
  superuser?: boolean;
}
export interface ClickHouseLoggingConfig3 {
  enabled?: boolean;
  default_table?: string;
  default_time_period_days?: number;
  available_tables?: string[];
  default_tables?: {
    [k: string]: string;
  };
  available_time_periods?: number[];
}
export interface LangfuseConfig3 {
  secret_key?: string;
  public_key?: string;
  host?: string;
}
export interface ReferenceCreateRequest {}
export interface ReferenceGetResponse {}
export interface ReferenceItem {}
export interface ReferenceUpdateRequest {}
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
export interface RunComplete {
  run_id: string;
  result: unknown;
}
export interface SecretReference {
  name: string;
  target_field: string;
  target_models?: string[] | null;
  project_id?: string;
  version?: string;
}
export interface Settings {
  debug_mode: boolean;
}
export interface StartAgentMessage {
  action: string;
  payload: StartAgentPayload;
}
export interface StartAgentPayload {
  settings: Settings;
  request: RequestModel;
}
export interface StopAgent {
  run_id: string;
}
export interface StreamEvent {
  event_type: string;
  data: {
    [k: string]: unknown;
  };
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
}
export interface SubAgentStatus {
  agent_name: string;
  tools: string[];
  status: string;
}
export interface SubAgentUpdate {
  sub_agent_name: string;
  state: SubAgentState;
}
export interface SupplyOption {
  name: string;
  description?: string | null;
  id: number;
  [k: string]: unknown;
}
export interface SupplyOptionBase {
  name: string;
  description?: string | null;
}
export interface SupplyOptionCreate {
  name: string;
  description?: string | null;
}
export interface SupplyOptionInDB {
  name: string;
  description?: string | null;
  id: number;
  [k: string]: unknown;
}
export interface SupplyOptionInDBBase {
  name: string;
  description?: string | null;
  id: number;
  [k: string]: unknown;
}
export interface SupplyOptionUpdate {
  name: string;
  description?: string | null;
}
export interface SyntheticDataGenParams {
  /**
   * Number of traces to generate.
   */
  num_traces?: number;
  /**
   * Number of unique users to simulate.
   */
  num_users?: number;
  /**
   * The fraction of traces that should be errors.
   */
  error_rate?: number;
  /**
   * A list of event types to simulate.
   */
  event_types?: string[];
  /**
   * The name of the source ClickHouse table for the content corpus.
   */
  source_table?: string;
  /**
   * The name of the destination ClickHouse table for the generated data.
   */
  destination_table?: string;
}
/**
 * Testing-specific settings.
 */
export interface TestingConfig {
  environment?: string;
  google_cloud?: GoogleCloudConfig4;
  oauth_config?: OAuthConfig;
  clickhouse_native?: ClickHouseNativeConfig4;
  clickhouse_https?: ClickHouseHTTPSConfig4;
  clickhouse_https_dev?: ClickHouseHTTPSDevConfig4;
  clickhouse_logging?: ClickHouseLoggingConfig4;
  langfuse?: LangfuseConfig4;
  ws_config?: WebSocketConfig;
  secret_key?: string;
  algorithm?: string;
  access_token_expire_minutes?: number;
  fernet_key?: string;
  jwt_secret_key?: string;
  api_base_url?: string;
  database_url?: string;
  log_level?: string;
  log_secrets?: boolean;
  frontend_url?: string;
  redis?: RedisConfig;
  llm_configs?: {
    [k: string]: LLMConfig;
  };
}
export interface GoogleCloudConfig4 {
  project_id?: string;
  client_id?: string;
  client_secret?: string;
}
export interface ClickHouseNativeConfig4 {
  host?: string;
  port?: number;
  user?: string;
  password?: string;
  database?: string;
}
export interface ClickHouseHTTPSConfig4 {
  host?: string;
  port?: number;
  user?: string;
  password?: string;
  database?: string;
}
export interface ClickHouseHTTPSDevConfig4 {
  host?: string;
  port?: number;
  user?: string;
  password?: string;
  database?: string;
  superuser?: boolean;
}
export interface ClickHouseLoggingConfig4 {
  enabled?: boolean;
  default_table?: string;
  default_time_period_days?: number;
  available_tables?: string[];
  default_tables?: {
    [k: string]: string;
  };
  available_time_periods?: number[];
}
export interface LangfuseConfig4 {
  secret_key?: string;
  public_key?: string;
  host?: string;
}
export interface TimePeriodSettings {
  days: number;
}
export interface Token {
  access_token: string;
  token_type: string;
}
export interface TokenPayload {
  sub: string;
}
export interface ToolCompleted {
  tool_name: string;
  result: unknown;
}
export interface ToolInput {
  tool_name: string;
  args?: unknown[];
  kwargs?: {
    [k: string]: unknown;
  };
}
export interface ToolInvocation {
  tool_result: ToolResult;
}
export interface ToolResult {
  tool_input: ToolInput;
  status?: ToolStatus;
  message?: string;
  payload?: unknown;
  start_time?: number;
  end_time?: number | null;
}
export interface ToolStarted {
  tool_name: string;
}
export interface TraceContext {
  trace_id: string;
  span_id: string;
  span_name: string;
  span_kind: string;
}
export interface UnifiedLogEntry {
  message: string;
}
export interface UserBase {
  email: string;
  full_name?: string | null;
  picture?: string | null;
}
export interface UserCreate {
  email: string;
  full_name?: string | null;
  picture?: string | null;
  password: string;
}
export interface UserCreateOAuth {
  email: string;
  full_name?: string | null;
  picture?: string | null;
}
export interface UserMessage {
  text: string;
  references?: string[];
}
export interface UserUpdate {
  email: string;
  full_name?: string | null;
  picture?: string | null;
}
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
