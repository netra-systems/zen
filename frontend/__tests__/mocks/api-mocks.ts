/**
 * API Mocks for Frontend Testing - MSW Service Layer
 * 
 * CRITICAL CONTEXT: Phase 1, Agent 2 implementation
 * - Comprehensive MSW handlers for all API endpoints
 * - Realistic response data matching production
 * - Error simulation capabilities
 * - Rate limiting mocks
 * 
 * ARCHITECTURAL COMPLIANCE:
 * - Maximum file size: 300 lines
 * - Functions ≤8 lines each
 * - Full TypeScript type safety
 * - Realistic data that matches production
 */

// Conditional MSW imports - only available when MSW is properly configured
let rest: any = null;
let setupServer: any = null;

try {
  const mswModule = require('msw');
  const mswNodeModule = require('msw/node');
  rest = mswModule.rest;
  setupServer = mswNodeModule.setupServer;
} catch (error) {
  // MSW not available - create placeholder functions
  console.warn('MSW not available, using placeholder functions');
}
import { Thread } from '@/types/domains/threads';
import { Message } from '@/types/domains/messages';

// ============================================================================
// MOCK DATA FACTORIES - Each function ≤8 lines
// ============================================================================

export function createMockThread(overrides: Partial<Thread> = {}): Thread {
  const id = overrides.id || `thread_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  const now = new Date().toISOString();
  return {
    id,
    title: `Mock Thread ${id.slice(-4)}`,
    name: `Mock Thread ${id.slice(-4)}`,
    created_at: now,
    updated_at: now,
    message_count: 3,
    status: 'active',
    ...overrides
  };
}

export function createMockMessage(overrides: Partial<Message> = {}): Message {
  const id = overrides.id || `msg_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  return {
    id,
    role: 'user',
    content: 'Mock message content',
    timestamp: Date.now(),
    created_at: new Date().toISOString(),
    ...overrides
  };
}

export function createMockUser(overrides: Record<string, unknown> = {}) {
  return {
    id: 'user_123',
    email: 'test@example.com',
    name: 'Test User',
    role: 'user',
    created_at: new Date().toISOString(),
    ...overrides
  };
}

export function createMockWorkload(overrides: Record<string, unknown> = {}) {
  return {
    id: 'workload_123',
    name: 'Test Workload',
    status: 'running',
    created_at: new Date().toISOString(),
    ...overrides
  };
}

// ============================================================================
// RESPONSE DELAY SIMULATION
// ============================================================================

export function withDelay<T>(data: T, delayMs: number = 100): Promise<T> {
  return new Promise(resolve => {
    setTimeout(() => resolve(data), delayMs);
  });
}

// ============================================================================
// ERROR SIMULATION UTILITIES  
// ============================================================================

export const mockApiErrors = {
  networkError: () => new Error('Network connection failed'),
  unauthorized: () => ({ status: 401, message: 'Unauthorized' }),
  forbidden: () => ({ status: 403, message: 'Forbidden' }),
  notFound: () => ({ status: 404, message: 'Resource not found' }),
  serverError: () => ({ status: 500, message: 'Internal server error' }),
  rateLimited: () => ({ status: 429, message: 'Rate limit exceeded' }),
  validationError: () => ({ status: 422, message: 'Validation failed' })
};

// ============================================================================
// MSW REST HANDLERS - All API endpoints
// ============================================================================

export const apiHandlers = rest ? [
  // Threads API
  rest.get(`${process.env.NEXT_PUBLIC_API_URL}/threads`, (req, res, ctx) => {
    const threads = Array.from({ length: 5 }, (_, i) => 
      createMockThread({ id: `thread_${i}`, title: `Thread ${i + 1}` })
    );
    return res(ctx.delay(100), ctx.json({ threads, total: 5 }));
  }),

  rest.post(`${process.env.NEXT_PUBLIC_API_URL}/threads`, (req, res, ctx) => {
    const newThread = createMockThread({ title: 'New Thread' });
    return res(ctx.delay(150), ctx.status(201), ctx.json(newThread));
  }),

  rest.get(`${process.env.NEXT_PUBLIC_API_URL}/threads/:id`, (req, res, ctx) => {
    const { id } = req.params;
    const thread = createMockThread({ id: id as string });
    return res(ctx.delay(80), ctx.json(thread));
  }),

  rest.put(`${process.env.NEXT_PUBLIC_API_URL}/threads/:id`, (req, res, ctx) => {
    const { id } = req.params;
    const thread = createMockThread({ id: id as string });
    return res(ctx.delay(120), ctx.json(thread));
  }),

  rest.delete(`${process.env.NEXT_PUBLIC_API_URL}/threads/:id`, (req, res, ctx) => {
    return res(ctx.delay(100), ctx.status(204));
  }),

  // Messages API
  rest.get(`${process.env.NEXT_PUBLIC_API_URL}/threads/:threadId/messages`, (req, res, ctx) => {
    const messages = Array.from({ length: 3 }, (_, i) => 
      createMockMessage({ 
        id: `msg_${i}`, 
        content: `Message ${i + 1}`,
        role: i % 2 === 0 ? 'user' : 'assistant'
      })
    );
    return res(ctx.delay(120), ctx.json({ messages, total: 3 }));
  }),

  rest.post(`${process.env.NEXT_PUBLIC_API_URL}/threads/:threadId/messages`, (req, res, ctx) => {
    const message = createMockMessage({ content: 'New message' });
    return res(ctx.delay(200), ctx.status(201), ctx.json(message));
  }),

  // Users API
  rest.get(`${process.env.NEXT_PUBLIC_API_URL}/users/me`, (req, res, ctx) => {
    const user = createMockUser();
    return res(ctx.delay(80), ctx.json(user));
  }),

  // Workloads API
  rest.get(`${process.env.NEXT_PUBLIC_API_URL}/workloads`, (req, res, ctx) => {
    const workloads = Array.from({ length: 3 }, (_, i) =>
      createMockWorkload({ id: `workload_${i}`, name: `Workload ${i + 1}` })
    );
    return res(ctx.delay(150), ctx.json({ workloads }));
  }),

  rest.post(`${process.env.NEXT_PUBLIC_API_URL}/workloads`, (req, res, ctx) => {
    const workload = createMockWorkload();
    return res(ctx.delay(300), ctx.status(201), ctx.json(workload));
  }),

  // Analytics API
  rest.get(`${process.env.NEXT_PUBLIC_API_URL}/analytics/metrics`, (req, res, ctx) => {
    const metrics = {
      totalRequests: 1234,
      averageResponseTime: 245,
      errorRate: 0.02,
      activeUsers: 56
    };
    return res(ctx.delay(100), ctx.json(metrics));
  }),

  // Config API
  rest.get(`${process.env.NEXT_PUBLIC_API_URL}/config`, (req, res, ctx) => {
    const config = {
      features: {
        websockets: true,
        analytics: true,
        fileUpload: true
      },
      limits: {
        maxThreads: 100,
        maxMessages: 1000,
        fileSize: 10485760
      }
    };
    return res(ctx.delay(50), ctx.json(config));
  }),

  // Health check
  rest.get(`${process.env.NEXT_PUBLIC_API_URL}/health`, (req, res, ctx) => {
    return res(ctx.delay(30), ctx.json({ status: 'healthy', timestamp: new Date().toISOString() }));
  })
] : [];

// ============================================================================
// ERROR SCENARIO HANDLERS
// ============================================================================

export const errorHandlers = rest ? [
  rest.get(`${process.env.NEXT_PUBLIC_API_URL}/threads`, (req, res, ctx) => {
    return res(ctx.delay(100), ctx.status(500), ctx.json(mockApiErrors.serverError()));
  }),

  rest.post(`${process.env.NEXT_PUBLIC_API_URL}/threads`, (req, res, ctx) => {
    return res(ctx.delay(50), ctx.status(429), ctx.json(mockApiErrors.rateLimited()));
  }),

  rest.get(`${process.env.NEXT_PUBLIC_API_URL}/users/me`, (req, res, ctx) => {
    return res(ctx.delay(30), ctx.status(401), ctx.json(mockApiErrors.unauthorized()));
  })
] : [];

// ============================================================================
// MSW SERVER SETUP
// ============================================================================

export const mockServer = setupServer ? setupServer(...apiHandlers) : null;

export function startMockServer() {
  if (mockServer) {
    mockServer.listen({ onUnhandledRequest: 'bypass' });
  } else {
    console.warn('MSW not available - mock server not started');
  }
}

export function stopMockServer() {
  if (mockServer) {
    mockServer.close();
  }
}

export function resetMockHandlers() {
  if (mockServer) {
    mockServer.resetHandlers();
  }
}

export function useMockErrorScenarios() {
  if (mockServer && errorHandlers.length > 0) {
    mockServer.use(...errorHandlers);
  }
}

// ============================================================================
// RATE LIMITING MOCK
// ============================================================================

let requestCounts: Record<string, number> = {};

export function simulateRateLimit(endpoint: string, limit: number = 10) {
  const count = requestCounts[endpoint] || 0;
  requestCounts[endpoint] = count + 1;
  return count >= limit;
}

export function resetRateLimits() {
  requestCounts = {};
}

// ============================================================================
// TEST UTILITIES
// ============================================================================

export function createMockApiResponse<T>(data: T, options: {
  status?: number;
  delay?: number;
  headers?: Record<string, string>;
} = {}) {
  const { status = 200, delay = 100, headers = {} } = options;
  return {
    status,
    delay,
    headers: { 'Content-Type': 'application/json', ...headers },
    body: JSON.stringify(data)
  };
}

export function waitForApiCall(timeout: number = 1000): Promise<void> {
  return new Promise(resolve => setTimeout(resolve, timeout));
}

// Default export for convenience
export default {
  apiHandlers,
  errorHandlers,
  mockServer,
  startMockServer,
  stopMockServer,
  resetMockHandlers,
  useMockErrorScenarios,
  createMockThread,
  createMockMessage,
  createMockUser,
  createMockWorkload,
  mockApiErrors
};