// ============================================================================
// API CLIENT TEST MOCKS - COMPREHENSIVE API TESTING INFRASTRUCTURE
// ============================================================================
// This file provides complete API client mocking for all API-related tests
// to ensure consistent API behavior and prevent real HTTP calls.
// ============================================================================

export interface MockAPIResponse<T = any> {
  status: number;
  statusText: string;
  data: T;
  headers: Record<string, string>;
  config?: any;
}

export interface MockAPIError {
  message: string;
  status: number;
  response?: {
    data: any;
    status: number;
    statusText: string;
  };
}

// ============================================================================
// API RESPONSE FACTORIES
// ============================================================================
export const createSuccessResponse = <T>(data: T, status: number = 200): MockAPIResponse<T> => ({
  status,
  statusText: status === 200 ? 'OK' : status === 201 ? 'Created' : 'Success',
  data,
  headers: {
    'Content-Type': 'application/json',
    'Cache-Control': 'no-cache'
  }
});

export const createErrorResponse = (message: string, status: number = 500, data: any = null): MockAPIError => ({
  message,
  status,
  response: {
    data: data || { error: message },
    status,
    statusText: getStatusText(status)
  }
});

const getStatusText = (status: number): string => {
  const statusTexts: Record<number, string> = {
    400: 'Bad Request',
    401: 'Unauthorized',
    403: 'Forbidden',
    404: 'Not Found',
    422: 'Unprocessable Entity',
    429: 'Too Many Requests',
    500: 'Internal Server Error',
    502: 'Bad Gateway',
    503: 'Service Unavailable'
  };
  return statusTexts[status] || 'Error';
};

// ============================================================================
// API CLIENT MOCK
// ============================================================================
export const createMockAPIClient = () => {
  const requestHistory: Array<{
    method: string;
    url: string;
    data?: any;
    headers?: any;
    timestamp: number;
  }> = [];

  const mockClient = {
    // HTTP methods
    get: jest.fn().mockImplementation(async (url: string, config?: any) => {
      requestHistory.push({
        method: 'GET',
        url,
        headers: config?.headers,
        timestamp: Date.now()
      });
      
      // Default successful response
      return createSuccessResponse({ message: 'GET request successful' });
    }),

    post: jest.fn().mockImplementation(async (url: string, data?: any, config?: any) => {
      requestHistory.push({
        method: 'POST',
        url,
        data,
        headers: config?.headers,
        timestamp: Date.now()
      });
      
      // Default successful response
      return createSuccessResponse({ message: 'POST request successful', data }, 201);
    }),

    put: jest.fn().mockImplementation(async (url: string, data?: any, config?: any) => {
      requestHistory.push({
        method: 'PUT',
        url,
        data,
        headers: config?.headers,
        timestamp: Date.now()
      });
      
      // Default successful response
      return createSuccessResponse({ message: 'PUT request successful', data });
    }),

    patch: jest.fn().mockImplementation(async (url: string, data?: any, config?: any) => {
      requestHistory.push({
        method: 'PATCH',
        url,
        data,
        headers: config?.headers,
        timestamp: Date.now()
      });
      
      // Default successful response
      return createSuccessResponse({ message: 'PATCH request successful', data });
    }),

    delete: jest.fn().mockImplementation(async (url: string, config?: any) => {
      requestHistory.push({
        method: 'DELETE',
        url,
        headers: config?.headers,
        timestamp: Date.now()
      });
      
      // Default successful response
      return createSuccessResponse({ message: 'DELETE request successful' });
    }),

    // Generic request method
    request: jest.fn().mockImplementation(async (config: any) => {
      requestHistory.push({
        method: config.method?.toUpperCase() || 'GET',
        url: config.url,
        data: config.data,
        headers: config.headers,
        timestamp: Date.now()
      });
      
      // Default successful response
      return createSuccessResponse({ message: 'Request successful', config });
    }),

    // Test utilities
    __getRequestHistory: () => [...requestHistory],
    __clearHistory: () => requestHistory.splice(0, requestHistory.length),
    __getLastRequest: () => requestHistory[requestHistory.length - 1],
    __wasUrlCalled: (url: string) => requestHistory.some(req => req.url.includes(url)),
    __wasMethodCalled: (method: string, url?: string) => {
      return requestHistory.some(req => {
        const methodMatches = req.method === method.toUpperCase();
        return url ? methodMatches && req.url.includes(url) : methodMatches;
      });
    },

    // Mock response configuration
    __mockResponse: (method: string, url: string, response: any) => {
      const methodFn = mockClient[method.toLowerCase() as keyof typeof mockClient];
      if (typeof methodFn === 'function') {
        (methodFn as jest.Mock).mockImplementationOnce(async () => response);
      }
    },

    __mockError: (method: string, url: string, error: MockAPIError) => {
      const methodFn = mockClient[method.toLowerCase() as keyof typeof mockClient];
      if (typeof methodFn === 'function') {
        (methodFn as jest.Mock).mockImplementationOnce(async () => {
          throw error;
        });
      }
    },

    __reset: () => {
      Object.keys(mockClient).forEach(key => {
        if (typeof mockClient[key as keyof typeof mockClient] === 'function' && key !== '__reset') {
          (mockClient[key as keyof typeof mockClient] as jest.Mock).mockClear();
        }
      });
      requestHistory.splice(0, requestHistory.length);
    }
  };

  return mockClient;
};

// ============================================================================
// API CLIENT WRAPPER MOCK
// ============================================================================
export const createMockAPIClientWrapper = () => {
  const baseClient = createMockAPIClient();
  
  return {
    ...baseClient,
    
    // Connection health check
    healthCheck: jest.fn().mockResolvedValue({
      status: 'healthy',
      timestamp: Date.now(),
      version: '1.0.0'
    }),

    // Authentication
    setAuthToken: jest.fn(),
    clearAuthToken: jest.fn(),
    getAuthHeaders: jest.fn().mockReturnValue({
      'Authorization': 'Bearer mock-token'
    }),

    // Request interceptors
    addRequestInterceptor: jest.fn(),
    addResponseInterceptor: jest.fn(),

    // Base URL management
    setBaseURL: jest.fn(),
    getBaseURL: jest.fn().mockReturnValue('http://localhost:8000'),

    // Timeout management
    setTimeout: jest.fn(),
    getTimeout: jest.fn().mockReturnValue(5000),

    // Retry logic
    setRetryConfig: jest.fn(),
    getRetryConfig: jest.fn().mockReturnValue({
      retries: 3,
      retryDelay: 1000
    })
  };
};

// ============================================================================
// COMMON API RESPONSE MOCKS
// ============================================================================
export const commonAPIResponses = {
  // Authentication
  loginSuccess: () => createSuccessResponse({
    access_token: 'mock-token-123',
    token_type: 'Bearer',
    expires_in: 3600,
    user: {
      id: 'user-123',
      email: 'test@example.com',
      full_name: 'Test User'
    }
  }),

  loginFailure: () => createErrorResponse('Invalid credentials', 401),

  // Threads
  getThreads: (threads: any[] = []) => createSuccessResponse({
    threads,
    total: threads.length,
    page: 1,
    limit: 10
  }),

  getThread: (thread: any = { id: 'thread-123', title: 'Test Thread' }) =>
    createSuccessResponse(thread),

  createThread: (thread: any = { id: 'new-thread-123', title: 'New Thread' }) =>
    createSuccessResponse(thread, 201),

  updateThread: (thread: any) => createSuccessResponse(thread),

  deleteThread: () => createSuccessResponse({ message: 'Thread deleted successfully' }),

  // Messages
  getMessages: (messages: any[] = []) => createSuccessResponse({
    messages,
    total: messages.length,
    thread_id: 'thread-123'
  }),

  sendMessage: (message: any = { id: 'msg-123', content: 'Test message' }) =>
    createSuccessResponse(message, 201),

  // MCP Tools
  getMCPServers: (servers: any[] = []) => createSuccessResponse({
    servers,
    total: servers.length
  }),

  getMCPTools: (tools: any[] = []) => createSuccessResponse({
    tools,
    total: tools.length
  }),

  executeMCPTool: (result: any = { success: true, output: 'Tool executed' }) =>
    createSuccessResponse(result),

  // Health checks
  healthCheck: () => createSuccessResponse({
    status: 'healthy',
    timestamp: Date.now(),
    services: {
      database: 'healthy',
      websocket: 'healthy',
      mcp: 'healthy'
    }
  }),

  // Generic errors
  notFound: () => createErrorResponse('Resource not found', 404),
  badRequest: () => createErrorResponse('Bad request', 400),
  unauthorized: () => createErrorResponse('Unauthorized', 401),
  forbidden: () => createErrorResponse('Forbidden', 403),
  serverError: () => createErrorResponse('Internal server error', 500),
  networkError: () => createErrorResponse('Network error', 0)
};

// ============================================================================
// API MOCK SCENARIOS
// ============================================================================
export const apiTestScenarios = {
  // Successful API calls
  allSuccessful: () => {
    const client = createMockAPIClient();
    
    // Configure all methods to return success
    Object.keys(commonAPIResponses).forEach(key => {
      const response = (commonAPIResponses as any)[key]();
      if (response.status < 400) {
        client.get.mockResolvedValue(response);
        client.post.mockResolvedValue(response);
        client.put.mockResolvedValue(response);
        client.delete.mockResolvedValue(response);
      }
    });
    
    return client;
  },

  // Network failures
  networkFailures: () => {
    const client = createMockAPIClient();
    const networkError = commonAPIResponses.networkError();
    
    client.get.mockRejectedValue(networkError);
    client.post.mockRejectedValue(networkError);
    client.put.mockRejectedValue(networkError);
    client.delete.mockRejectedValue(networkError);
    
    return client;
  },

  // Authentication failures
  authFailures: () => {
    const client = createMockAPIClient();
    const authError = commonAPIResponses.unauthorized();
    
    client.get.mockRejectedValue(authError);
    client.post.mockRejectedValue(authError);
    client.put.mockRejectedValue(authError);
    client.delete.mockRejectedValue(authError);
    
    return client;
  },

  // Rate limiting
  rateLimited: () => {
    const client = createMockAPIClient();
    const rateLimitError = createErrorResponse('Too many requests', 429);
    
    client.get.mockRejectedValueOnce(rateLimitError).mockResolvedValue(commonAPIResponses.healthCheck());
    client.post.mockRejectedValueOnce(rateLimitError).mockResolvedValue(commonAPIResponses.healthCheck());
    
    return client;
  },

  // Intermittent failures
  intermittentFailures: () => {
    const client = createMockAPIClient();
    
    client.get
      .mockRejectedValueOnce(commonAPIResponses.serverError())
      .mockResolvedValue(commonAPIResponses.healthCheck());
    
    client.post
      .mockRejectedValueOnce(commonAPIResponses.serverError())
      .mockResolvedValue(commonAPIResponses.sendMessage());
    
    return client;
  }
};

// ============================================================================
// FETCH MOCK UTILITIES
// ============================================================================
export const setupFetchMocks = (responses: Array<{ url: string; response: any; status?: number }>) => {
  const mockFetch = jest.fn();
  
  responses.forEach(({ url, response, status = 200 }) => {
    const mockResponse = {
      ok: status >= 200 && status < 300,
      status,
      statusText: getStatusText(status),
      json: jest.fn().mockResolvedValue(response),
      text: jest.fn().mockResolvedValue(JSON.stringify(response)),
      headers: new Headers({
        'Content-Type': 'application/json'
      }),
    };

    mockFetch.mockImplementation((fetchUrl: string, options: any = {}) => {
      if (fetchUrl.includes(url)) {
        return Promise.resolve(mockResponse);
      }
      return Promise.reject(new Error(`Unexpected fetch to ${fetchUrl}`));
    });
  });

  global.fetch = mockFetch;
  return mockFetch;
};

// ============================================================================
// CONNECTION HEALTH MOCKS
// ============================================================================
export const createConnectionHealthMock = (initialState: 'healthy' | 'unhealthy' | 'unknown' = 'healthy') => {
  let connectionState = initialState;
  
  return {
    isHealthy: jest.fn().mockImplementation(() => connectionState === 'healthy'),
    checkHealth: jest.fn().mockImplementation(async () => {
      if (connectionState === 'healthy') {
        return createSuccessResponse({
          status: 'healthy',
          latency: 50,
          timestamp: Date.now()
        });
      } else {
        throw createErrorResponse('Health check failed', 503);
      }
    }),
    
    // Test utilities
    setHealthy: () => { connectionState = 'healthy'; },
    setUnhealthy: () => { connectionState = 'unhealthy'; },
    setUnknown: () => { connectionState = 'unknown'; },
    getState: () => connectionState
  };
};

export default {
  createMockAPIClient,
  createMockAPIClientWrapper,
  commonAPIResponses,
  apiTestScenarios,
  setupFetchMocks,
  createConnectionHealthMock
};