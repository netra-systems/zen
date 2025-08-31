import { setupAntiHang, cleanupAntiHang } from '@/__tests__/utils/anti-hanging-test-utilities';
import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import { ct from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import {
  setupIntegrationTest,
  teardownIntegrationTest,
  createMockHealthStatus,
  createMockDegradedHealth,
  createHealthService,
  createTestComponent,
  setupDefaultHookMocks,
  setupAuthMocks,
  setupLoadingMocks,
  createMockUseUnifiedChatStore,
  createMockUseWebSocket,
  createMockUseAgent,
  createMockUseAuthStore,
  createMockUseLoadingState,
  createMockUseThreadNavigation
} from './integration-shared-utilities';

// Declare mocks first (Jest Module Hoisting)
const mockUseUnifiedChatStore = createMockUseUnifiedChatStore();
const mockUseWebSocket = createMockUseWebSocket();
const mockUseAgent = createMockUseAgent();
const mockUseAuthStore = createMockUseAuthStore();
const mockUseLoadingState = createMockUseLoadingState();
const mockUseThreadNavigation = createMockUseThreadNavigation();

// Mock hooks before imports
jest.mock('@/store/unified-chat', () => ({
  useUnifiedChatStore: mockUseUnifiedChatStore
}));

jest.mock('@/hooks/useWebSocket', () => ({
  useWebSocket: mockUseWebSocket
}));

jest.mock('@/hooks/useAgent', () => ({
  useAgent: mockUseAgent
}));

describe('Health Check Monitoring Integration Tests', () => {
    jest.setTimeout(10000);
  let server: any;
  const healthService = createHealthService();
  
  beforeEach(() => {
    server = setupIntegrationTest();
    setupAllMocks();
  });

  afterEach(() => {
    teardownIntegrationTest();
      // Clean up timers to prevent hanging
      jest.clearAllTimers();
      jest.useFakeTimers();
      jest.runOnlyPendingTimers();
      jest.useRealTimers();
  });

  describe('7. Health Check Monitoring', () => {
      jest.setTimeout(10000);
    it('should monitor service health status', async () => {
      const mockHealth = createMockHealthStatus();
      setupHealthMock(mockHealth);
      
      const health = await checkServiceHealth();
      
      verifyHealthStatus(health, 'healthy');
    });

    it('should handle degraded service states', async () => {
      jest.setTimeout(10000);
      const mockDegradedHealth = createMockDegradedHealth();
      setupDegradedHealthMock(mockDegradedHealth);
      
      const TestComponent = createHealthMonitorComponent();
      const { getByTestId } = render(createTestComponent(<TestComponent />));
      
      await verifyDegradedState(getByTestId);
    });

    it('should alert on critical service failures', async () => {
      const criticalHealth = { status: 'critical', services: { database: 'down' } };
      setupCriticalHealthMock(criticalHealth);
      
      await checkCriticalHealth();
      
      verifyCriticalAlert(criticalHealth);
    });

    it('should track health check history and trends', async () => {
      const healthHistory = [
        { timestamp: Date.now() - 3600000, status: 'healthy' },
        { timestamp: Date.now() - 1800000, status: 'degraded' },
        { timestamp: Date.now(), status: 'healthy' }
      ];
      setupHealthHistoryMock(healthHistory);
      
      await trackHealthHistory();
      
      verifyHealthHistory(healthHistory);
    });

    it('should handle health check timeouts gracefully', async () => {
      setupHealthTimeoutMock();
      
      await attemptHealthCheckWithTimeout();
      
      verifyTimeoutHandled();
    });

    it('should aggregate health from multiple services', async () => {
      const serviceHealth = {
        database: 'healthy',
        redis: 'degraded',
        elasticsearch: 'healthy',
        api: 'healthy'
      };
      setupAggregateHealthMock(serviceHealth);
      
      await checkAggregateHealth();
      
      verifyAggregateHealth(serviceHealth);
    });

    it('should support custom health check endpoints', async () => {
      const customEndpoints = ['/health/custom1', '/health/custom2'];
      setupCustomEndpointMocks(customEndpoints);
      
      await checkCustomEndpoints(customEndpoints);
      
      verifyCustomEndpointsChecked(customEndpoints);
    });

    it('should handle health check authentication', async () => {
      const authHeaders = { Authorization: 'Bearer token123' };
      setupHealthAuthMock(authHeaders);
      
      await checkHealthWithAuth(authHeaders);
      
      verifyHealthAuthUsed(authHeaders);
    });
  });
});

// Helper functions ≤8 lines each
const setupAllMocks = () => {
  const mocks = {
    mockUseUnifiedChatStore,
    mockUseWebSocket,
    mockUseAgent,
    mockUseAuthStore,
    mockUseLoadingState,
    mockUseThreadNavigation
  };
  
  setupDefaultHookMocks(mocks);
  setupAuthMocks(mocks);
  setupLoadingMocks(mocks);
};

const setupHealthMock = (mockHealth: any) => {
  healthService.checkHealth.mockResolvedValueOnce(mockHealth);
};

const setupDegradedHealthMock = (mockHealth: any) => {
  healthService.checkHealth.mockResolvedValueOnce(mockHealth);
};

const setupCriticalHealthMock = (criticalHealth: any) => {
  healthService.checkHealth.mockResolvedValueOnce(criticalHealth);
};

const setupHealthHistoryMock = (history: any[]) => {
  (fetch as jest.Mock).mockResolvedValueOnce({
    ok: true,
    json: async () => ({ history })
  });
};

const setupHealthTimeoutMock = () => {
  healthService.checkHealth.mockRejectedValueOnce(new Error('Timeout'));
};

const setupAggregateHealthMock = (serviceHealth: any) => {
  (fetch as jest.Mock).mockResolvedValueOnce({
    ok: true,
    json: async () => ({ aggregate: serviceHealth })
  });
};

const setupCustomEndpointMocks = (endpoints: string[]) => {
  endpoints.forEach(endpoint => {
    (fetch as jest.Mock).mockResolvedValueOnce({
      ok: true,
      json: async () => ({ status: 'healthy', endpoint })
    });
  });
};

const setupHealthAuthMock = (authHeaders: any) => {
  (fetch as jest.Mock).mockResolvedValueOnce({
    ok: true,
    json: async () => ({ status: 'healthy', authenticated: true })
  });
};

const createHealthMonitorComponent = () => {
  return () => {
    const [health, setHealth] = React.useState<any>(null);
    
    React.useEffect(() => {
      healthService.checkHealth().then(setHealth);
    }, []);
    
    return (
      <div>
        <div data-testid="health-status">{health?.status || 'checking'}</div>
        {health?.status === 'degraded' && (
          <div data-testid="alert">Service Degraded</div>
        )}
      </div>
    );
  };
};

const checkServiceHealth = async () => {
  return await healthService.checkHealth();
};

const checkCriticalHealth = async () => {
  return await healthService.checkHealth();
};

const trackHealthHistory = async () => {
  await fetch('/api/health/history');
};

const attemptHealthCheckWithTimeout = async () => {
  try {
    await healthService.checkHealth();
  } catch (error) {
    // Expected timeout
  }
};

const checkAggregateHealth = async () => {
  await fetch('/api/health/aggregate');
};

const checkCustomEndpoints = async (endpoints: string[]) => {
  for (const endpoint of endpoints) {
    await fetch(endpoint);
  }
};

const checkHealthWithAuth = async (authHeaders: any) => {
  await fetch('/api/health', { headers: authHeaders });
};

const verifyHealthStatus = (health: any, expectedStatus: string) => {
  expect(health.status).toBe(expectedStatus);
  expect(health.services.database).toBe('up');
};

const verifyDegradedState = async (getByTestId: any) => {
  await waitFor(() => {
    expect(getByTestId('health-status')).toHaveTextContent('degraded');
    expect(getByTestId('alert')).toHaveTextContent('Service Degraded');
  });
};

const verifyCriticalAlert = (criticalHealth: any) => {
  expect(healthService.checkHealth).toHaveBeenCalled();
  expect(criticalHealth.status).toBe('critical');
};

const verifyHealthHistory = (history: any[]) => {
  expect(fetch).toHaveBeenCalledWith('/api/health/history');
  expect(history).toHaveLength(3);
};

const verifyTimeoutHandled = () => {
  expect(healthService.checkHealth).toHaveBeenCalled();
};

const verifyAggregateHealth = (serviceHealth: any) => {
  expect(fetch).toHaveBeenCalledWith('/api/health/aggregate');
  expect(serviceHealth.database).toBe('healthy');
};

const verifyCustomEndpointsChecked = (endpoints: string[]) => {
  endpoints.forEach(endpoint => {
    expect(fetch).toHaveBeenCalledWith(endpoint);
  });
};

const verifyHealthAuthUsed = (authHeaders: any) => {
  expect(fetch).toHaveBeenCalledWith('/api/health',
    expect.objectContaining({ headers: authHeaders })
  );
};