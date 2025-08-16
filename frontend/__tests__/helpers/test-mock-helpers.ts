/**
 * Test Mock Helpers - Reusable mock data and services
 * Keeps test functions ≤8 lines by extracting mock creation
 */

export const createMockDocument = () => ({
  id: 'doc-123',
  title: 'Test Document',
  content: 'Document content for testing',
  embeddings: [0.1, 0.2, 0.3],
  created_at: new Date().toISOString()
});

export const createMockSearchResults = () => [
  { id: 'doc-1', score: 0.95, content: 'relevant content' },
  { id: 'doc-2', score: 0.87, content: 'related content' }
];

export const createMockGenerationJob = () => ({
  id: 'job-456',
  status: 'processing',
  template: 'customer_support',
  count: 100,
  progress: 0
});

export const createMockExportData = () => ({
  format: 'json',
  data: [{ id: 1, content: 'synthetic' }],
  size: 1024
});

export const createMockHealthStatus = () => ({
  status: 'healthy',
  services: { database: 'up', redis: 'up' }
});

export const createMockDegradedHealth = () => ({
  status: 'degraded',
  services: { database: 'up', redis: 'down' }
});

export const createMockOAuthResponse = () => ({
  access_token: 'oauth-token',
  user: { id: 'oauth-user', email: 'oauth@example.com', full_name: 'OAuth User', name: 'OAuth User' }
});

export const createMockTask = () => ({
  id: 'task-123',
  type: 'data_processing',
  status: 'queued',
  created_at: Date.now()
});

export const createExpiredToken = () => {
  return 'eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJleHAiOjE2MDAwMDAwMDB9.fake';
};

export const setupCorpusServiceMock = () => {
  return { 
    uploadDocument: jest.fn().mockResolvedValue({}), 
    searchDocuments: jest.fn().mockResolvedValue([]) 
  };
};

export const setupSyntheticDataServiceMock = () => {
  return { 
    exportData: jest.fn().mockResolvedValue(new Blob(['data'])) 
  };
};

export const setupLLMCacheServiceMock = () => {
  return { 
    query: jest.fn().mockResolvedValue({ cached: false, response: 'response' }) 
  };
};

export const setupHealthServiceMock = () => {
  return { 
    checkHealth: jest.fn().mockResolvedValue(createMockHealthStatus()) 
  };
};

export const setupRetryFetchMock = () => {
  let attempts = 0;
  return jest.fn().mockImplementation(async () => {
    attempts++;
    if (attempts < 3) throw new Error('Network error');
    return { ok: true, json: async () => ({ success: true }) };
  });
};

export const setupLLMCacheResponseMocks = () => {
  const llmCacheService = setupLLMCacheServiceMock();
  llmCacheService.query = jest.fn()
    .mockResolvedValueOnce({ cached: false, response: 'new response' })
    .mockResolvedValueOnce({ cached: true, response: 'cached response' });
  return llmCacheService;
};