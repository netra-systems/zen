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
import { authInterceptor } from '@/lib/auth-interceptor';
import { logger } from '@/lib/logger';

// ============================================
// Service Configuration
// ============================================

const MCP_API_BASE = '/api/mcp';

// All API calls now use auth interceptor for consistent header management

const handleApiResponse = async <T>(response: Response | any): Promise<T> => {
  if (!response.ok) {
    let errorText = '';
    try {
      // Handle both real Response objects and jest-fetch-mock objects
      if (typeof response.text === 'function') {
        errorText = await response.text();
      } else if (response._bodyText) {
        // jest-fetch-mock stores body as _bodyText
        errorText = response._bodyText;
      } else if (response.body) {
        // Fallback for other mock implementations
        errorText = typeof response.body === 'string' ? response.body : JSON.stringify(response.body);
      } else {
        errorText = `HTTP ${response.status}`;
      }
    } catch {
      errorText = `HTTP ${response.status}`;
    }

    let errorMessage: string;
    try {
      const parsed = JSON.parse(errorText);
      errorMessage = parsed.detail || parsed.message || parsed.error || `MCP API Error ${response.status}: ${errorText}`;
    } catch {
      errorMessage = errorText || `MCP API Error ${response.status}`;
    }
    throw new Error(errorMessage);
  }

  // Handle both real Response objects and jest-fetch-mock objects for success responses
  try {
    if (typeof response.json === 'function') {
      return await response.json();
    } else if (response._bodyText) {
      // jest-fetch-mock stores body as _bodyText
      return JSON.parse(response._bodyText);
    } else if (response.body) {
      // Fallback for other mock implementations
      return typeof response.body === 'string' ? JSON.parse(response.body) : response.body;
    } else {
      // Last resort - assume response itself is the data
      return response as T;
    }
  } catch (error) {
    logger.error('Failed to parse API response', error as Error, {
      component: 'MCPClientService',
      action: 'handleApiResponse'
    });
    throw new Error('Failed to parse API response: ' + (error as Error).message);
  }
};

// ============================================
// Server Management Functions (8 lines max)
// ============================================

export const listServers = async (): Promise<MCPServerInfo[]> => {
  try {
    const response = await authInterceptor.get(`${MCP_API_BASE}/servers`);
    const result = await handleApiResponse<ListServersResponse>(response);
    return result.data || [];
  } catch (error) {
    logger.error('Failed to list MCP servers', error as Error, {
      component: 'MCPClientService',
      action: 'listServers'
    });
    throw error;
  }
};

export const getServerStatus = async (serverName: string): Promise<MCPServerInfo | null> => {
  try {
    const response = await authInterceptor.get(`${MCP_API_BASE}/servers/${serverName}/status`);
    const result = await handleApiResponse<MCPApiResponse<MCPServerInfo>>(response);
    return result.data || null;
  } catch (error) {
    logger.error('Failed to get MCP server status', error as Error, {
      component: 'MCPClientService',
      action: 'getServerStatus',
      serverName
    });
    throw error;
  }
};

export const connectServer = async (serverName: string): Promise<boolean> => {
  try {
    const response = await authInterceptor.post(`${MCP_API_BASE}/servers/${serverName}/connect`);
    const result = await handleApiResponse<MCPApiResponse>(response);
    return result.success;
  } catch (error) {
    logger.error('Failed to connect MCP server', error as Error, {
      component: 'MCPClientService',
      action: 'connectServer',
      serverName
    });
    throw error;
  }
};

export const disconnectServer = async (serverName: string): Promise<boolean> => {
  try {
    const response = await authInterceptor.post(`${MCP_API_BASE}/servers/${serverName}/disconnect`);
    const result = await handleApiResponse<MCPApiResponse>(response);
    return result.success;
  } catch (error) {
    logger.error('Failed to disconnect MCP server', error as Error, {
      component: 'MCPClientService',
      action: 'disconnectServer',
      serverName
    });
    throw error;
  }
};

// ============================================
// Tool Management Functions (8 lines max)
// ============================================

export const discoverTools = async (serverName?: string): Promise<MCPTool[]> => {
  try {
    const url = serverName 
      ? `${MCP_API_BASE}/tools?server=${serverName}` 
      : `${MCP_API_BASE}/tools`;
    const response = await authInterceptor.get(url);
    const result = await handleApiResponse<DiscoverToolsResponse>(response);
    return result.data || [];
  } catch (error) {
    logger.error('Failed to discover MCP tools', error as Error, {
      component: 'MCPClientService',
      action: 'discoverTools',
      serverName
    });
    throw error;
  }
};

export const executeTool = async (
  serverName: string,
  toolName: string,
  arguments_: Record<string, any>
): Promise<MCPToolResult> => {
  try {
    const response = await authInterceptor.post(`${MCP_API_BASE}/tools/execute`, {
      server_name: serverName, 
      tool_name: toolName, 
      arguments: arguments_
    });
    const result = await handleApiResponse<ExecuteToolResponse>(response);
    if (!result.success || !result.data) {
      throw new Error(result.message || 'Tool execution failed');
    }
    return result.data;
  } catch (error) {
    logger.error('Failed to execute MCP tool', error as Error, {
      component: 'MCPClientService',
      action: 'executeTool',
      serverName,
      toolName
    });
    throw error;
  }
};

export const getToolSchema = async (
  serverName: string,
  toolName: string
): Promise<Record<string, any>> => {
  const response = await authInterceptor.get(`${MCP_API_BASE}/tools/${serverName}/${toolName}/schema`);
  return handleApiResponse<Record<string, any>>(response);
};

// ============================================
// Resource Management Functions (8 lines max)
// ============================================

export const listResources = async (serverName: string): Promise<MCPResource[]> => {
  const response = await authInterceptor.get(`${MCP_API_BASE}/resources?server=${serverName}`);
  const result = await handleApiResponse<MCPApiResponse<MCPResource[]>>(response);
  return result.data || [];
};

export const fetchResource = async (
  serverName: string,
  uri: string
): Promise<MCPResource | null> => {
  const response = await authInterceptor.post(`${MCP_API_BASE}/resources/fetch`, {
    server_name: serverName, 
    uri
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
  const response = await authInterceptor.post(`${MCP_API_BASE}/cache/clear`, {
    server_name: serverName, 
    cache_type: cacheType
  });
  const result = await handleApiResponse<MCPApiResponse>(response);
  return result.success;
};

// ============================================
// Health Check Functions (8 lines max)
// ============================================

export const healthCheck = async (): Promise<boolean> => {
  try {
    const response = await authInterceptor.get(`${MCP_API_BASE}/health`);
    return response.ok;
  } catch {
    return false;
  }
};

export const serverHealthCheck = async (serverName: string): Promise<boolean> => {
  try {
    const response = await authInterceptor.get(`${MCP_API_BASE}/servers/${serverName}/health`);
    return response.ok;
  } catch {
    return false;
  }
};

// ============================================
// Batch Operations (8 lines max)
// ============================================

export const getServerConnections = async (): Promise<MCPServerInfo[]> => {
  const response = await authInterceptor.get(`${MCP_API_BASE}/connections`);
  const result = await handleApiResponse<ServerStatusResponse>(response);
  return result.data || [];
};

export const refreshAllConnections = async (): Promise<boolean> => {
  const response = await authInterceptor.post(`${MCP_API_BASE}/connections/refresh`);
  const result = await handleApiResponse<MCPApiResponse>(response);
  return result.success;
};