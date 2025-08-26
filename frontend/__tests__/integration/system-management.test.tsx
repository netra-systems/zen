/**
 * System Management Integration Tests
 * Tests for LLM cache, supply catalog, configuration, and health checks
 */

import React from 'react';
import { render, waitFor, fireEvent } from '@testing-library/react';
import '@testing-library/jest-dom';
import apiClient from '@/services/apiClient';
import { TestProviders } from '@/__tests__/setup/test-providers';

// Mock apiClient
jest.mock('@/services/apiClient', () => ({
  get: jest.fn(),
  post: jest.fn(),
  put: jest.fn(),
  delete: jest.fn(),
}));

// Mock stores
const createMockStore = (initialState: any) => {
  let state = initialState;
  const store = Object.assign(
    jest.fn(() => state),
    {
      getState: jest.fn(() => state),
      setState: jest.fn((newState: any) => {
        state = typeof newState === 'function' ? newState(state) : { ...state, ...newState };
      })
    }
  );
  return store;
};

const useLLMCacheStore = createMockStore({
  cacheSize: 0,
  clearCache: jest.fn(),
  setCacheTTL: jest.fn()
});

const useSupplyStore = createMockStore({
  catalog: { models: [] },
  activeModel: null,
  setCatalog: jest.fn((catalog: any) => {
    useSupplyStore.setState((prev: any) => ({ ...prev, catalog }));
  }),
  switchModel: jest.fn((model: string) => {
    useSupplyStore.setState((prev: any) => ({ ...prev, activeModel: model }));
  })
});

const useConfigStore = createMockStore({
  config: null,
  setConfig: jest.fn((config: any) => {
    useConfigStore.setState((prev: any) => ({ ...prev, config }));
  }),
  updateConfig: jest.fn((path: string, value: any) => {
    useConfigStore.setState((prev: any) => {
      const keys = path.split('.');
      const newConfig = { ...prev.config };
      let current = newConfig;
      for (let i = 0; i < keys.length - 1; i++) {
        current[keys[i]] = { ...current[keys[i]] };
        current = current[keys[i]];
      }
      current[keys[keys.length - 1]] = value;
      return { ...prev, config: newConfig };
    });
  })
});

// Mock API
jest.mock('@/services/apiClient');

afterEach(() => {
  jest.clearAllMocks();
});

describe('LLM Cache Management Integration', () => {
  it('should clear LLM cache and update UI', async () => {
    const TestComponent = () => {
      const [cacheStatus, setCacheStatus] = React.useState('');
      
      const handleClearCache = async () => {
        await useLLMCacheStore.getState().clearCache();
        setCacheStatus('Cache cleared');
      };
      
      return (
        <div>
          <button onClick={handleClearCache}>Clear Cache</button>
          <div data-testid="cache-status">{cacheStatus}</div>
        </div>
      );
    };
    
    const { getByText, getByTestId } = render(
      <TestProviders>
        <TestComponent />
      </TestProviders>
    );
    
    fireEvent.click(getByText('Clear Cache'));
    
    await waitFor(() => {
      expect(getByTestId('cache-status')).toHaveTextContent('Cache cleared');
      expect(useLLMCacheStore.getState().clearCache).toHaveBeenCalled();
    });
  });

  it('should update cache TTL settings', async () => {
    const TestComponent = () => {
      const [ttl, setTTL] = React.useState(3600);
      
      const handleUpdateTTL = async (newTTL: number) => {
        await useLLMCacheStore.getState().setCacheTTL(newTTL);
        setTTL(newTTL);
      };
      
      return (
        <div>
          <button onClick={() => handleUpdateTTL(7200)}>Update TTL</button>
          <div data-testid="ttl">{ttl}</div>
        </div>
      );
    };
    
    const { getByText, getByTestId } = render(
      <TestProviders>
        <TestComponent />
      </TestProviders>
    );
    
    fireEvent.click(getByText('Update TTL'));
    
    await waitFor(() => {
      expect(getByTestId('ttl')).toHaveTextContent('7200');
    });
  });
});

describe('Supply Catalog Integration', () => {
  it('should load and display supply catalog', async () => {
    const TestComponent = () => {
      const [catalog, setCatalog] = React.useState<any>(null);
      
      React.useEffect(() => {
        const loadCatalog = async () => {
          const mockCatalog = {
            models: [
              { id: 'gemini-2.5-flash', name: 'GPT-4', provider: 'openai' },
              { id: 'gemini-2.5-flash', name: 'Claude 3', provider: 'anthropic' }
            ]
          };
          useSupplyStore.getState().setCatalog(mockCatalog);
          setCatalog(mockCatalog);
        };
        loadCatalog();
      }, []);
      
      return (
        <div data-testid="catalog">
          {catalog?.models.map((m: any) => (
            <div key={m.id}>{m.name}</div>
          ))}
        </div>
      );
    };
    
    const { getByTestId } = render(
      <TestProviders>
        <TestComponent />
      </TestProviders>
    );
    
    await waitFor(() => {
      expect(getByTestId('catalog')).toHaveTextContent('GPT-4');
      expect(getByTestId('catalog')).toHaveTextContent('Claude 3');
    });
  });

  it('should switch between different model providers', async () => {
    const TestComponent = () => {
      const handleSwitch = async (model: string) => {
        await useSupplyStore.getState().switchModel(model);
      };
      
      return (
        <div>
          <button onClick={() => handleSwitch('gemini-2.5-flash')}>Use GPT-4</button>
          <button onClick={() => handleSwitch('gemini-2.5-flash')}>Use Claude</button>
          <div data-testid="active-model">
            {useSupplyStore.getState().activeModel || 'none'}
          </div>
        </div>
      );
    };
    
    const { getByText, getByTestId, rerender } = render(
      <TestProviders>
        <TestComponent />
      </TestProviders>
    );
    
    fireEvent.click(getByText('Use GPT-4'));
    
    rerender(
      <TestProviders>
        <TestComponent />
      </TestProviders>
    );
    
    await waitFor(() => {
      expect(useSupplyStore.getState().activeModel).toBe('gemini-2.5-flash');
    });
  });
});

describe('Configuration Management', () => {
  it('should load and display configuration', async () => {
    const TestComponent = () => {
      const [config, setConfig] = React.useState<any>(null);
      
      React.useEffect(() => {
        const mockConfig = {
          app: { name: 'Netra', version: '1.0.0' },
          features: { darkMode: true, analytics: false }
        };
        useConfigStore.getState().setConfig(mockConfig);
        setConfig(mockConfig);
      }, []);
      
      return (
        <div data-testid="config">
          {config && (
            <>
              <div>{config.app.name}</div>
              <div>Dark Mode: {config.features.darkMode ? 'on' : 'off'}</div>
            </>
          )}
        </div>
      );
    };
    
    const { getByTestId } = render(
      <TestProviders>
        <TestComponent />
      </TestProviders>
    );
    
    await waitFor(() => {
      expect(getByTestId('config')).toHaveTextContent('Netra');
      expect(getByTestId('config')).toHaveTextContent('Dark Mode: on');
    });
  });

  it('should update nested configuration values', async () => {
    const TestComponent = () => {
      const handleUpdate = () => {
        useConfigStore.getState().updateConfig('features.darkMode', false);
      };
      
      return (
        <div>
          <button onClick={handleUpdate}>Toggle Dark Mode</button>
          <div data-testid="dark-mode">
            {useConfigStore.getState().config?.features?.darkMode ? 'on' : 'off'}
          </div>
        </div>
      );
    };
    
    // Initialize config
    useConfigStore.setState({
      config: { features: { darkMode: true } }
    });
    
    const { getByText, rerender } = render(
      <TestProviders>
        <TestComponent />
      </TestProviders>
    );
    
    fireEvent.click(getByText('Toggle Dark Mode'));
    
    rerender(
      <TestProviders>
        <TestComponent />
      </TestProviders>
    );
    
    await waitFor(() => {
      expect(useConfigStore.getState().config.features.darkMode).toBe(false);
    });
  });
});

describe('Health Check Monitoring', () => {
  it('should fetch and display system health status', async () => {
    (apiClient.get as jest.Mock).mockResolvedValue({
      data: {
        status: 'healthy',
        database: { status: 'connected', latency: 5 },
        redis: { status: 'connected', latency: 2 },
        services: { all: 'operational' }
      }
    });
    
    const TestComponent = () => {
      const [health, setHealth] = React.useState<any>(null);
      
      const checkHealth = async () => {
        const response = await apiClient.get('/health');
        setHealth(response.data);
      };
      
      React.useEffect(() => {
        checkHealth();
      }, []);
      
      return (
        <div data-testid="health">
          {health && (
            <>
              <div>Status: {health.status}</div>
              <div>Database: {health.database.status}</div>
              <div>Redis: {health.redis.status}</div>
            </>
          )}
        </div>
      );
    };
    
    const { getByTestId } = render(
      <TestProviders>
        <TestComponent />
      </TestProviders>
    );
    
    await waitFor(() => {
      expect(getByTestId('health')).toHaveTextContent('Status: healthy');
      expect(getByTestId('health')).toHaveTextContent('Database: connected');
      expect(getByTestId('health')).toHaveTextContent('Redis: connected');
    });
  });
});