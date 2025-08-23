/**
 * MCP Client Service Mock Implementation
 * Comprehensive mock for MCP (Model Context Protocol) client service
 * Used in frontend integration tests to prevent real API calls
 */

export interface MCPServerInfo {
  id: string;
  name: string;
  url: string;
  transport: 'HTTP' | 'WEBSOCKET';
  status: 'CONNECTED' | 'DISCONNECTED' | 'ERROR';
  created_at: string;
  updated_at: string;
}

export interface MCPTool {
  name: string;
  server_name: string;
  description: string;
  input_schema: {
    type: string;
    properties: Record<string, any>;
  };
}

export interface MCPToolResult {
  tool_name: string;
  server_name: string;
  content: Array<{ type: string; text: string }>;
  is_error: boolean;
  execution_time_ms: number;
}

export interface MCPResource {
  uri: string;
  name: string;
  description: string;
  mimeType: string;
  content: string;
}

// Mock data factories
export const mockFactories = {
  createMockServer: (overrides: Partial<MCPServerInfo> = {}): MCPServerInfo => ({
    id: 'mock-server-1',
    name: 'mock-server',
    url: 'http://localhost:3001',
    transport: 'HTTP',
    status: 'CONNECTED',
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
    ...overrides
  }),

  createMockTool: (overrides: Partial<MCPTool> = {}): MCPTool => ({
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
  }),

  createMockToolResult: (overrides: Partial<MCPToolResult> = {}): MCPToolResult => ({
    tool_name: 'mock-tool',
    server_name: 'mock-server',
    content: [{ type: 'text', text: 'Mock result content' }],
    is_error: false,
    execution_time_ms: 150,
    ...overrides
  }),

  createMockResource: (overrides: Partial<MCPResource> = {}): MCPResource => ({
    uri: 'mock://resource/1',
    name: 'Mock Resource',
    description: 'Mock MCP resource for testing',
    mimeType: 'text/plain',
    content: 'Mock resource content',
    ...overrides
  })
};

// Global mock state
let mockServers: MCPServerInfo[] = [mockFactories.createMockServer()];
let mockTools: MCPTool[] = [mockFactories.createMockTool()];
let mockResources: MCPResource[] = [mockFactories.createMockResource()];

// Main MCP Client Service class mock
export class MCPClientService {
  static async initialize(): Promise<void> {
    return Promise.resolve();
  }

  static async connect(): Promise<boolean> {
    return Promise.resolve(true);
  }

  static async disconnect(): Promise<boolean> {
    return Promise.resolve(true);
  }

  static async getAvailableTools(): Promise<MCPTool[]> {
    return Promise.resolve(mockTools);
  }

  static async executeTool(
    serverName: string, 
    toolName: string, 
    arguments_: Record<string, any>
  ): Promise<MCPToolResult> {
    return Promise.resolve(mockFactories.createMockToolResult({
      tool_name: toolName,
      server_name: serverName
    }));
  }

  static getConnectionStatus(): string {
    return 'CONNECTED';
  }
}

// Individual service functions
export const listServers = jest.fn().mockResolvedValue(mockServers);

export const getServerStatus = jest.fn().mockImplementation((serverName: string) => {
  const server = mockServers.find(s => s.name === serverName);
  return Promise.resolve(server || null);
});

export const connectServer = jest.fn().mockResolvedValue(true);

export const disconnectServer = jest.fn().mockResolvedValue(true);

export const discoverTools = jest.fn().mockResolvedValue(mockTools);

export const executeTool = jest.fn().mockImplementation((
  serverName: string,
  toolName: string, 
  args: Record<string, any>
) => {
  return Promise.resolve(mockFactories.createMockToolResult({
    tool_name: toolName,
    server_name: serverName
  }));
});

export const getToolSchema = jest.fn().mockResolvedValue({
  type: 'object',
  properties: {
    input: { type: 'string', description: 'Mock schema' }
  }
});

export const listResources = jest.fn().mockResolvedValue(mockResources);

export const fetchResource = jest.fn().mockImplementation((uri: string) => {
  return Promise.resolve(mockFactories.createMockResource({ uri }));
});

export const clearCache = jest.fn().mockResolvedValue(true);

export const healthCheck = jest.fn().mockResolvedValue(true);

export const serverHealthCheck = jest.fn().mockImplementation((serverName: string) => {
  return Promise.resolve(true);
});

export const getServerConnections = jest.fn().mockImplementation(() => {
  return Promise.resolve(mockServers.filter(s => s.status === 'CONNECTED'));
});

export const refreshAllConnections = jest.fn().mockResolvedValue(true);

// Test utilities for mock state management
export const __mockSetServers = (servers: MCPServerInfo[]): void => {
  mockServers = servers;
};

export const __mockSetTools = (tools: MCPTool[]): void => {
  mockTools = tools;
};

export const __mockSetResources = (resources: MCPResource[]): void => {
  mockResources = resources;
};

export const __mockReset = (): void => {
  mockServers = [mockFactories.createMockServer()];
  mockTools = [mockFactories.createMockTool()];
  mockResources = [mockFactories.createMockResource()];
};

// Default export for compatibility
export default MCPClientService;