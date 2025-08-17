// MCP Client Service - Frontend API interface for MCP operations
// Handles server registration, tool execution, and resource management

import type {
  MCPServerInfo,
  MCPTool,
  MCPToolResult,
  MCPResource,
  MCPApiResponse,
  ListServersResponse,
  DiscoverToolsResponse,
  ExecuteToolResponse,
  ServerStatusResponse
} from '@/types/mcp-types';

// ============================================
// Service Configuration
// ============================================

const MCP_API_BASE = '/api/mcp';

const createHeaders = (): HeadersInit => {
  const token = typeof window !== 'undefined' 
    ? localStorage.getItem('jwt_token') || sessionStorage.getItem('jwt_token')
    : null;
  
  return {
    'Content-Type': 'application/json',
    'Accept': 'application/json',
    ...(token && { 'Authorization': `Bearer ${token}` })
  };
};

const handleApiResponse = async <T>(response: Response): Promise<T> => {
  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(`MCP API Error ${response.status}: ${errorText}`);
  }
  return response.json();
};

// ============================================
// Server Management Functions (8 lines max)
// ============================================

export const listServers = async (): Promise<MCPServerInfo[]> => {
  const response = await fetch(`${MCP_API_BASE}/servers`, {
    method: 'GET',
    headers: createHeaders()
  });
  const result = await handleApiResponse<ListServersResponse>(response);
  return result.data || [];
};

export const getServerStatus = async (serverName: string): Promise<MCPServerInfo | null> => {
  const response = await fetch(`${MCP_API_BASE}/servers/${serverName}/status`, {
    method: 'GET',
    headers: createHeaders()
  });
  const result = await handleApiResponse<MCPApiResponse<MCPServerInfo>>(response);
  return result.data || null;
};

export const connectServer = async (serverName: string): Promise<boolean> => {
  const response = await fetch(`${MCP_API_BASE}/servers/${serverName}/connect`, {
    method: 'POST',
    headers: createHeaders()
  });
  const result = await handleApiResponse<MCPApiResponse>(response);
  return result.success;
};

export const disconnectServer = async (serverName: string): Promise<boolean> => {
  const response = await fetch(`${MCP_API_BASE}/servers/${serverName}/disconnect`, {
    method: 'POST',
    headers: createHeaders()
  });
  const result = await handleApiResponse<MCPApiResponse>(response);
  return result.success;
};

// ============================================
// Tool Management Functions (8 lines max)
// ============================================

export const discoverTools = async (serverName?: string): Promise<MCPTool[]> => {
  const url = serverName 
    ? `${MCP_API_BASE}/tools?server=${serverName}` 
    : `${MCP_API_BASE}/tools`;
  const response = await fetch(url, {
    method: 'GET',
    headers: createHeaders()
  });
  const result = await handleApiResponse<DiscoverToolsResponse>(response);
  return result.data || [];
};

export const executeTool = async (
  serverName: string,
  toolName: string,
  arguments_: Record<string, any>
): Promise<MCPToolResult> => {
  const response = await fetch(`${MCP_API_BASE}/tools/execute`, {
    method: 'POST',
    headers: createHeaders(),
    body: JSON.stringify({ server_name: serverName, tool_name: toolName, arguments: arguments_ })
  });
  const result = await handleApiResponse<ExecuteToolResponse>(response);
  if (!result.success || !result.data) {
    throw new Error(result.message || 'Tool execution failed');
  }
  return result.data;
};

export const getToolSchema = async (
  serverName: string,
  toolName: string
): Promise<Record<string, any>> => {
  const response = await fetch(`${MCP_API_BASE}/tools/${serverName}/${toolName}/schema`, {
    method: 'GET',
    headers: createHeaders()
  });
  return handleApiResponse<Record<string, any>>(response);
};

// ============================================
// Resource Management Functions (8 lines max)
// ============================================

export const listResources = async (serverName: string): Promise<MCPResource[]> => {
  const response = await fetch(`${MCP_API_BASE}/resources?server=${serverName}`, {
    method: 'GET',
    headers: createHeaders()
  });
  const result = await handleApiResponse<MCPApiResponse<MCPResource[]>>(response);
  return result.data || [];
};

export const fetchResource = async (
  serverName: string,
  uri: string
): Promise<MCPResource | null> => {
  const response = await fetch(`${MCP_API_BASE}/resources/fetch`, {
    method: 'POST',
    headers: createHeaders(),
    body: JSON.stringify({ server_name: serverName, uri })
  });
  const result = await handleApiResponse<MCPApiResponse<MCPResource>>(response);
  return result.data || null;
};

// ============================================
// Cache Management Functions (8 lines max)
// ============================================

export const clearCache = async (
  serverName?: string,
  cacheType?: string
): Promise<boolean> => {
  const response = await fetch(`${MCP_API_BASE}/cache/clear`, {
    method: 'POST',
    headers: createHeaders(),
    body: JSON.stringify({ server_name: serverName, cache_type: cacheType })
  });
  const result = await handleApiResponse<MCPApiResponse>(response);
  return result.success;
};

// ============================================
// Health Check Functions (8 lines max)
// ============================================

export const healthCheck = async (): Promise<boolean> => {
  try {
    const response = await fetch(`${MCP_API_BASE}/health`, {
      method: 'GET',
      headers: createHeaders()
    });
    return response.ok;
  } catch {
    return false;
  }
};

export const serverHealthCheck = async (serverName: string): Promise<boolean> => {
  try {
    const response = await fetch(`${MCP_API_BASE}/servers/${serverName}/health`, {
      method: 'GET',
      headers: createHeaders()
    });
    return response.ok;
  } catch {
    return false;
  }
};

// ============================================
// Batch Operations (8 lines max)
// ============================================

export const getServerConnections = async (): Promise<MCPServerInfo[]> => {
  const response = await fetch(`${MCP_API_BASE}/connections`, {
    method: 'GET',
    headers: createHeaders()
  });
  const result = await handleApiResponse<ServerStatusResponse>(response);
  return result.data || [];
};

export const refreshAllConnections = async (): Promise<boolean> => {
  const response = await fetch(`${MCP_API_BASE}/connections/refresh`, {
    method: 'POST',
    headers: createHeaders()
  });
  const result = await handleApiResponse<MCPApiResponse>(response);
  return result.success;
};