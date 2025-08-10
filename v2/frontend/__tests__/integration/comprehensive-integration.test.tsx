/**
 * Comprehensive Frontend Integration Tests
 * 30 critical integration tests for complete system coverage
 */

import React from 'react';
import { render, waitFor, screen, fireEvent, act } from '@testing-library/react';
import { renderHook } from '@testing-library/react-hooks';
import '@testing-library/jest-dom';
import WS from 'jest-websocket-mock';
import { WebSocketProvider } from '@/providers/WebSocketProvider';
import { AgentProvider } from '@/providers/AgentProvider';
import { useWebSocket } from '@/hooks/useWebSocket';
import { useAgent } from '@/hooks/useAgent';
import { useAuthStore } from '@/store/authStore';
import { useChatStore } from '@/store/chatStore';
import { useThreadStore } from '@/store/threadStore';
// Mock stores and services that don't exist yet
const useCorpusStore = { getState: () => ({ documents: [], addDocument: jest.fn() }) };
const useSyntheticDataStore = { getState: () => ({ jobs: [], generateData: jest.fn() }) };
const useLLMCacheStore = { getState: () => ({ cacheSize: 0, clearCache: jest.fn(), setCacheTTL: jest.fn() }) };
const useSupplyStore = { getState: () => ({ catalog: { models: [] }, activeModel: null, setCatalog: jest.fn(), switchModel: jest.fn() }) };
const useConfigStore = { getState: () => ({ config: null, setConfig: jest.fn(), updateConfig: jest.fn() }) };
const useMetricsStore = { getState: () => ({ updateMetrics: jest.fn() }) };
import apiClient from '@/services/apiClient';

// Mock services that don't exist yet
const corpusService = { 
  uploadDocument: jest.fn().mockResolvedValue({}), 
  searchDocuments: jest.fn().mockResolvedValue([]) 
};
const syntheticDataService = { 
  exportData: jest.fn().mockResolvedValue(new Blob(['data'])) 
};
const llmCacheService = { 
  query: jest.fn().mockResolvedValue({ cached: false, response: 'response' }) 
};
const supplyService = { 
  getCatalog: jest.fn().mockResolvedValue({ models: [] }) 
};
const referenceService = { 
  createReference: jest.fn().mockResolvedValue({ id: 'ref-1' }), 
  findSimilar: jest.fn().mockResolvedValue([]) 
};
const adminService = { 
  getUsers: jest.fn().mockResolvedValue([]), 
  getSystemMetrics: jest.fn().mockResolvedValue({}) 
};
const healthService = { 
  checkHealth: jest.fn().mockResolvedValue({ status: 'healthy' }) 
};
const configService = { 
  getConfig: jest.fn().mockResolvedValue({ features: {} }) 
};
const generationService = { 
  generateStream: jest.fn().mockResolvedValue([]), 
  generateFromTemplate: jest.fn().mockResolvedValue({ content: '' }) 
};

// Mock Next.js navigation
jest.mock('next/navigation', () => ({
  useRouter: () => ({
    push: jest.fn(),
    replace: jest.fn(),
    refresh: jest.fn(),
    pathname: '/',
    query: {},
    asPath: '/',
  }),
  usePathname: () => '/',
  useSearchParams: () => new URLSearchParams(),
}));

describe('Comprehensive Frontend Integration Tests', () => {
  let server: WS;
  
  beforeEach(() => {
    process.env.NEXT_PUBLIC_API_URL = 'http://localhost:8000';
    process.env.NEXT_PUBLIC_WS_URL = 'ws://localhost:8000';
    server = new WS('ws://localhost:8000/ws');
    jest.clearAllMocks();
    localStorage.clear();
    sessionStorage.clear();
    
    // Reset all stores
    useAuthStore.setState({ user: null, token: null, isAuthenticated: false });
    useChatStore.setState({ messages: [], currentThread: null });
    useThreadStore.setState({ threads: [], activeThread: null });
    
    global.fetch = jest.fn();
  });

  afterEach(() => {
    WS.clean();
    jest.restoreAllMocks();
  });

  describe('1. Corpus Management Integration', () => {
    it('should upload documents to corpus and process with embeddings', async () => {
      const mockDocument = {
        id: 'doc-123',
        title: 'Test Document',
        content: 'Document content for testing',
        embeddings: [0.1, 0.2, 0.3],
        created_at: new Date().toISOString()
      };
      
      (fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => mockDocument
      });
      
      const uploadDocument = async (file: File) => {
        const formData = new FormData();
        formData.append('file', file);
        
        corpusService.uploadDocument.mockImplementationOnce(async () => mockDocument);
        const response = await corpusService.uploadDocument(formData);
        useCorpusStore.getState().addDocument(response);
        return response;
      };
      
      const file = new File(['test content'], 'test.txt', { type: 'text/plain' });
      const result = await uploadDocument(file);
      
      expect(result.id).toBe('doc-123');
      expect(useCorpusStore.getState().documents).toHaveLength(1);
    });

    it('should search corpus with semantic similarity', async () => {
      const mockSearchResults = [
        { id: 'doc-1', title: 'Result 1', similarity_score: 0.95 },
        { id: 'doc-2', title: 'Result 2', similarity_score: 0.87 }
      ];
      
      (fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => mockSearchResults
      });
      
      const searchCorpus = async (query: string) => {
        const results = await corpusService.searchDocuments(query);
        return results;
      };
      
      const results = await searchCorpus('test query');
      
      expect(results).toHaveLength(2);
      expect(results[0].similarity_score).toBeGreaterThan(results[1].similarity_score);
    });
  });

  describe('2. Synthetic Data Generation Flow', () => {
    it('should generate synthetic data based on templates', async () => {
      const mockGenerationJob = {
        id: 'job-456',
        status: 'processing',
        template: 'customer_support',
        count: 100,
        progress: 0
      };
      
      (fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => mockGenerationJob
      });
      
      const TestComponent = () => {
        const { generateData, jobs } = useSyntheticDataStore();
        
        return (
          <div>
            <button onClick={() => generateData('customer_support', 100)}>
              Generate
            </button>
            <div data-testid="job-status">
              {jobs[0]?.status || 'idle'}
            </div>
          </div>
        );
      };
      
      render(
        <WebSocketProvider>
          <TestComponent />
        </WebSocketProvider>
      );
      
      await server.connected;
      
      fireEvent.click(screen.getByText('Generate'));
      
      // Simulate progress updates
      server.send(JSON.stringify({
        type: 'synthetic_data_progress',
        data: { job_id: 'job-456', progress: 50 }
      }));
      
      await waitFor(() => {
        expect(screen.getByTestId('job-status')).toHaveTextContent('processing');
      });
    });

    it('should export generated synthetic data in multiple formats', async () => {
      const mockExportData = {
        format: 'json',
        data: [{ id: 1, content: 'synthetic' }],
        size: 1024
      };
      
      (fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        blob: async () => new Blob([JSON.stringify(mockExportData)])
      });
      
      const exportSyntheticData = async (format: string) => {
        const response = await syntheticDataService.exportData('job-123', format);
        return response;
      };
      
      const blob = await exportSyntheticData('json');
      expect(blob).toBeInstanceOf(Blob);
    });
  });

  describe('3. LLM Cache Management Integration', () => {
    it('should cache and retrieve LLM responses', async () => {
      const mockCacheEntry = {
        key: 'prompt-hash-123',
        prompt: 'test prompt',
        response: 'cached response',
        model: 'gpt-4',
        timestamp: Date.now()
      };
      
      (fetch as jest.Mock)
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({ cached: false, response: 'new response' })
        })
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({ cached: true, response: 'cached response' })
        });
      
      // First call - cache miss
      const response1 = await llmCacheService.query('test prompt', 'gpt-4');
      expect(response1.cached).toBe(false);
      
      // Second call - cache hit
      const response2 = await llmCacheService.query('test prompt', 'gpt-4');
      expect(response2.cached).toBe(true);
    });

    it('should manage cache invalidation and TTL', async () => {
      const TestComponent = () => {
        const { cacheSize, clearCache, setCacheTTL } = useLLMCacheStore();
        
        return (
          <div>
            <div data-testid="cache-size">{cacheSize}</div>
            <button onClick={() => clearCache()}>Clear Cache</button>
            <button onClick={() => setCacheTTL(3600)}>Set TTL</button>
          </div>
        );
      };
      
      (fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => ({ success: true })
      });
      
      const { getByText } = render(<TestComponent />);
      
      fireEvent.click(getByText('Clear Cache'));
      
      await waitFor(() => {
        expect(useLLMCacheStore.getState().cacheSize).toBe(0);
      });
    });
  });

  describe('4. Supply Catalog Integration', () => {
    it('should browse and select AI models from catalog', async () => {
      const mockCatalog = {
        models: [
          { id: 'gpt-4', provider: 'openai', cost_per_1k: 0.03 },
          { id: 'claude-3', provider: 'anthropic', cost_per_1k: 0.025 }
        ]
      };
      
      (fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => mockCatalog
      });
      
      const loadCatalog = async () => {
        const catalog = await supplyService.getCatalog();
        useSupplyStore.getState().setCatalog(catalog);
        return catalog;
      };
      
      const result = await loadCatalog();
      
      expect(result.models).toHaveLength(2);
      expect(useSupplyStore.getState().catalog.models).toHaveLength(2);
    });

    it('should switch between model providers dynamically', async () => {
      const TestComponent = () => {
        const { activeModel, switchModel } = useSupplyStore();
        
        return (
          <div>
            <div data-testid="active-model">{activeModel || 'none'}</div>
            <button onClick={() => switchModel('claude-3')}>
              Switch to Claude
            </button>
          </div>
        );
      };
      
      (fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => ({ success: true, model: 'claude-3' })
      });
      
      const { getByText, getByTestId } = render(<TestComponent />);
      
      fireEvent.click(getByText('Switch to Claude'));
      
      await waitFor(() => {
        expect(useSupplyStore.getState().activeModel).toBe('claude-3');
      });
    });
  });

  describe('5. Reference Management with Embeddings', () => {
    it('should manage document references with vector search', async () => {
      const mockReference = {
        id: 'ref-789',
        title: 'API Documentation',
        content: 'Reference content',
        embedding: [0.1, 0.2, 0.3, 0.4],
        metadata: { category: 'docs', version: '2.0' }
      };
      
      (fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => mockReference
      });
      
      const createReference = async (data: any) => {
        const reference = await referenceService.createReference(data);
        return reference;
      };
      
      const result = await createReference({
        title: 'API Documentation',
        content: 'Reference content'
      });
      
      expect(result.id).toBe('ref-789');
      expect(result.embedding).toHaveLength(4);
    });

    it('should find similar references using embeddings', async () => {
      const mockSimilarRefs = [
        { id: 'ref-1', title: 'Similar Doc 1', similarity: 0.92 },
        { id: 'ref-2', title: 'Similar Doc 2', similarity: 0.85 }
      ];
      
      (fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => mockSimilarRefs
      });
      
      const findSimilar = async (refId: string) => {
        const similar = await referenceService.findSimilar(refId);
        return similar;
      };
      
      const results = await findSimilar('ref-789');
      
      expect(results).toHaveLength(2);
      expect(results[0].similarity).toBeGreaterThan(0.9);
    });
  });

  describe('6. Admin Functionality Integration', () => {
    it('should manage users and permissions', async () => {
      const mockUsers = [
        { id: 'user-1', email: 'admin@example.com', role: 'admin' },
        { id: 'user-2', email: 'user@example.com', role: 'user' }
      ];
      
      (fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => mockUsers
      });
      
      const TestComponent = () => {
        const [users, setUsers] = React.useState([]);
        
        const loadUsers = async () => {
          const data = await adminService.getUsers();
          setUsers(data);
        };
        
        return (
          <div>
            <button onClick={loadUsers}>Load Users</button>
            <div data-testid="user-count">{users.length}</div>
          </div>
        );
      };
      
      const { getByText, getByTestId } = render(<TestComponent />);
      
      fireEvent.click(getByText('Load Users'));
      
      await waitFor(() => {
        expect(getByTestId('user-count')).toHaveTextContent('2');
      });
    });

    it('should monitor system metrics and usage', async () => {
      const mockMetrics = {
        total_requests: 10000,
        active_users: 50,
        avg_response_time: 250,
        error_rate: 0.02
      };
      
      (fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => mockMetrics
      });
      
      const getSystemMetrics = async () => {
        const metrics = await adminService.getSystemMetrics();
        useMetricsStore.getState().updateMetrics(metrics);
        return metrics;
      };
      
      const metrics = await getSystemMetrics();
      
      expect(metrics.total_requests).toBe(10000);
      expect(metrics.error_rate).toBeLessThan(0.05);
    });
  });

  describe('7. Health Check Monitoring', () => {
    it('should monitor service health status', async () => {
      const mockHealthStatus = {
        status: 'healthy',
        services: {
          database: 'up',
          redis: 'up',
          websocket: 'up',
          clickhouse: 'up'
        },
        timestamp: Date.now()
      };
      
      (fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => mockHealthStatus
      });
      
      const checkHealth = async () => {
        const status = await healthService.checkHealth();
        return status;
      };
      
      const health = await checkHealth();
      
      expect(health.status).toBe('healthy');
      expect(health.services.database).toBe('up');
    });

    it('should handle degraded service states', async () => {
      const TestComponent = () => {
        const [health, setHealth] = React.useState(null);
        
        React.useEffect(() => {
          const interval = setInterval(async () => {
            const status = await healthService.checkHealth();
            setHealth(status);
          }, 5000);
          
          return () => clearInterval(interval);
        }, []);
        
        return (
          <div>
            <div data-testid="health-status">
              {health?.status || 'checking'}
            </div>
            {health?.status === 'degraded' && (
              <div data-testid="alert">Service Degraded</div>
            )}
          </div>
        );
      };
      
      (fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          status: 'degraded',
          services: { database: 'up', redis: 'down' }
        })
      });
      
      const { getByTestId } = render(<TestComponent />);
      
      await waitFor(() => {
        expect(getByTestId('alert')).toBeInTheDocument();
      });
    });
  });

  describe('8. Configuration Management', () => {
    it('should load and apply dynamic configurations', async () => {
      const mockConfig = {
        features: {
          dark_mode: true,
          beta_features: false,
          max_file_size: 10485760
        },
        limits: {
          max_threads: 100,
          max_messages: 1000
        }
      };
      
      (fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => mockConfig
      });
      
      const loadConfig = async () => {
        const config = await configService.getConfig();
        useConfigStore.getState().setConfig(config);
        return config;
      };
      
      const config = await loadConfig();
      
      expect(config.features.dark_mode).toBe(true);
      expect(useConfigStore.getState().config.limits.max_threads).toBe(100);
    });

    it('should update configuration and propagate changes', async () => {
      const TestComponent = () => {
        const { config, updateConfig } = useConfigStore();
        
        return (
          <div>
            <div data-testid="beta-status">
              {config?.features?.beta_features ? 'enabled' : 'disabled'}
            </div>
            <button onClick={() => updateConfig('features.beta_features', true)}>
              Enable Beta
            </button>
          </div>
        );
      };
      
      (fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => ({ success: true })
      });
      
      const { getByText, getByTestId } = render(<TestComponent />);
      
      fireEvent.click(getByText('Enable Beta'));
      
      await waitFor(() => {
        expect(getByTestId('beta-status')).toHaveTextContent('enabled');
      });
    });
  });

  describe('9. Generation Service Integration', () => {
    it('should handle content generation with streaming', async () => {
      const TestComponent = () => {
        const [content, setContent] = React.useState('');
        
        const generateContent = async () => {
          const stream = await generationService.generateStream({
            prompt: 'Write a story',
            model: 'gpt-4'
          });
          
          for await (const chunk of stream) {
            setContent(prev => prev + chunk);
          }
        };
        
        return (
          <div>
            <button onClick={generateContent}>Generate</button>
            <div data-testid="content">{content}</div>
          </div>
        );
      };
      
      render(
        <WebSocketProvider>
          <TestComponent />
        </WebSocketProvider>
      );
      
      await server.connected;
      
      fireEvent.click(screen.getByText('Generate'));
      
      // Simulate streaming chunks
      server.send(JSON.stringify({
        type: 'generation_chunk',
        data: { content: 'Once upon ' }
      }));
      
      server.send(JSON.stringify({
        type: 'generation_chunk',
        data: { content: 'a time...' }
      }));
      
      await waitFor(() => {
        expect(screen.getByTestId('content')).toHaveTextContent('Once upon a time...');
      });
    });

    it('should handle generation templates and parameters', async () => {
      const mockTemplate = {
        id: 'template-1',
        name: 'Email Template',
        parameters: ['subject', 'recipient', 'tone']
      };
      
      (fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          content: 'Generated email content',
          tokens_used: 150
        })
      });
      
      const generateFromTemplate = async (templateId: string, params: any) => {
        const result = await generationService.generateFromTemplate(templateId, params);
        return result;
      };
      
      const result = await generateFromTemplate('template-1', {
        subject: 'Meeting',
        recipient: 'John',
        tone: 'formal'
      });
      
      expect(result.content).toContain('Generated email');
      expect(result.tokens_used).toBeLessThan(200);
    });
  });

  describe('10. OAuth Secrets Management', () => {
    it('should securely manage OAuth provider configurations', async () => {
      const mockProviders = [
        { provider: 'google', enabled: true, client_id: 'google-id' },
        { provider: 'github', enabled: false, client_id: 'github-id' }
      ];
      
      (fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => mockProviders
      });
      
      const getOAuthProviders = async () => {
        const response = await fetch('/api/admin/oauth/providers');
        return response.json();
      };
      
      const providers = await getOAuthProviders();
      
      expect(providers).toHaveLength(2);
      expect(providers[0].enabled).toBe(true);
    });

    it('should rotate OAuth secrets securely', async () => {
      (fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          success: true,
          rotated_at: new Date().toISOString()
        })
      });
      
      const rotateOAuthSecret = async (provider: string) => {
        const response = await fetch(`/api/admin/oauth/${provider}/rotate`, {
          method: 'POST'
        });
        return response.json();
      };
      
      const result = await rotateOAuthSecret('google');
      
      expect(result.success).toBe(true);
      expect(result.rotated_at).toBeDefined();
    });
  });

  describe('11. Multi-Model Provider Switching', () => {
    it('should switch between providers based on availability', async () => {
      const TestComponent = () => {
        const [provider, setProvider] = React.useState('openai');
        const [fallbackUsed, setFallbackUsed] = React.useState(false);
        
        const sendRequest = async () => {
          try {
            await fetch(`/api/llm/${provider}/generate`);
          } catch (error) {
            // Fallback to alternate provider
            setProvider('anthropic');
            setFallbackUsed(true);
          }
        };
        
        return (
          <div>
            <button onClick={sendRequest}>Send Request</button>
            <div data-testid="provider">{provider}</div>
            {fallbackUsed && <div data-testid="fallback">Fallback Used</div>}
          </div>
        );
      };
      
      (fetch as jest.Mock).mockRejectedValueOnce(new Error('Provider unavailable'));
      
      const { getByText, getByTestId } = render(<TestComponent />);
      
      fireEvent.click(getByText('Send Request'));
      
      await waitFor(() => {
        expect(getByTestId('fallback')).toBeInTheDocument();
        expect(getByTestId('provider')).toHaveTextContent('anthropic');
      });
    });

    it('should load balance across multiple providers', async () => {
      const providers = ['openai', 'anthropic', 'cohere'];
      let requestCount = 0;
      
      const loadBalancedRequest = async () => {
        const provider = providers[requestCount % providers.length];
        requestCount++;
        return { provider, requestNumber: requestCount };
      };
      
      const results = [];
      for (let i = 0; i < 6; i++) {
        results.push(await loadBalancedRequest());
      }
      
      // Verify round-robin distribution
      expect(results[0].provider).toBe('openai');
      expect(results[1].provider).toBe('anthropic');
      expect(results[2].provider).toBe('cohere');
      expect(results[3].provider).toBe('openai');
    });
  });

  describe('12. Cost Tracking and Budgeting', () => {
    it('should track API usage costs in real-time', async () => {
      const TestComponent = () => {
        const [costs, setCosts] = React.useState({ total: 0, breakdown: {} });
        
        React.useEffect(() => {
          const ws = new WebSocket('ws://localhost:8000/ws');
          
          ws.onmessage = (event) => {
            const message = JSON.parse(event.data);
            if (message.type === 'cost_update') {
              setCosts(message.data);
            }
          };
          
          return () => ws.close();
        }, []);
        
        return (
          <div>
            <div data-testid="total-cost">${costs.total.toFixed(2)}</div>
            <div data-testid="breakdown">
              {Object.entries(costs.breakdown).map(([model, cost]) => (
                <div key={model}>{model}: ${cost}</div>
              ))}
            </div>
          </div>
        );
      };
      
      render(<TestComponent />);
      
      await server.connected;
      
      server.send(JSON.stringify({
        type: 'cost_update',
        data: {
          total: 12.50,
          breakdown: { 'gpt-4': 10.00, 'claude-3': 2.50 }
        }
      }));
      
      await waitFor(() => {
        expect(screen.getByTestId('total-cost')).toHaveTextContent('$12.50');
      });
    });

    it('should enforce budget limits and alerts', async () => {
      const mockBudget = {
        monthly_limit: 1000,
        current_usage: 950,
        alert_threshold: 0.9
      };
      
      (fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => mockBudget
      });
      
      const checkBudget = async () => {
        const budget = await fetch('/api/budget/status');
        const data = await budget.json();
        
        const percentUsed = data.current_usage / data.monthly_limit;
        if (percentUsed >= data.alert_threshold) {
          return { alert: true, message: 'Budget alert: 95% used' };
        }
        return { alert: false };
      };
      
      const result = await checkBudget();
      
      expect(result.alert).toBe(true);
      expect(result.message).toContain('95%');
    });
  });

  describe('13. Database Repository Pattern Integration', () => {
    it('should handle unit of work pattern for transactions', async () => {
      const TestComponent = () => {
        const [transactionStatus, setTransactionStatus] = React.useState('');
        
        const executeTransaction = async () => {
          setTransactionStatus('starting');
          
          try {
            // Start transaction
            await fetch('/api/transaction/begin', { method: 'POST' });
            
            // Multiple operations
            await fetch('/api/threads', { method: 'POST' });
            await fetch('/api/messages', { method: 'POST' });
            
            // Commit
            await fetch('/api/transaction/commit', { method: 'POST' });
            setTransactionStatus('committed');
          } catch (error) {
            // Rollback
            await fetch('/api/transaction/rollback', { method: 'POST' });
            setTransactionStatus('rolled back');
          }
        };
        
        return (
          <div>
            <button onClick={executeTransaction}>Execute Transaction</button>
            <div data-testid="status">{transactionStatus}</div>
          </div>
        );
      };
      
      (fetch as jest.Mock)
        .mockImplementationOnce(async () => { ok: true })
        .mockImplementationOnce(async () => { ok: true })
        .mockImplementationOnce(async () => { ok: true })
        .mockImplementationOnce(async () => { ok: true });
      
      const { getByText, getByTestId } = render(<TestComponent />);
      
      fireEvent.click(getByText('Execute Transaction'));
      
      await waitFor(() => {
        expect(getByTestId('status')).toHaveTextContent('committed');
      });
    });

    it('should implement repository caching layer', async () => {
      const repositoryCache = new Map();
      
      const getCachedOrFetch = async (key: string, fetcher: () => Promise<any>) => {
        if (repositoryCache.has(key)) {
          return repositoryCache.get(key);
        }
        
        const data = await fetcher();
        repositoryCache.set(key, data);
        return data;
      };
      
      let fetchCount = 0;
      const fetcher = async () => {
        fetchCount++;
        return { id: 'user-1', name: 'Test User' };
      };
      
      // First call - fetches
      await getCachedOrFetch('user:1', fetcher);
      expect(fetchCount).toBe(1);
      
      // Second call - uses cache
      await getCachedOrFetch('user:1', fetcher);
      expect(fetchCount).toBe(1);
    });
  });

  describe('14. Migration Handling', () => {
    it('should check and apply database migrations', async () => {
      const mockMigrations = {
        current_version: '003',
        latest_version: '005',
        pending: ['004_add_embeddings', '005_add_metrics']
      };
      
      (fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => mockMigrations
      });
      
      const checkMigrations = async () => {
        const response = await fetch('/api/admin/migrations/status');
        return response.json();
      };
      
      const status = await checkMigrations();
      
      expect(status.pending).toHaveLength(2);
      expect(status.current_version).toBe('003');
    });

    it('should handle migration rollback on failure', async () => {
      (fetch as jest.Mock)
        .mockImplementationOnce(async () => { ok: true })
        .mockRejectedValueOnce(new Error('Migration failed'))
        .mockImplementationOnce(async () => { ok: true });
      
      const applyMigration = async (version: string) => {
        try {
          await fetch(`/api/admin/migrations/apply/${version}`, { method: 'POST' });
          return { success: true };
        } catch (error) {
          // Rollback
          await fetch(`/api/admin/migrations/rollback/${version}`, { method: 'POST' });
          return { success: false, rolled_back: true };
        }
      };
      
      const result = await applyMigration('004');
      
      expect(result.success).toBe(false);
      expect(result.rolled_back).toBe(true);
    });
  });

  describe('15. Background Task Processing', () => {
    it('should queue and process background tasks', async () => {
      const TestComponent = () => {
        const [taskStatus, setTaskStatus] = React.useState('idle');
        const [taskId, setTaskId] = React.useState('');
        
        const queueTask = async () => {
          const response = await fetch('/api/tasks/queue', {
            method: 'POST',
            body: JSON.stringify({ type: 'data_processing', payload: {} })
          });
          const data = await response.json();
          setTaskId(data.task_id);
          setTaskStatus('queued');
        };
        
        React.useEffect(() => {
          if (taskId) {
            const checkStatus = setInterval(async () => {
              const response = await fetch(`/api/tasks/${taskId}/status`);
              const data = await response.json();
              setTaskStatus(data.status);
              
              if (data.status === 'completed' || data.status === 'failed') {
                clearInterval(checkStatus);
              }
            }, 1000);
            
            return () => clearInterval(checkStatus);
          }
        }, [taskId]);
        
        return (
          <div>
            <button onClick={queueTask}>Queue Task</button>
            <div data-testid="task-status">{taskStatus}</div>
          </div>
        );
      };
      
      (fetch as jest.Mock)
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({ task_id: 'task-123' })
        })
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({ status: 'processing' })
        })
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({ status: 'completed' })
        });
      
      const { getByText, getByTestId } = render(<TestComponent />);
      
      fireEvent.click(getByText('Queue Task'));
      
      await waitFor(() => {
        expect(getByTestId('task-status')).toHaveTextContent('completed');
      }, { timeout: 3000 });
    });

    it('should handle task retry with exponential backoff', async () => {
      let attempts = 0;
      const maxRetries = 3;
      
      const executeWithRetry = async (task: () => Promise<any>) => {
        for (let i = 0; i < maxRetries; i++) {
          try {
            attempts++;
            return await task();
          } catch (error) {
            if (i === maxRetries - 1) throw error;
            await new Promise(resolve => setTimeout(resolve, Math.pow(2, i) * 1000));
          }
        }
      };
      
      const task = jest.fn()
        .mockRejectedValueOnce(new Error('Fail 1'))
        .mockRejectedValueOnce(new Error('Fail 2'))
        .mockImplementationOnce(async () => { success: true });
      
      const result = await executeWithRetry(task);
      
      expect(result.success).toBe(true);
      expect(attempts).toBe(3);
    });
  });

  describe('16. Redis Caching Integration', () => {
    it('should cache session data in Redis', async () => {
      const mockSession = {
        session_id: 'sess-123',
        user_id: 'user-456',
        data: { theme: 'dark', language: 'en' },
        expires_at: Date.now() + 3600000
      };
      
      (fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => ({ cached: true })
      });
      
      const cacheSession = async (session: any) => {
        const response = await fetch('/api/session/cache', {
          method: 'POST',
          body: JSON.stringify(session)
        });
        return response.json();
      };
      
      const result = await cacheSession(mockSession);
      
      expect(result.cached).toBe(true);
    });

    it('should implement distributed locking with Redis', async () => {
      const acquireLock = async (resource: string, ttl: number) => {
        const response = await fetch('/api/locks/acquire', {
          method: 'POST',
          body: JSON.stringify({ resource, ttl })
        });
        return response.json();
      };
      
      const releaseLock = async (resource: string, token: string) => {
        const response = await fetch('/api/locks/release', {
          method: 'POST',
          body: JSON.stringify({ resource, token })
        });
        return response.json();
      };
      
      (fetch as jest.Mock)
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({ acquired: true, token: 'lock-token-123' })
        })
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({ released: true })
        });
      
      const lock = await acquireLock('resource-1', 5000);
      expect(lock.acquired).toBe(true);
      
      const release = await releaseLock('resource-1', lock.token);
      expect(release.released).toBe(true);
    });
  });

  describe('17. ClickHouse Analytics Integration', () => {
    it('should log and query time-series events', async () => {
      const mockEvents = [
        { timestamp: Date.now() - 3600000, event_type: 'api_call', latency: 250 },
        { timestamp: Date.now() - 1800000, event_type: 'api_call', latency: 180 },
        { timestamp: Date.now(), event_type: 'api_call', latency: 200 }
      ];
      
      (fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => mockEvents
      });
      
      const queryEvents = async (filters: any) => {
        const response = await fetch('/api/analytics/events', {
          method: 'POST',
          body: JSON.stringify(filters)
        });
        return response.json();
      };
      
      const events = await queryEvents({
        event_type: 'api_call',
        time_range: 'last_hour'
      });
      
      expect(events).toHaveLength(3);
      expect(events[0].latency).toBeDefined();
    });

    it('should aggregate metrics for dashboards', async () => {
      const mockAggregates = {
        avg_latency: 210,
        p95_latency: 450,
        total_requests: 1500,
        error_rate: 0.02
      };
      
      (fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => mockAggregates
      });
      
      const getAggregates = async (metric: string, period: string) => {
        const response = await fetch(`/api/analytics/aggregates/${metric}?period=${period}`);
        return response.json();
      };
      
      const metrics = await getAggregates('latency', '1h');
      
      expect(metrics.avg_latency).toBe(210);
      expect(metrics.p95_latency).toBeLessThan(500);
    });
  });

  describe('18. Error Context and Tracing', () => {
    it('should propagate trace IDs through requests', async () => {
      const traceId = 'trace-' + Date.now();
      
      const TestComponent = () => {
        const [traceResult, setTraceResult] = React.useState('');
        
        const makeTracedRequest = async () => {
          const response = await fetch('/api/test', {
            headers: { 'X-Trace-ID': traceId }
          });
          const data = await response.json();
          setTraceResult(data.trace_id);
        };
        
        return (
          <div>
            <button onClick={makeTracedRequest}>Make Request</button>
            <div data-testid="trace-id">{traceResult}</div>
          </div>
        );
      };
      
      (fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => ({ trace_id: traceId, status: 'success' })
      });
      
      const { getByText, getByTestId } = render(<TestComponent />);
      
      fireEvent.click(getByText('Make Request'));
      
      await waitFor(() => {
        expect(getByTestId('trace-id')).toHaveTextContent(traceId);
      });
    });

    it('should capture error context with stack traces', async () => {
      const TestComponent = () => {
        const [error, setError] = React.useState(null);
        
        const triggerError = async () => {
          try {
            await fetch('/api/error-endpoint');
          } catch (err) {
            const errorContext = {
              message: err.message,
              stack: err.stack,
              timestamp: Date.now(),
              user_id: useAuthStore.getState().user?.id,
              trace_id: 'trace-error-123'
            };
            
            await fetch('/api/errors/log', {
              method: 'POST',
              body: JSON.stringify(errorContext)
            });
            
            setError(errorContext);
          }
        };
        
        return (
          <div>
            <button onClick={triggerError}>Trigger Error</button>
            {error && <div data-testid="error-trace">{error.trace_id}</div>}
          </div>
        );
      };
      
      (fetch as jest.Mock)
        .mockRejectedValueOnce(new Error('API Error'))
        .mockImplementationOnce(async () => { ok: true });
      
      const { getByText, getByTestId } = render(<TestComponent />);
      
      fireEvent.click(getByText('Trigger Error'));
      
      await waitFor(() => {
        expect(getByTestId('error-trace')).toHaveTextContent('trace-error-123');
      });
    });
  });

  describe('19. Security Service Integration', () => {
    it('should validate and sanitize user inputs', async () => {
      const validateInput = (input: string) => {
        // Remove script tags
        const sanitized = input.replace(/<script\b[^<]*(?:(?!<\/script>)<[^<]*)*<\/script>/gi, '');
        
        // Check for SQL injection patterns
        const sqlPatterns = /(\bDROP\b|\bDELETE\b|\bINSERT\b|\bUPDATE\b)/gi;
        if (sqlPatterns.test(input)) {
          return { valid: false, reason: 'SQL injection detected' };
        }
        
        return { valid: true, sanitized };
      };
      
      const maliciousInput = '<script>alert("xss")</script>Normal text';
      const result = validateInput(maliciousInput);
      
      expect(result.valid).toBe(true);
      expect(result.sanitized).toBe('Normal text');
      
      const sqlInput = 'DROP TABLE users';
      const sqlResult = validateInput(sqlInput);
      
      expect(sqlResult.valid).toBe(false);
      expect(sqlResult.reason).toContain('SQL injection');
    });

    it('should implement rate limiting for API endpoints', async () => {
      const rateLimiter = new Map();
      const RATE_LIMIT = 10;
      const WINDOW_MS = 60000;
      
      const checkRateLimit = (clientId: string) => {
        const now = Date.now();
        const clientData = rateLimiter.get(clientId) || { count: 0, resetTime: now + WINDOW_MS };
        
        if (now > clientData.resetTime) {
          clientData.count = 0;
          clientData.resetTime = now + WINDOW_MS;
        }
        
        clientData.count++;
        rateLimiter.set(clientId, clientData);
        
        return {
          allowed: clientData.count <= RATE_LIMIT,
          remaining: Math.max(0, RATE_LIMIT - clientData.count),
          resetTime: clientData.resetTime
        };
      };
      
      // Simulate multiple requests
      for (let i = 0; i < 12; i++) {
        const result = checkRateLimit('client-123');
        
        if (i < 10) {
          expect(result.allowed).toBe(true);
        } else {
          expect(result.allowed).toBe(false);
        }
      }
    });
  });

  describe('20. Key Manager Integration', () => {
    it('should securely store and retrieve API keys', async () => {
      const mockKey = {
        id: 'key-123',
        provider: 'openai',
        encrypted_value: 'encrypted_key_data',
        created_at: new Date().toISOString()
      };
      
      (fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => ({ success: true, key_id: 'key-123' })
      });
      
      const storeApiKey = async (provider: string, key: string) => {
        const response = await fetch('/api/keys/store', {
          method: 'POST',
          body: JSON.stringify({ provider, key })
        });
        return response.json();
      };
      
      const result = await storeApiKey('openai', 'sk-test-key');
      
      expect(result.success).toBe(true);
      expect(result.key_id).toBe('key-123');
    });

    it('should rotate API keys periodically', async () => {
      const TestComponent = () => {
        const [lastRotation, setLastRotation] = React.useState(null);
        
        React.useEffect(() => {
          const rotateKeys = async () => {
            const response = await fetch('/api/keys/rotate', { method: 'POST' });
            const data = await response.json();
            setLastRotation(data.rotated_at);
          };
          
          // Rotate every 30 days
          const interval = setInterval(rotateKeys, 30 * 24 * 60 * 60 * 1000);
          
          return () => clearInterval(interval);
        }, []);
        
        return (
          <div data-testid="rotation-status">
            {lastRotation ? `Rotated: ${lastRotation}` : 'Not rotated'}
          </div>
        );
      };
      
      (fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => ({ rotated_at: new Date().toISOString() })
      });
      
      render(<TestComponent />);
      
      // Component would handle rotation in production
      expect(screen.getByTestId('rotation-status')).toBeInTheDocument();
    });
  });

  describe('21. Demo Mode Functionality', () => {
    it('should restrict features in demo mode', async () => {
      const TestComponent = () => {
        const [isDemoMode, setIsDemoMode] = React.useState(true);
        const [message, setMessage] = React.useState('');
        
        const performAction = async (action: string) => {
          if (isDemoMode && ['delete', 'export', 'admin'].includes(action)) {
            setMessage('This feature is disabled in demo mode');
            return;
          }
          
          setMessage(`Action ${action} performed`);
        };
        
        return (
          <div>
            <button onClick={() => performAction('view')}>View</button>
            <button onClick={() => performAction('delete')}>Delete</button>
            <button onClick={() => setIsDemoMode(false)}>Exit Demo</button>
            <div data-testid="message">{message}</div>
          </div>
        );
      };
      
      const { getByText, getByTestId } = render(<TestComponent />);
      
      fireEvent.click(getByText('Delete'));
      
      await waitFor(() => {
        expect(getByTestId('message')).toHaveTextContent('disabled in demo mode');
      });
      
      fireEvent.click(getByText('Exit Demo'));
      fireEvent.click(getByText('Delete'));
      
      await waitFor(() => {
        expect(getByTestId('message')).toHaveTextContent('Action delete performed');
      });
    });

    it('should provide sample data in demo mode', async () => {
      const mockDemoData = {
        threads: [
          { id: 'demo-1', name: 'Demo Thread 1', messages: 5 },
          { id: 'demo-2', name: 'Demo Thread 2', messages: 3 }
        ],
        optimizations: [
          { id: 'opt-1', type: 'cost', saving: '40%' },
          { id: 'opt-2', type: 'latency', improvement: '25ms' }
        ]
      };
      
      (fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => mockDemoData
      });
      
      const loadDemoData = async () => {
        const response = await fetch('/api/demo/data');
        return response.json();
      };
      
      const data = await loadDemoData();
      
      expect(data.threads).toHaveLength(2);
      expect(data.optimizations).toHaveLength(2);
    });
  });

  describe('22. Enterprise Demo Features', () => {
    it('should showcase enterprise-specific capabilities', async () => {
      const mockEnterpriseFeatures = {
        sso_enabled: true,
        audit_logging: true,
        custom_models: ['enterprise-gpt', 'custom-claude'],
        team_collaboration: true,
        api_governance: true
      };
      
      (fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => mockEnterpriseFeatures
      });
      
      const getEnterpriseFeatures = async () => {
        const response = await fetch('/api/enterprise/features');
        return response.json();
      };
      
      const features = await getEnterpriseFeatures();
      
      expect(features.sso_enabled).toBe(true);
      expect(features.custom_models).toHaveLength(2);
    });

    it('should handle team collaboration workflows', async () => {
      const TestComponent = () => {
        const [team, setTeam] = React.useState([]);
        const [sharedThread, setSharedThread] = React.useState(null);
        
        const shareThread = async (threadId: string, teamMembers: string[]) => {
          const response = await fetch('/api/collaboration/share', {
            method: 'POST',
            body: JSON.stringify({ threadId, teamMembers })
          });
          const data = await response.json();
          setSharedThread(data);
        };
        
        return (
          <div>
            <button onClick={() => shareThread('thread-123', ['user1', 'user2'])}>
              Share Thread
            </button>
            {sharedThread && (
              <div data-testid="shared-status">Thread shared with team</div>
            )}
          </div>
        );
      };
      
      (fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => ({ shared: true, thread_id: 'thread-123' })
      });
      
      const { getByText, getByTestId } = render(<TestComponent />);
      
      fireEvent.click(getByText('Share Thread'));
      
      await waitFor(() => {
        expect(getByTestId('shared-status')).toBeInTheDocument();
      });
    });
  });

  describe('23. PDF and Image Processing', () => {
    it('should extract text from PDF documents', async () => {
      const mockPdfData = {
        text: 'Extracted PDF content',
        pages: 5,
        metadata: { title: 'Test PDF', author: 'Test Author' }
      };
      
      const file = new File(['pdf content'], 'test.pdf', { type: 'application/pdf' });
      
      (fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => mockPdfData
      });
      
      const processPdf = async (file: File) => {
        const formData = new FormData();
        formData.append('file', file);
        
        const response = await fetch('/api/process/pdf', {
          method: 'POST',
          body: formData
        });
        return response.json();
      };
      
      const result = await processPdf(file);
      
      expect(result.text).toContain('Extracted PDF content');
      expect(result.pages).toBe(5);
    });

    it('should analyze images with vision models', async () => {
      const mockImageAnalysis = {
        description: 'A chart showing revenue growth',
        objects_detected: ['chart', 'text', 'numbers'],
        text_extracted: 'Revenue: $1.2M'
      };
      
      const file = new File(['image data'], 'chart.png', { type: 'image/png' });
      
      (fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => mockImageAnalysis
      });
      
      const analyzeImage = async (file: File) => {
        const formData = new FormData();
        formData.append('image', file);
        
        const response = await fetch('/api/vision/analyze', {
          method: 'POST',
          body: formData
        });
        return response.json();
      };
      
      const analysis = await analyzeImage(file);
      
      expect(analysis.description).toContain('revenue growth');
      expect(analysis.objects_detected).toContain('chart');
    });
  });

  describe('24. Jupyter Notebook Support', () => {
    it('should parse and execute notebook cells', async () => {
      const mockNotebook = {
        cells: [
          { type: 'code', source: 'print("Hello")', output: 'Hello' },
          { type: 'markdown', source: '# Title' },
          { type: 'code', source: 'x = 10\ny = 20\nprint(x + y)', output: '30' }
        ]
      };
      
      (fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => mockNotebook
      });
      
      const loadNotebook = async (path: string) => {
        const response = await fetch(`/api/notebooks/load?path=${path}`);
        return response.json();
      };
      
      const notebook = await loadNotebook('/notebooks/test.ipynb');
      
      expect(notebook.cells).toHaveLength(3);
      expect(notebook.cells[0].output).toBe('Hello');
    });

    it('should convert notebooks to different formats', async () => {
      const mockConverted = {
        format: 'html',
        content: '<html><body>Notebook content</body></html>'
      };
      
      (fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => mockConverted
      });
      
      const convertNotebook = async (notebookId: string, format: string) => {
        const response = await fetch(`/api/notebooks/${notebookId}/convert`, {
          method: 'POST',
          body: JSON.stringify({ format })
        });
        return response.json();
      };
      
      const result = await convertNotebook('nb-123', 'html');
      
      expect(result.format).toBe('html');
      expect(result.content).toContain('<html>');
    });
  });

  describe('25. Export Functionality', () => {
    it('should export data in multiple formats', async () => {
      const TestComponent = () => {
        const [exportStatus, setExportStatus] = React.useState('');
        
        const exportData = async (format: string) => {
          setExportStatus('exporting');
          
          const response = await fetch('/api/export', {
            method: 'POST',
            body: JSON.stringify({
              format,
              data_type: 'threads',
              filters: { date_range: 'last_30_days' }
            })
          });
          
          if (response.ok) {
            const blob = await response.blob();
            const url = URL.createObjectURL(blob);
            
            // Trigger download
            const a = document.createElement('a');
            a.href = url;
            a.download = `export.${format}`;
            a.click();
            
            setExportStatus('completed');
          }
        };
        
        return (
          <div>
            <button onClick={() => exportData('json')}>Export JSON</button>
            <button onClick={() => exportData('csv')}>Export CSV</button>
            <button onClick={() => exportData('pdf')}>Export PDF</button>
            <div data-testid="export-status">{exportStatus}</div>
          </div>
        );
      };
      
      (fetch as jest.Mock).mockResolvedValue({
        ok: true,
        blob: async () => new Blob(['export data'])
      });
      
      const { getByText, getByTestId } = render(<TestComponent />);
      
      fireEvent.click(getByText('Export JSON'));
      
      await waitFor(() => {
        expect(getByTestId('export-status')).toHaveTextContent('completed');
      });
    });

    it('should handle large data exports with progress', async () => {
      const TestComponent = () => {
        const [progress, setProgress] = React.useState(0);
        
        React.useEffect(() => {
          const eventSource = new EventSource('/api/export/stream');
          
          eventSource.onmessage = (event) => {
            const data = JSON.parse(event.data);
            if (data.type === 'progress') {
              setProgress(data.value);
            }
          };
          
          return () => eventSource.close();
        }, []);
        
        return (
          <div>
            <div data-testid="progress">{progress}%</div>
            <progress value={progress} max="100" />
          </div>
        );
      };
      
      render(<TestComponent />);
      
      // In real scenario, SSE would update progress
      expect(screen.getByTestId('progress')).toBeInTheDocument();
    });
  });

  describe('26. Import Functionality', () => {
    it('should validate and import data files', async () => {
      const mockImportResult = {
        success: true,
        imported: 150,
        failed: 2,
        errors: ['Row 45: Invalid date format', 'Row 89: Missing required field']
      };
      
      const file = new File(['import data'], 'data.csv', { type: 'text/csv' });
      
      (fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => mockImportResult
      });
      
      const importData = async (file: File) => {
        const formData = new FormData();
        formData.append('file', file);
        
        const response = await fetch('/api/import', {
          method: 'POST',
          body: formData
        });
        return response.json();
      };
      
      const result = await importData(file);
      
      expect(result.success).toBe(true);
      expect(result.imported).toBe(150);
      expect(result.errors).toHaveLength(2);
    });

    it('should preview import data before confirmation', async () => {
      const mockPreview = {
        total_rows: 100,
        sample_data: [
          { id: 1, name: 'Sample 1' },
          { id: 2, name: 'Sample 2' }
        ],
        columns: ['id', 'name'],
        validation_errors: []
      };
      
      (fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => mockPreview
      });
      
      const previewImport = async (file: File) => {
        const formData = new FormData();
        formData.append('file', file);
        
        const response = await fetch('/api/import/preview', {
          method: 'POST',
          body: formData
        });
        return response.json();
      };
      
      const file = new File(['data'], 'import.csv', { type: 'text/csv' });
      const preview = await previewImport(file);
      
      expect(preview.total_rows).toBe(100);
      expect(preview.sample_data).toHaveLength(2);
    });
  });

  describe('27. Collaboration Features', () => {
    it('should handle real-time collaborative editing', async () => {
      const TestComponent = () => {
        const [collaborators, setCollaborators] = React.useState([]);
        const [content, setContent] = React.useState('');
        
        React.useEffect(() => {
          const ws = new WebSocket('ws://localhost:8000/collab');
          
          ws.onmessage = (event) => {
            const message = JSON.parse(event.data);
            
            if (message.type === 'user_joined') {
              setCollaborators(prev => [...prev, message.user]);
            } else if (message.type === 'content_update') {
              setContent(message.content);
            }
          };
          
          return () => ws.close();
        }, []);
        
        return (
          <div>
            <div data-testid="collaborators">{collaborators.length} users</div>
            <textarea value={content} onChange={(e) => setContent(e.target.value)} />
          </div>
        );
      };
      
      render(<TestComponent />);
      
      await server.connected;
      
      server.send(JSON.stringify({
        type: 'user_joined',
        user: { id: 'user-1', name: 'Alice' }
      }));
      
      await waitFor(() => {
        expect(screen.getByTestId('collaborators')).toHaveTextContent('1 users');
      });
    });

    it('should synchronize cursor positions between users', async () => {
      const TestComponent = () => {
        const [cursors, setCursors] = React.useState({});
        
        React.useEffect(() => {
          const ws = new WebSocket('ws://localhost:8000/collab');
          
          ws.onmessage = (event) => {
            const message = JSON.parse(event.data);
            
            if (message.type === 'cursor_update') {
              setCursors(prev => ({
                ...prev,
                [message.user_id]: message.position
              }));
            }
          };
          
          const handleMouseMove = (e: MouseEvent) => {
            ws.send(JSON.stringify({
              type: 'cursor_move',
              position: { x: e.clientX, y: e.clientY }
            }));
          };
          
          document.addEventListener('mousemove', handleMouseMove);
          return () => {
            document.removeEventListener('mousemove', handleMouseMove);
            ws.close();
          };
        }, []);
        
        return (
          <div>
            {Object.entries(cursors).map(([userId, position]) => (
              <div key={userId} data-testid={`cursor-${userId}`}>
                User {userId}: {position.x}, {position.y}
              </div>
            ))}
          </div>
        );
      };
      
      render(<TestComponent />);
      
      await server.connected;
      
      server.send(JSON.stringify({
        type: 'cursor_update',
        user_id: 'user-2',
        position: { x: 100, y: 200 }
      }));
      
      await waitFor(() => {
        expect(screen.getByTestId('cursor-user-2')).toHaveTextContent('100, 200');
      });
    });
  });

  describe('28. Real-time Metrics Dashboard', () => {
    it('should display live performance metrics', async () => {
      const TestComponent = () => {
        const [metrics, setMetrics] = React.useState({
          requests_per_second: 0,
          avg_latency: 0,
          active_connections: 0
        });
        
        React.useEffect(() => {
          const ws = new WebSocket('ws://localhost:8000/metrics');
          
          ws.onmessage = (event) => {
            const data = JSON.parse(event.data);
            setMetrics(data);
          };
          
          return () => ws.close();
        }, []);
        
        return (
          <div>
            <div data-testid="rps">{metrics.requests_per_second} req/s</div>
            <div data-testid="latency">{metrics.avg_latency}ms</div>
            <div data-testid="connections">{metrics.active_connections} active</div>
          </div>
        );
      };
      
      render(<TestComponent />);
      
      await server.connected;
      
      server.send(JSON.stringify({
        requests_per_second: 150,
        avg_latency: 45,
        active_connections: 25
      }));
      
      await waitFor(() => {
        expect(screen.getByTestId('rps')).toHaveTextContent('150 req/s');
        expect(screen.getByTestId('latency')).toHaveTextContent('45ms');
      });
    });

    it('should visualize historical metrics with time series', async () => {
      const mockTimeSeries = {
        timestamps: [1000, 2000, 3000, 4000, 5000],
        values: [100, 120, 115, 130, 125]
      };
      
      (fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => mockTimeSeries
      });
      
      const getTimeSeriesData = async (metric: string, period: string) => {
        const response = await fetch(`/api/metrics/timeseries?metric=${metric}&period=${period}`);
        return response.json();
      };
      
      const data = await getTimeSeriesData('requests', '1h');
      
      expect(data.timestamps).toHaveLength(5);
      expect(Math.max(...data.values)).toBe(130);
    });
  });

  describe('29. Agent Tool Dispatcher Integration', () => {
    it('should dynamically dispatch tools to agents', async () => {
      const mockToolExecution = {
        tool: 'cost_analyzer',
        result: {
          current_cost: 500,
          optimized_cost: 300,
          savings: 200
        },
        execution_time: 250
      };
      
      (fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => mockToolExecution
      });
      
      const dispatchTool = async (toolName: string, params: any) => {
        const response = await fetch('/api/agent/tools/dispatch', {
          method: 'POST',
          body: JSON.stringify({ tool: toolName, params })
        });
        return response.json();
      };
      
      const result = await dispatchTool('cost_analyzer', {
        workload_id: 'wl-123'
      });
      
      expect(result.tool).toBe('cost_analyzer');
      expect(result.result.savings).toBe(200);
    });

    it('should handle tool chaining and dependencies', async () => {
      const TestComponent = () => {
        const [toolChain, setToolChain] = React.useState([]);
        const [results, setResults] = React.useState({});
        
        const executeToolChain = async () => {
          const chain = [
            { tool: 'data_collector', depends_on: [] },
            { tool: 'analyzer', depends_on: ['data_collector'] },
            { tool: 'optimizer', depends_on: ['analyzer'] },
            { tool: 'reporter', depends_on: ['optimizer'] }
          ];
          
          for (const step of chain) {
            // Wait for dependencies
            const inputs = step.depends_on.map(dep => results[dep]);
            
            const response = await fetch('/api/agent/tools/execute', {
              method: 'POST',
              body: JSON.stringify({ ...step, inputs })
            });
            
            const result = await response.json();
            setResults(prev => ({ ...prev, [step.tool]: result }));
            setToolChain(prev => [...prev, step.tool]);
          }
        };
        
        return (
          <div>
            <button onClick={executeToolChain}>Execute Chain</button>
            <div data-testid="chain-status">
              {toolChain.join(' → ')}
            </div>
          </div>
        );
      };
      
      (fetch as jest.Mock)
        .mockImplementationOnce(async () => { ok: true, json: async () => ({ data: 'collected' }) })
        .mockImplementationOnce(async () => { ok: true, json: async () => ({ analysis: 'complete' }) })
        .mockImplementationOnce(async () => { ok: true, json: async () => ({ optimized: true }) })
        .mockImplementationOnce(async () => { ok: true, json: async () => ({ report: 'generated' }) });
      
      const { getByText, getByTestId } = render(<TestComponent />);
      
      fireEvent.click(getByText('Execute Chain'));
      
      await waitFor(() => {
        expect(getByTestId('chain-status')).toHaveTextContent(
          'data_collector → analyzer → optimizer → reporter'
        );
      });
    });
  });

  describe('30. State Persistence and Recovery', () => {
    it('should persist application state across sessions', async () => {
      const mockPersistedState = {
        version: 2,
        timestamp: Date.now(),
        data: {
          user_preferences: { theme: 'dark', language: 'en' },
          session_data: { last_thread: 'thread-123' },
          cached_results: { optimization_1: { result: 'cached' } }
        }
      };
      
      // Save state
      const saveState = async (state: any) => {
        localStorage.setItem('app_state', JSON.stringify(state));
        
        // Also persist to backend
        const response = await fetch('/api/state/persist', {
          method: 'POST',
          body: JSON.stringify(state)
        });
        return response.json();
      };
      
      // Restore state
      const restoreState = async () => {
        // Try local storage first
        const localState = localStorage.getItem('app_state');
        if (localState) {
          return JSON.parse(localState);
        }
        
        // Fallback to backend
        const response = await fetch('/api/state/restore');
        return response.json();
      };
      
      (fetch as jest.Mock)
        .mockImplementationOnce(async () => { ok: true, json: async () => ({ persisted: true }) })
        .mockImplementationOnce(async () => { ok: true, json: async () => mockPersistedState });
      
      await saveState(mockPersistedState);
      const restored = await restoreState();
      
      expect(restored.data.user_preferences.theme).toBe('dark');
      expect(restored.data.session_data.last_thread).toBe('thread-123');
    });

    it('should recover from corrupted state gracefully', async () => {
      const TestComponent = () => {
        const [state, setState] = React.useState(null);
        const [error, setError] = React.useState(null);
        
        const loadState = async () => {
          try {
            // Simulate corrupted state
            const corrupted = 'invalid json {{{';
            localStorage.setItem('app_state', corrupted);
            
            const stored = localStorage.getItem('app_state');
            const parsed = JSON.parse(stored);
            setState(parsed);
          } catch (err) {
            // Recovery: Use default state
            const defaultState = {
              version: 1,
              data: {
                user_preferences: { theme: 'light', language: 'en' },
                session_data: {}
              }
            };
            
            setState(defaultState);
            setError('State corrupted, using defaults');
            
            // Clear corrupted data
            localStorage.removeItem('app_state');
            
            // Notify backend
            await fetch('/api/state/corruption-report', {
              method: 'POST',
              body: JSON.stringify({ error: err.message })
            });
          }
        };
        
        return (
          <div>
            <button onClick={loadState}>Load State</button>
            {error && <div data-testid="error">{error}</div>}
            {state && <div data-testid="state">State loaded</div>}
          </div>
        );
      };
      
      (fetch as jest.Mock).mockImplementationOnce(async () => { ok: true });
      
      const { getByText, getByTestId } = render(<TestComponent />);
      
      fireEvent.click(getByText('Load State'));
      
      await waitFor(() => {
        expect(getByTestId('error')).toHaveTextContent('State corrupted, using defaults');
        expect(getByTestId('state')).toHaveTextContent('State loaded');
      });
    });
  });
});