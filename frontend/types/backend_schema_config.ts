/* tslint:disable */
/* eslint-disable */
/**
/* This file was automatically generated from pydantic models by running pydantic2ts.
/* Do not modify it by hand - just update the pydantic models and then re-run the script
*/

// Configuration interfaces
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

export interface RedisConfig {
  host?: string;
  port?: number;
  username?: string;
  password?: string | null;
}

export interface WebSocketConfig {
  /**
   * The WebSocket URL for the frontend to connect to.
   */
  ws_url?: string;
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

export interface LangfuseConfig {
  secret_key?: string;
  public_key?: string;
  host?: string;
}

// ClickHouse configuration interfaces
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

export interface ClickHouseCredentials {
  host: string;
  port: number;
  user: string;
  password: string;
  database: string;
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

/**
 * Development-specific settings can override defaults.
 */
export interface DevelopmentConfig {
  environment?: string;
  google_cloud?: GoogleCloudConfig;
  oauth_config?: OAuthConfig;
  clickhouse_native?: ClickHouseNativeConfig;
  clickhouse_https?: ClickHouseHTTPSConfig;
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
  debug?: boolean;
  dev_user_email?: string;
}

/**
 * Production-specific settings.
 */
export interface ProductionConfig {
  environment?: string;
  google_cloud?: GoogleCloudConfig;
  oauth_config?: OAuthConfig;
  clickhouse_native?: ClickHouseNativeConfig;
  clickhouse_https?: ClickHouseHTTPSConfig;
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
  debug?: boolean;
}

/**
 * Testing-specific settings.
 */
export interface TestingConfig {
  environment?: string;
  google_cloud?: GoogleCloudConfig;
  oauth_config?: OAuthConfig;
  clickhouse_native?: ClickHouseNativeConfig;
  clickhouse_https?: ClickHouseHTTPSConfig;
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

export interface LogTableSettings {
  log_table: string;
}

export interface DefaultLogTableSettings {
  context: string;
  log_table: string;
}

export interface TimePeriodSettings {
  days: number;
}

export interface SecretReference {
  name: string;
  target_field: string;
  target_models?: string[] | null;
  project_id?: string;
  version?: string;
}
