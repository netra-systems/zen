import { http, HttpResponse } from 'msw';
import { User } from '@/types/unified';
import type { 
  MCPServerInfo, 
  MCPTool, 
  MCPToolResult, 
  MCPResource 
} from '@/types/mcp-types';

export const handlers = [
  // Mock for login
  http.post('/api/login', async ({ request }) => {
    const body = await request.json() as { username: string };
    if (body.username === 'testuser') {
      const user: User = {
        id: 'c7b3d8e0-5e0b-4b0f-8b3a-3b9f4b3d3b3d',
        full_name: 'John Maverick',
        email: 'testuser@example.com',
      };
      return HttpResponse.json(user);
    } else {
      return new HttpResponse(null, { status: 401 });
    }
  }),

  // Mock for logout
  http.post('/api/logout', () => {
    return new HttpResponse(null, { status: 200 });
  }),

  // Mock for user settings
  http.get('/api/user/settings', () => {
    return HttpResponse.json({
      theme: 'dark',
    });
  }),

  // Mock for dashboard data
  http.get('/api/dashboard', () => {
    return HttpResponse.json({
      metrics: [
        { name: 'Metric 1', value: 123 },
        { name: 'Metric 2', value: 456 },
      ],
    });
  }),

  // Mock for DeepAgent chat
  http.post('/api/chat', async ({ request }) => {
    const body = await request.json() as { message: string };
    return HttpResponse.json({
      reply: `You said: ${body.message}`,
    });
  }),

  // ============================================
  // MCP API Mock Endpoints
  // ============================================

  // Mock MCP Servers endpoints
  http.get('/api/mcp/servers', () => {
    const mockServers: MCPServerInfo[] = [
      {
        id: 'mock-server-1',
        name: 'mock-server',
        url: 'http://localhost:3001',
        transport: 'HTTP',
        status: 'CONNECTED',
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString()
      }
    ];
    return HttpResponse.json({ data: mockServers, success: true });
  }),

  http.get('/api/mcp/servers/:serverName/status', ({ params }) => {
    const mockServer: MCPServerInfo = {
      id: 'mock-server-1',
      name: params.serverName as string,
      url: 'http://localhost:3001',
      transport: 'HTTP',
      status: 'CONNECTED',
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString()
    };
    return HttpResponse.json({ data: mockServer, success: true });
  }),

  http.post('/api/mcp/servers/:serverName/connect', ({ params }) => {
    return HttpResponse.json({ success: true, message: `Connected to ${params.serverName}` });
  }),

  http.post('/api/mcp/servers/:serverName/disconnect', ({ params }) => {
    return HttpResponse.json({ success: true, message: `Disconnected from ${params.serverName}` });
  }),

  // Mock MCP Tools endpoints
  http.get('/api/mcp/tools', ({ request }) => {
    const url = new URL(request.url);
    const serverName = url.searchParams.get('server');
    
    const mockTools: MCPTool[] = [
      {
        name: 'mock-tool',
        server_name: serverName || 'mock-server',
        description: 'Mock MCP tool for testing',
        input_schema: {
          type: 'object',
          properties: {
            input: { type: 'string', description: 'Test input' }
          }
        }
      }
    ];
    return HttpResponse.json({ data: mockTools, success: true });
  }),

  http.post('/api/mcp/tools/execute', async ({ request }) => {
    const body = await request.json() as { 
      server_name: string; 
      tool_name: string; 
      arguments: Record<string, any> 
    };
    
    const mockResult: MCPToolResult = {
      tool_name: body.tool_name,
      server_name: body.server_name,
      content: [{ type: 'text', text: 'Mock execution result' }],
      is_error: false,
      execution_time_ms: 150
    };
    return HttpResponse.json({ data: mockResult, success: true });
  }),

  http.get('/api/mcp/tools/:serverName/:toolName/schema', ({ params }) => {
    const mockSchema = {
      type: 'object',
      properties: {
        input: { type: 'string', description: 'Mock schema input' }
      }
    };
    return HttpResponse.json(mockSchema);
  }),

  // Mock MCP Resources endpoints
  http.get('/api/mcp/resources', ({ request }) => {
    const mockResources: MCPResource[] = [
      {
        uri: 'mock://resource/1',
        name: 'Mock Resource',
        description: 'Mock MCP resource for testing',
        mimeType: 'text/plain',
        content: 'Mock resource content'
      }
    ];
    return HttpResponse.json({ data: mockResources, success: true });
  }),

  http.post('/api/mcp/resources/fetch', async ({ request }) => {
    const body = await request.json() as { server_name: string; uri: string };
    
    const mockResource: MCPResource = {
      uri: body.uri,
      name: 'Fetched Mock Resource',
      description: 'Mock resource fetched for testing',
      mimeType: 'text/plain',
      content: `Mock content for ${body.uri}`
    };
    return HttpResponse.json({ data: mockResource, success: true });
  }),

  // Mock MCP Cache endpoints
  http.post('/api/mcp/cache/clear', async ({ request }) => {
    const body = await request.json() as { server_name?: string; cache_type?: string };
    return HttpResponse.json({ success: true, message: 'Cache cleared successfully' });
  }),

  // Mock MCP Health endpoints
  http.get('/api/mcp/health', () => {
    return HttpResponse.json({ status: 'healthy', timestamp: new Date().toISOString() });
  }),

  http.get('/api/mcp/servers/:serverName/health', ({ params }) => {
    return HttpResponse.json({ 
      status: 'healthy', 
      server: params.serverName,
      timestamp: new Date().toISOString() 
    });
  }),

  // Mock MCP Connections endpoints
  http.get('/api/mcp/connections', () => {
    const mockConnections: MCPServerInfo[] = [
      {
        id: 'connected-server-1',
        name: 'connected-server',
        url: 'http://localhost:3001',
        transport: 'HTTP',
        status: 'CONNECTED',
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString()
      }
    ];
    return HttpResponse.json({ data: mockConnections, success: true });
  }),

  http.post('/api/mcp/connections/refresh', () => {
    return HttpResponse.json({ success: true, message: 'All connections refreshed' });
  }),
];