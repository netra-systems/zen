import { http, HttpResponse } from 'msw';
import { User } from '@/types/unified';
import type { 
  MCPServerInfo, 
  MCPTool, 
  MCPToolResult, 
  MCPResource 
} from '@/types/mcp-types';

export const handlers = [
  // Mock for login - return JWT token
  http.post('/api/auth/login', async ({ request }) => {
    const body = await request.json() as { username: string; password?: string; email?: string };
    if (body.username === 'testuser' || body.email === 'test@example.com') {
      const user: User = {
        id: 'c7b3d8e0-5e0b-4b0f-8b3a-3b9f4b3d3b3d',
        full_name: 'John Maverick',
        email: 'testuser@example.com',
      };
      const token = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjoidGVzdC11c2VyLTEyMyIsImVtYWlsIjoidGVzdEBleGFtcGxlLmNvbSIsImV4cCI6OTk5OTk5OTk5OX0.test-signature';
      return HttpResponse.json({ token, user, access_token: token, token_type: 'Bearer' });
    } else {
      return new HttpResponse(
        JSON.stringify({ error: 'Invalid credentials' }), 
        { status: 401 }
      );
    }
  }),

  // Legacy login endpoint for backward compatibility
  http.post('/api/login', async ({ request }) => {
    const body = await request.json() as { username: string };
    if (body.username === 'testuser') {
      const user: User = {
        id: 'c7b3d8e0-5e0b-4b0f-8b3a-3b9f4b3d3b3d',
        full_name: 'John Maverick',
        email: 'testuser@example.com',
      };
      const token = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjoidGVzdC11c2VyLTEyMyIsImVtYWlsIjoidGVzdEBleGFtcGxlLmNvbSIsImV4cCI6OTk5OTk5OTk5OX0.test-signature';
      return HttpResponse.json({ token, user });
    } else {
      return new HttpResponse(null, { status: 401 });
    }
  }),

  // Mock for logout
  http.post('/api/auth/logout', () => {
    return HttpResponse.json({ success: true, message: 'Logged out successfully' });
  }),

  // Legacy logout endpoint for backward compatibility
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

  // Mock protected data endpoint for auth testing
  http.get('/api/protected-data', async ({ request }) => {
    const authHeader = request.headers.get('authorization');
    if (authHeader && authHeader.startsWith('Bearer ') && 
        authHeader.includes('eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9')) {
      return HttpResponse.json({ message: 'Protected data', success: true });
    }
    return new HttpResponse(
      JSON.stringify({ error: 'Unauthorized' }),
      { status: 401 }
    );
  }),

  // ============================================
  // WebSocket Mock Handlers
  // ============================================
  // Note: WebSocket connections are mocked globally in jest.setup.js
  // These handlers are for WebSocket-related HTTP endpoints
  
  // Mock auth token verification endpoint
  http.post('/api/auth/verify', async ({ request }) => {
    const authHeader = request.headers.get('authorization');
    const body = await request.json().catch(() => ({})) as { token?: string };
    const token = body.token || authHeader?.replace('Bearer ', '');
    
    if (token && token.includes('eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9') && token !== 'invalid_token') {
      return HttpResponse.json({ 
        valid: true,
        user: {
          id: 'test-user-123',
          email: 'test@example.com',
          full_name: 'Test User'
        }
      });
    }
    return new HttpResponse(
      JSON.stringify({ valid: false, error: 'Invalid token' }),
      { status: 401 }
    );
  }),

  // Mock WebSocket authentication endpoint
  http.post('/api/websocket/auth', async ({ request }) => {
    const authHeader = request.headers.get('authorization');
    const body = await request.json().catch(() => ({})) as { token?: string };
    const token = body.token || authHeader?.replace('Bearer ', '');
    
    if (token && token.includes('eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9') && token !== 'invalid_token') {
      return HttpResponse.json({ 
        success: true, 
        user_id: 'test-user-123',
        permissions: ['chat', 'agent_control']
      });
    }
    return new HttpResponse(
      JSON.stringify({ success: false, error: 'Invalid token' }),
      { status: 401 }
    );
  }),

  // Mock WebSocket connection info endpoint
  http.get('/api/websocket/info', () => {
    return HttpResponse.json({
      url: 'ws://localhost:8000/ws',
      protocols: ['netra-v1'],
      heartbeat_interval: 30000,
      max_message_size: 1048576
    });
  }),

  // Mock WebSocket metrics endpoint
  http.get('/api/websocket/metrics', () => {
    return HttpResponse.json({
      active_connections: 1,
      total_messages_sent: 42,
      total_messages_received: 38,
      average_latency_ms: 150,
      uptime_seconds: 3600
    });
  }),
];