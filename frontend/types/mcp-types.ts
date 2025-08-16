// MCP (Model Context Protocol) TypeScript types for frontend
// Based on backend MCP client schemas - maintains type consistency

// ============================================
// Enums and Constants
// ============================================

export type MCPTransport = 'HTTP' | 'WEBSOCKET' | 'STDIO';

export type MCPServerStatus = 
  | 'CONNECTING' 
  | 'CONNECTED' 
  | 'DISCONNECTED' 
  | 'ERROR' 
  | 'MAINTENANCE';

export type MCPAuthType = 'NONE' | 'API_KEY' | 'OAUTH' | 'ENVIRONMENT';

export type MCPToolExecutionStatus = 
  | 'PENDING' 
  | 'RUNNING' 
  | 'COMPLETED' 
  | 'FAILED' 
  | 'CANCELLED';

// ============================================
// Core MCP Types
// ============================================

export interface MCPAuthConfig {
  auth_type: MCPAuthType;
  api_key?: string;
  oauth_config?: Record<string, any>;
  environment_vars?: Record<string, string>;
}

export interface MCPRetryConfig {
  max_attempts: number;
  base_delay_ms: number;
  max_delay_ms: number;
  exponential_base: number;
}

export interface MCPServerConfig {
  name: string;
  url: string;
  transport: MCPTransport;
  auth?: MCPAuthConfig;
  timeout_ms: number;
  retry_config?: MCPRetryConfig;
  metadata?: Record<string, any>;
}

export interface MCPServerInfo {
  id: string;
  name: string;
  url: string;
  transport: MCPTransport;
  status: MCPServerStatus;
  capabilities?: Record<string, any>;
  last_health_check?: string;
  created_at: string;
  updated_at: string;
}

export interface MCPConnection {
  id: string;
  server_name: string;
  transport: MCPTransport;
  session_id: string;
  capabilities: Record<string, any>;
  status: MCPServerStatus;
  created_at: string;
}

export interface MCPTool {
  name: string;
  description: string;
  server_name: string;
  input_schema: Record<string, any>;
  output_schema?: Record<string, any>;
  metadata?: Record<string, any>;
}

export interface MCPToolResult {
  tool_name: string;
  server_name: string;
  content: Array<Record<string, any>>;
  is_error: boolean;
  error_message?: string;
  execution_time_ms?: number;
}

export interface MCPResource {
  uri: string;
  name: string;
  description?: string;
  mime_type?: string;
  content?: string;
  metadata?: Record<string, any>;
}

// ============================================
// Tool Execution State Types
// ============================================

export interface MCPToolExecution {
  id: string;
  tool_name: string;
  server_name: string;
  status: MCPToolExecutionStatus;
  arguments: Record<string, any>;
  result?: MCPToolResult;
  started_at: string;
  completed_at?: string;
  duration_ms?: number;
}

export interface MCPServerMetrics {
  server_name: string;
  connection_status: MCPServerStatus;
  tools_count: number;
  resources_count: number;
  last_tool_execution?: string;
  average_response_time_ms?: number;
  error_count: number;
  uptime_percentage: number;
}

// ============================================
// UI State Types
// ============================================

export interface MCPUIState {
  servers: Map<string, MCPServerInfo>;
  connections: Map<string, MCPConnection>;
  available_tools: MCPTool[];
  active_executions: Map<string, MCPToolExecution>;
  server_metrics: Map<string, MCPServerMetrics>;
  is_loading: boolean;
  last_error?: string;
}

export interface MCPToolIndicatorProps {
  tool_executions: MCPToolExecution[];
  server_status: MCPServerStatus;
  show_details?: boolean;
  className?: string;
}

export interface MCPServerStatusProps {
  servers: MCPServerInfo[];
  connections: MCPConnection[];
  compact?: boolean;
  className?: string;
}

export interface MCPResultCardProps {
  result: MCPToolResult;
  execution: MCPToolExecution;
  show_raw_data?: boolean;
  collapsible?: boolean;
  className?: string;
}

// ============================================
// Hook Return Types
// ============================================

export interface UseMCPToolsReturn {
  tools: MCPTool[];
  executions: MCPToolExecution[];
  servers: MCPServerInfo[];
  executeTool: (serverName: string, toolName: string, args: Record<string, any>) => Promise<MCPToolResult>;
  getServerStatus: (serverName: string) => MCPServerStatus;
  refreshTools: () => Promise<void>;
  isLoading: boolean;
  error?: string;
}

// ============================================
// API Response Types
// ============================================

export interface MCPApiResponse<T = any> {
  success: boolean;
  data?: T;
  message: string;
  error_code?: string;
}

export type ListServersResponse = MCPApiResponse<MCPServerInfo[]>;
export type DiscoverToolsResponse = MCPApiResponse<MCPTool[]>;
export type ExecuteToolResponse = MCPApiResponse<MCPToolResult>;
export type ServerStatusResponse = MCPApiResponse<MCPConnection[]>;