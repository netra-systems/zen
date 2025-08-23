// Mock MCP Client Service - Prevents 404 errors in tests
// Provides complete mock implementation for all MCP service functions

import type {
  MCPServerInfo,
  MCPTool,
  MCPToolResult,
  MCPResource,
  MCPApiResponse,
  ListServersResponse,
  DiscoverToolsResponse,
  ExecuteToolResponse,
  ServerStatusResponse,
  MCPServerStatus
} from '@/types/mcp-types';

// ============================================
// Mock Data Factory Functions
// ============================================

const createMockServer = (overrides?: Partial<MCPServerInfo>): MCPServerInfo => ({
  id: 'mock-server-1',
  name: 'mock-server',
  url: 'http://localhost:3001',
  transport: 'HTTP',
  status: 'CONNECTED' as MCPServerStatus,
  created_at: new Date().toISOString(),
  updated_at: new Date().toISOString(),
  ...overrides
});

const createMockTool = (overrides?: Partial<MCPTool>): MCPTool => ({
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

const createMockToolResult = (overrides?: Partial<MCPToolResult>): MCPToolResult => ({
  tool_name: 'mock-tool',
  server_name: 'mock-server',
  content: [{ type: 'text', text: 'Mock result content' }],
  is_error: false,
  execution_time_ms: 150,
  ...overrides
});

const createMockResource = (overrides?: Partial<MCPResource>): MCPResource => ({
  uri: 'mock://resource/1',
  name: 'Mock Resource',
  description: 'Mock MCP resource for testing',
  mimeType: 'text/plain',
  content: 'Mock resource content',
  ...overrides
});

// ============================================
// Mock State Management
// ============================================

let mockServers: MCPServerInfo[] = [createMockServer()];
let mockTools: MCPTool[] = [createMockTool()];
let mockResources: MCPResource[] = [createMockResource()];

// ============================================
// Server Management Mock Functions
// ============================================

export const listServers = jest.fn().mockImplementation(async (): Promise<MCPServerInfo[]> => {
  return Promise.resolve(mockServers);
});

export const getServerStatus = jest.fn().mockImplementation(async (serverName: string): Promise<MCPServerInfo | null> => {
  const server = mockServers.find(s => s.name === serverName);
  return Promise.resolve(server || null);
});

export const connectServer = jest.fn().mockImplementation(async (serverName: string): Promise<boolean> => {
  const serverIndex = mockServers.findIndex(s => s.name === serverName);
  if (serverIndex >= 0) {
    mockServers[serverIndex].status = 'CONNECTED';
    return Promise.resolve(true);
  }
  return Promise.resolve(false);
});

export const disconnectServer = jest.fn().mockImplementation(async (serverName: string): Promise<boolean> => {
  const serverIndex = mockServers.findIndex(s => s.name === serverName);
  if (serverIndex >= 0) {
    mockServers[serverIndex].status = 'DISCONNECTED';
    return Promise.resolve(true);
  }
  return Promise.resolve(false);
});

// ============================================
// Tool Management Mock Functions
// ============================================

export const discoverTools = jest.fn().mockImplementation(async (serverName?: string): Promise<MCPTool[]> => {
  if (serverName) {
    return Promise.resolve(mockTools.filter(t => t.server_name === serverName));
  }
  return Promise.resolve(mockTools);
});

export const executeTool = jest.fn().mockImplementation(async (
  serverName: string,
  toolName: string,
  arguments_: Record<string, any>
): Promise<MCPToolResult> => {
  const result = createMockToolResult({
    tool_name: toolName,
    server_name: serverName
  });
  return Promise.resolve(result);
});

export const getToolSchema = jest.fn().mockImplementation(async (
  serverName: string,
  toolName: string
): Promise<Record<string, any>> => {
  return Promise.resolve({
    type: 'object',
    properties: {
      input: { type: 'string', description: 'Mock schema' }
    }
  });
});

// ============================================
// Resource Management Mock Functions
// ============================================

export const listResources = jest.fn().mockImplementation(async (serverName: string): Promise<MCPResource[]> => {
  return Promise.resolve(mockResources);
});

export const fetchResource = jest.fn().mockImplementation(async (
  serverName: string,
  uri: string
): Promise<MCPResource | null> => {
  const resource = mockResources.find(r => r.uri === uri);
  return Promise.resolve(resource || null);
});

// ============================================
// Cache Management Mock Functions
// ============================================

export const clearCache = jest.fn().mockImplementation(async (
  serverName?: string,
  cacheType?: string
): Promise<boolean> => {
  return Promise.resolve(true);
});

// ============================================
// Health Check Mock Functions
// ============================================

export const healthCheck = jest.fn().mockImplementation(async (): Promise<boolean> => {
  return Promise.resolve(true);
});

export const serverHealthCheck = jest.fn().mockImplementation(async (serverName: string): Promise<boolean> => {
  return Promise.resolve(true);
});

// ============================================
// Batch Operations Mock Functions
// ============================================

export const getServerConnections = jest.fn().mockImplementation(async (): Promise<MCPServerInfo[]> => {
  return Promise.resolve(mockServers.filter(s => s.status === 'CONNECTED'));
});

export const refreshAllConnections = jest.fn().mockImplementation(async (): Promise<boolean> => {
  return Promise.resolve(true);
});

// ============================================
// Mock State Utilities
// ============================================

export const __mockSetServers = (servers: MCPServerInfo[]) => {
  mockServers = servers;
};

export const __mockSetTools = (tools: MCPTool[]) => {
  mockTools = tools;
};

export const __mockSetResources = (resources: MCPResource[]) => {
  mockResources = resources;
};

export const __mockReset = () => {
  mockServers = [createMockServer()];
  mockTools = [createMockTool()];
  mockResources = [createMockResource()];
  
  // Reset all jest mock functions
  Object.values(module.exports).forEach(fn => {
    if (jest.isMockFunction(fn)) {
      fn.mockClear();
    }
  });
};

// ============================================
// Mock Factory Exports for Tests
// ============================================

export const mockFactories = {
  createMockServer,
  createMockTool,
  createMockToolResult,
  createMockResource
};