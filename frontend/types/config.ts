/* tslint:disable */
/* eslint-disable */
/**
 * Configuration-related type definitions
 * Auto-generated from pydantic models - do not modify by hand
 */

export interface AppConfig {
  auth_endpoints: AuthEndpoints;
  features: {
    analytics: boolean;
    file_upload: boolean;
    real_time_collaboration: boolean;
    advanced_search: boolean;
    data_export: boolean;
    custom_integrations: boolean;
    ai_suggestions: boolean;
    workflow_automation: boolean;
  };
  limits: {
    max_file_size_mb: number;
    max_threads_per_user: number;
    max_messages_per_thread: number;
    api_rate_limit_per_minute: number;
  };
  ui: {
    theme: string;
    brand_name: string;
    support_email: string;
    documentation_url: string;
  };
}

export interface ClickHouseCredentials {
  host: string;
  port: number;
  username: string;
  password: string;
  database: string;
  secure?: boolean;
}

export interface ClickHouseHTTPSConfig {
  host: string;
  port?: number;
  username: string;
  password: string;
  database: string;
  secure?: boolean;
}

export interface ClickHouseHTTPSDevConfig {
  host: string;
  port?: number;
  username: string;
  password: string;
  database: string;
  secure?: boolean;
  debug?: boolean;
}

export interface ClickHouseLoggingConfig {
  enabled: boolean;
  table_name?: string;
  batch_size?: number;
  flush_interval?: number;
  max_retries?: number;
}

export interface ClickHouseNativeConfig {
  host: string;
  port?: number;
  username: string;
  password: string;
  database: string;
  secure?: boolean;
}

export interface DevelopmentConfig {
  debug: boolean;
  auto_reload: boolean;
  show_sql_queries: boolean;
  enable_cors: boolean;
}

export interface GoogleCloudConfig {
  project_id: string;
  credentials_path?: string | null;
  bucket_name?: string | null;
  region?: string;
}

export interface LangfuseConfig {
  secret_key: string;
  public_key: string;
  host: string;
  debug?: boolean;
  enabled?: boolean;
}

export interface LLMConfig {
  provider: string;
  model: string;
  api_key?: string | null;
  temperature?: number;
  max_tokens?: number;
  timeout?: number;
}

export interface OAuthConfig {
  google_client_id: string;
  google_client_secret: string;
  google_redirect_uri: string;
  allowed_domains?: string[] | null;
  auto_register?: boolean;
}

export interface ProductionConfig {
  log_level: string;
  enable_metrics: boolean;
  enable_tracing: boolean;
  max_connections: number;
}

export interface RedisConfig {
  host: string;
  port?: number;
  password?: string | null;
  db?: number;
  ssl?: boolean;
}

export interface Settings {
  environment: string;
  debug: boolean;
  cors_origins: string[];
  database_url?: string | null;
  secret_key: string;
  access_token_expire_minutes?: number;
  oauth: OAuthConfig;
  clickhouse: ClickHouseHTTPSConfig | ClickHouseNativeConfig;
  redis?: RedisConfig | null;
  langfuse?: LangfuseConfig | null;
  google_cloud?: GoogleCloudConfig | null;
  websocket: WebSocketConfig;
  development?: DevelopmentConfig | null;
  production?: ProductionConfig | null;
  testing?: TestingConfig | null;
}

export interface TestingConfig {
  use_test_db: boolean;
  reset_db_before_tests: boolean;
  generate_test_data: boolean;
  parallel_tests: boolean;
}

export interface WebSocketConfig {
  host: string;
  port: number;
  path?: string;
  max_connections?: number;
  heartbeat_interval?: number;
  timeout?: number;
}

// Re-export types needed by config
export interface AuthEndpoints {
  login_url: string;
  logout_url: string;
  user_info_url: string;
  refresh_url: string;
}