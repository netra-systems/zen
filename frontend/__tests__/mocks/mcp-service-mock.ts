// MCP Service Mock - Centralized mock utilities for MCP testing
// Provides consistent mock data and utilities across all MCP-related tests

import type {
  MCPServerInfo,
  MCPTool,
  MCPToolResult,
  MCPResource,
  MCPServerStatus,
  MCPToolExecution,
  UseMCPToolsReturn
} from '@/types/mcp-types';

// ============================================
// Mock Data Factory Functions
// ============================================

export const createMockServer = (overrides?: Partial<MCPServerInfo>): MCPServerInfo => {
  const fixedDate = '2025-08-25T06:33:34.322Z';
  return {
    id: 'mock-server-1',
    name: 'mock-server',
    url: 'http://localhost:3001',
    transport: 'HTTP',
    status: 'CONNECTED' as MCPServerStatus,
    created_at: fixedDate,
    updated_at: fixedDate,
    ...overrides
  };
};

export const createMockTool = (overrides?: Partial<MCPTool>): MCPTool => ({
  name: 'mock-tool',
  server_name: 'mock-server',
  description: 'Mock MCP tool for testing',
  input_schema: {
    type: 'object',
    properties: {
      input: { type: 'string', description: 'Test input' }
    }
  },
  ...overrides
});

export const createMockToolResult = (overrides?: Partial<MCPToolResult>): MCPToolResult => ({
  tool_name: 'mock-tool',
  server_name: 'mock-server',
  content: [{ type: 'text', text: 'Mock result content' }],
  is_error: false,
  execution_time_ms: 150,
  ...overrides
});

export const createMockResource = (overrides?: Partial<MCPResource>): MCPResource => ({
  uri: 'mock://resource/1',
  name: 'Mock Resource',
  description: 'Mock MCP resource for testing',
  mimeType: 'text/plain',
  content: 'Mock resource content',
  ...overrides
});

export const createMockExecution = (overrides?: Partial<MCPToolExecution>): MCPToolExecution => {
  const fixedDate = '2025-08-25T06:33:34.322Z';
  return {
    id: 'exec-1',
    tool_name: 'mock-tool',
    server_name: 'mock-server',
    status: 'COMPLETED',
    arguments: { param1: 'value1' },
    started_at: fixedDate,
    duration_ms: 1500,
    ...overrides
  };
};

// ============================================
// Mock State Management
// ============================================

class MCPMockState {
  private servers: MCPServerInfo[] = [];
  private tools: MCPTool[] = [];
  private resources: MCPResource[] = [];
  private executions: MCPToolExecution[] = [];

  constructor() {
    this.reset();
  }

  // Server management
  setServers(servers: MCPServerInfo[]): void {
    this.servers = servers;
  }

  getServers(): MCPServerInfo[] {
    return this.servers;
  }

  addServer(server: MCPServerInfo): void {
    this.servers.push(server);
  }

  updateServer(name: string, updates: Partial<MCPServerInfo>): void {
    const index = this.servers.findIndex(s => s.name === name);
    if (index >= 0) {
      this.servers[index] = { ...this.servers[index], ...updates };
    }
  }

  // Tool management
  setTools(tools: MCPTool[]): void {
    this.tools = tools;
  }

  getTools(serverName?: string): MCPTool[] {
    if (serverName) {
      return this.tools.filter(t => t.server_name === serverName);
    }
    return this.tools;
  }

  addTool(tool: MCPTool): void {
    this.tools.push(tool);
  }

  // Resource management
  setResources(resources: MCPResource[]): void {
    this.resources = resources;
  }

  getResources(): MCPResource[] {
    return this.resources;
  }

  addResource(resource: MCPResource): void {
    this.resources.push(resource);
  }

  // Execution management
  setExecutions(executions: MCPToolExecution[]): void {
    this.executions = executions;
  }

  getExecutions(): MCPToolExecution[] {
    return this.executions;
  }

  addExecution(execution: MCPToolExecution): void {
    this.executions.push(execution);
  }

  // Reset all state to defaults
  reset(): void {
    this.servers = [createMockServer()];
    this.tools = [createMockTool()];
    this.resources = [createMockResource()];
    this.executions = [createMockExecution()];
  }
}

// Global mock state instance
export const mcpMockState = new MCPMockState();

// ============================================
// Mock useMCPTools Hook
// ============================================

export const createMockUseMCPTools = (overrides?: Partial<UseMCPToolsReturn>): UseMCPToolsReturn => ({
  tools: mcpMockState.getTools(),
  executions: mcpMockState.getExecutions(),
  servers: mcpMockState.getServers(),
  isLoading: false,
  error: undefined,
  executeTool: jest.fn().mockImplementation(async (serverName: string, toolName: string, args: Record<string, any>) => {
    const result = createMockToolResult({ tool_name: toolName, server_name: serverName });
    return Promise.resolve(result);
  }),
  getServerStatus: jest.fn().mockImplementation((serverName: string): MCPServerStatus => {
    const server = mcpMockState.getServers().find(s => s.name === serverName);
    return server?.status || 'DISCONNECTED';
  }),
  refreshTools: jest.fn().mockResolvedValue(undefined),
  ...overrides
});

// ============================================
// Test Setup Utilities
// ============================================

export const setupMCPMocks = () => {
  // Reset state before each test
  mcpMockState.reset();

  // Mock the MCP client service module
  jest.doMock('@/services/mcp-client-service', () => {
    class MCPClientService {
      static async initialize() {
        return Promise.resolve();
      }

      static async connect() {
        return Promise.resolve(true);
      }

      static async disconnect() {
        return Promise.resolve(true);
      }

      static async getAvailableTools() {
        return Promise.resolve(mcpMockState.getTools());
      }

      static async executeTool(serverName: string, toolName: string, arguments_: Record<string, any>) {
        const result = createMockToolResult({ tool_name: toolName, server_name: serverName });
        return Promise.resolve(result);
      }

      static getConnectionStatus() {
        return 'CONNECTED';
      }
    }

    return {
      default: MCPClientService,
      MCPClientService,
      listServers: jest.fn().mockImplementation(() => Promise.resolve(mcpMockState.getServers())),
      getServerStatus: jest.fn().mockImplementation((serverName: string) => {
        const server = mcpMockState.getServers().find(s => s.name === serverName);
        return Promise.resolve(server || null);
      }),
      connectServer: jest.fn().mockImplementation((serverName: string) => {
        mcpMockState.updateServer(serverName, { status: 'CONNECTED' });
        return Promise.resolve(true);
      }),
      disconnectServer: jest.fn().mockImplementation((serverName: string) => {
        mcpMockState.updateServer(serverName, { status: 'DISCONNECTED' });
        return Promise.resolve(true);
      }),
      discoverTools: jest.fn().mockImplementation((serverName?: string) => {
        return Promise.resolve(mcpMockState.getTools(serverName));
      }),
      executeTool: jest.fn().mockImplementation((serverName: string, toolName: string, args: Record<string, any>) => {
        const result = createMockToolResult({ tool_name: toolName, server_name: serverName });
        return Promise.resolve(result);
      }),
      getToolSchema: jest.fn().mockResolvedValue({
        type: 'object',
        properties: {
          input: { type: 'string', description: 'Mock schema' }
        }
      }),
      listResources: jest.fn().mockImplementation(() => Promise.resolve(mcpMockState.getResources())),
      fetchResource: jest.fn().mockImplementation((serverName: string, uri: string) => {
        const resource = mcpMockState.getResources().find(r => r.uri === uri);
        return Promise.resolve(resource || null);
      }),
      clearCache: jest.fn().mockResolvedValue(true),
      healthCheck: jest.fn().mockResolvedValue(true),
      serverHealthCheck: jest.fn().mockResolvedValue(true),
      getServerConnections: jest.fn().mockImplementation(() => {
        return Promise.resolve(mcpMockState.getServers().filter(s => s.status === 'CONNECTED'));
      }),
      refreshAllConnections: jest.fn().mockResolvedValue(true)
    };
  });

  // Don't mock the useMCPTools hook - let it use the mocked service
};

export const cleanupMCPMocks = () => {
  jest.dontMock('@/services/mcp-client-service');
  mcpMockState.reset();
};

// ============================================
// Test Assertion Helpers
// ============================================

export const expectMCPServiceCalled = (serviceFn: jest.MockedFunction<any>, ...args: any[]) => {
  expect(serviceFn).toHaveBeenCalledWith(...args);
};

export const expectMCPServiceNotCalled = (serviceFn: jest.MockedFunction<any>) => {
  expect(serviceFn).not.toHaveBeenCalled();
};

export const expectMCPHookState = (hookReturn: UseMCPToolsReturn, expected: Partial<UseMCPToolsReturn>) => {
  if (expected.tools) {
    expect(hookReturn.tools).toHaveLength(expected.tools.length);
    expected.tools.forEach((tool, index) => {
      expect(hookReturn.tools[index]).toMatchObject({
        name: tool.name,
        server_name: tool.server_name,
        description: tool.description
      });
    });
  }
  if (expected.servers) {
    expect(hookReturn.servers).toHaveLength(expected.servers.length);
    expected.servers.forEach((server, index) => {
      expect(hookReturn.servers[index]).toMatchObject({
        id: server.id,
        name: server.name,
        url: server.url,
        transport: server.transport,
        status: server.status
      });
    });
  }
  if (expected.isLoading !== undefined) {
    expect(hookReturn.isLoading).toBe(expected.isLoading);
  }
  if (expected.error !== undefined) {
    expect(hookReturn.error).toBe(expected.error);
  }
};

// ============================================
// Scenario Builders
// ============================================

export const createDisconnectedServerScenario = () => {
  const server = createMockServer({ status: 'DISCONNECTED', name: 'disconnected-server' });
  mcpMockState.setServers([server]);
  return server;
};

export const createFailedExecutionScenario = () => {
  const execution = createMockExecution({ status: 'FAILED', id: 'failed-exec' });
  mcpMockState.setExecutions([execution]);
  return execution;
};

export const createMultiServerScenario = () => {
  const servers = [
    createMockServer({ name: 'server-1', status: 'CONNECTED' }),
    createMockServer({ name: 'server-2', status: 'DISCONNECTED', id: 'server-2' })
  ];
  mcpMockState.setServers(servers);
  return servers;
};