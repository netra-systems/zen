// useMCPTools Hook - React hook for MCP functionality
// Provides tools discovery, execution, and server management

import { useState, useEffect, useCallback, useMemo } from 'react';
import { useUnifiedChatStore } from '@/store/unified-chat';
import * as mcpService from '@/services/mcp-client-service';
import type { 
  MCPTool, 
  MCPToolExecution, 
  MCPServerInfo, 
  MCPToolResult,
  UseMCPToolsReturn,
  MCPServerStatus
} from '@/types/mcp-types';

// ============================================
// Hook Implementation
// ============================================

export const useMCPTools = (): UseMCPToolsReturn => {
  const { mcpState } = useUnifiedChatStore();
  
  const [tools, setTools] = useState<MCPTool[]>([]);
  const [servers, setServers] = useState<MCPServerInfo[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | undefined>();

  // ============================================
  // Derived State (8 lines max)
  // ============================================

  const executions = useMemo((): MCPToolExecution[] => {
    if (!mcpState?.active_executions) return [];
    return Array.from(mcpState.active_executions.values());
  }, [mcpState?.active_executions]);

  const serverStatuses = useMemo((): Map<string, MCPServerStatus> => {
    const statuses = new Map<string, MCPServerStatus>();
    servers.forEach(server => {
      statuses.set(server.name, server.status);
    });
    return statuses;
  }, [servers]);

  // ============================================
  // API Functions (8 lines max)
  // ============================================

  const loadServers = useCallback(async (): Promise<void> => {
    try {
      setIsLoading(true);
      const serverList = await mcpService.listServers();
      setServers(serverList);
      setError(undefined);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load servers');
    } finally {
      setIsLoading(false);
    }
  }, []);

  const loadTools = useCallback(async (serverName?: string): Promise<void> => {
    try {
      setIsLoading(true);
      const toolList = await mcpService.discoverTools(serverName);
      setTools(toolList);
      setError(undefined);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load tools');
    } finally {
      setIsLoading(false);
    }
  }, []);

  const executeTool = useCallback(async (
    serverName: string,
    toolName: string,
    args: Record<string, any>
  ): Promise<MCPToolResult> => {
    try {
      setIsLoading(true);
      const result = await mcpService.executeTool(serverName, toolName, args);
      setError(undefined);
      return result;
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Tool execution failed';
      setError(errorMessage);
      throw new Error(errorMessage);
    } finally {
      setIsLoading(false);
    }
  }, []);

  const getServerStatus = useCallback((serverName: string): MCPServerStatus => {
    return serverStatuses.get(serverName) || 'DISCONNECTED';
  }, [serverStatuses]);

  const refreshTools = useCallback(async (): Promise<void> => {
    await Promise.all([loadServers(), loadTools()]);
  }, [loadServers, loadTools]);

  const connectToServer = useCallback(async (serverName: string): Promise<boolean> => {
    try {
      setIsLoading(true);
      const success = await mcpService.connectServer(serverName);
      if (success) {
        await loadServers(); // Refresh server status
      }
      return success;
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Connection failed');
      return false;
    } finally {
      setIsLoading(false);
    }
  }, [loadServers]);

  const disconnectFromServer = useCallback(async (serverName: string): Promise<boolean> => {
    try {
      setIsLoading(true);
      const success = await mcpService.disconnectServer(serverName);
      if (success) {
        await loadServers(); // Refresh server status
      }
      return success;
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Disconnection failed');
      return false;
    } finally {
      setIsLoading(false);
    }
  }, [loadServers]);

  // ============================================
  // Effects (8 lines max)
  // ============================================

  useEffect(() => {
    loadServers();
    loadTools();
  }, [loadServers, loadTools]);

  useEffect(() => {
    const interval = setInterval(async () => {
      try {
        await loadServers(); // Periodic health check
      } catch {
        // Silently handle background refresh errors
      }
    }, 30000); // Every 30 seconds

    return () => clearInterval(interval);
  }, [loadServers]);

  // ============================================
  // Return Object
  // ============================================

  return {
    tools,
    executions,
    servers,
    executeTool,
    getServerStatus,
    refreshTools,
    isLoading,
    error,
    // Additional utility functions
    connectToServer,
    disconnectFromServer,
    loadServers,
    loadTools
  } as UseMCPToolsReturn & {
    connectToServer: (serverName: string) => Promise<boolean>;
    disconnectFromServer: (serverName: string) => Promise<boolean>;
    loadServers: () => Promise<void>;
    loadTools: (serverName?: string) => Promise<void>;
  };
};