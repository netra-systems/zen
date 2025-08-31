import React, { useState, useEffect } from 'react';
import { render, screen, act, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import { InitializationProgress } from '@/components/InitializationProgress';
import { WebSocketProvider, useWebSocket } from '@/providers/WebSocketProvider';
import { useInitializationCoordinator } from '@/hooks/useInitializationCoordinator';
import { useAuth } from '@/hooks/useAuth';
import webSocketService from '@/services/webSocketService';
import { setupAntiHang, cleanupAntiHang } from '@/__tests__/utils/anti-hanging-test-utilities';

// Mock dependencies
jest.mock('@/hooks/useAuth');
jest.mock('@/services/webSocketService');
jest.mock('@/services/reconciliationService', () => ({
  reconciliationService: {
    processMessage: jest.fn((msg) => msg),
    getUnreconciledMessages: jest.fn().mockReturnValue([]),
    clearUnreconciledMessages: jest.fn()
  }
}));
jest.mock('@/lib/logger', () => ({
  debugLogger: {
    debug: jest.fn(),
    error: jest.fn(),
    warn: jest.fn()
  }
}));
jest.mock('@/hooks/useInitializationCoordinator');

// Integration test component that simulates the real initialization flow
const InitializationFlowTestComponent = ({ onPhaseChange }: { onPhaseChange?: (phase: string) => void }) => {
  const [isInitialized, setIsInitialized] = useState(false);
  const { phase, progress } = useInitializationCoordinator();
  const { status: wsStatus } = useWebSocket();
  
  useEffect(() => {
    if (onPhaseChange) {
      onPhaseChange(phase);
    }
    
    if (phase === 'ready') {
      setIsInitialized(true);
    }
  }, [phase, onPhaseChange]);
  
  if (!isInitialized) {
    return (
      <InitializationProgress
        phase={phase}
        progress={progress}
        connectionStatus={wsStatus}
      />
    );
  }
  
  return <div data-testid="app-ready">Application is ready!</div>;
};

describe('Initialization Flow Integration', () => {
  setupAntiHang();
    jest.setTimeout(10000);
  let mockAuth: jest.Mocked<ReturnType<typeof useAuth>>;
  let mockWebSocketService: jest.Mocked<typeof webSocketService>;
  let mockInitializationCoordinator: jest.Mocked<ReturnType<typeof useInitializationCoordinator>>;
  
  beforeEach(() => {
    jest.useFakeTimers();
    
    // Setup auth mock
    mockAuth = {
      token: 'test-token',
      isAuthenticated: true,
      loading: false,
      user: null,
      error: null,
      login: jest.fn(),
      logout: jest.fn(),
      refreshToken: jest.fn()
    };
    (useAuth as jest.Mock).mockReturnValue(mockAuth);
    
    // Setup WebSocket service mock
    mockWebSocketService = {
      connect: jest.fn().mockResolvedValue(undefined),
      disconnect: jest.fn(),
      send: jest.fn(),
      onMessage: null,
      onStatusChange: null,
      isConnected: jest.fn().mockReturnValue(false),
      status: 'CLOSED' as any,
      lastHeartbeat: null
    };
    (webSocketService as any) = mockWebSocketService;
    
    // Setup initialization coordinator mock with default values
    mockInitializationCoordinator = {
      phase: 'auth',
      progress: 0,
      error: null,
      isInitialized: false,
      reset: jest.fn()
    };
    (useInitializationCoordinator as jest.Mock).mockReturnValue(mockInitializationCoordinator);
  });
  
  afterEach(() => {
    jest.clearAllMocks();
    jest.useRealTimers();
      // Clean up timers to prevent hanging
      jest.clearAllTimers();
      jest.useFakeTimers();
      jest.runOnlyPendingTimers();
      jest.useRealTimers();
      cleanupAntiHang();
  });
  
  describe('Complete Initialization Flow', () => {
        setupAntiHang();
      jest.setTimeout(10000);
    it('progresses through all phases to completion', async () => {
      const phaseHistory: string[] = [];
      
      const { rerender } = render(
        <WebSocketProvider>
          <InitializationFlowTestComponent onPhaseChange={(phase) => phaseHistory.push(phase)} />
        </WebSocketProvider>
      );
      
      // Verify initial state
      expect(screen.getByText('Authenticating your session...')).toBeInTheDocument();
      expect(screen.getByText('0% complete')).toBeInTheDocument();
      
      // Progress through auth phase (0-33%)
      await act(async () => {
        mockInitializationCoordinator.phase = 'auth';
        mockInitializationCoordinator.progress = 15;
        (useInitializationCoordinator as jest.Mock).mockReturnValue(mockInitializationCoordinator);
        rerender(
          <WebSocketProvider>
            <InitializationFlowTestComponent onPhaseChange={(phase) => phaseHistory.push(phase)} />
          </WebSocketProvider>
        );
        jest.advanceTimersByTime(500);
      });
      
      expect(screen.getByText('15% complete')).toBeInTheDocument();
      
      // Move to WebSocket phase (33-66%)
      await act(async () => {
        mockInitializationCoordinator.phase = 'websocket';
        mockInitializationCoordinator.progress = 40;
        (useInitializationCoordinator as jest.Mock).mockReturnValue(mockInitializationCoordinator);
        rerender(
          <WebSocketProvider>
            <InitializationFlowTestComponent onPhaseChange={(phase) => phaseHistory.push(phase)} />
          </WebSocketProvider>
        );
        
        // Simulate WebSocket connection
        if (mockWebSocketService.onStatusChange) {
          mockWebSocketService.onStatusChange('CONNECTING' as any);
        }
        jest.advanceTimersByTime(100);
      });
      
      expect(screen.getByText('Connecting to real-time services...')).toBeInTheDocument();
      expect(screen.getByText('40% complete')).toBeInTheDocument();
      
      // WebSocket connected
      await act(async () => {
        mockInitializationCoordinator.progress = 55;
        (useInitializationCoordinator as jest.Mock).mockReturnValue(mockInitializationCoordinator);
        if (mockWebSocketService.onStatusChange) {
          mockWebSocketService.onStatusChange('OPEN' as any);
        }
        rerender(
          <WebSocketProvider>
            <InitializationFlowTestComponent onPhaseChange={(phase) => phaseHistory.push(phase)} />
          </WebSocketProvider>
        );
        jest.advanceTimersByTime(500);
      });
      
      // Move to Store phase (66-100%)
      await act(async () => {
        mockInitializationCoordinator.phase = 'store';
        mockInitializationCoordinator.progress = 75;
        (useInitializationCoordinator as jest.Mock).mockReturnValue(mockInitializationCoordinator);
        rerender(
          <WebSocketProvider>
            <InitializationFlowTestComponent onPhaseChange={(phase) => phaseHistory.push(phase)} />
          </WebSocketProvider>
        );
        jest.advanceTimersByTime(200);
      });
      
      expect(screen.getByText('Loading your workspace...')).toBeInTheDocument();
      expect(screen.getByText('75% complete')).toBeInTheDocument();
      
      // Complete initialization
      await act(async () => {
        mockInitializationCoordinator.phase = 'ready';
        mockInitializationCoordinator.progress = 100;
        mockInitializationCoordinator.isInitialized = true;
        (useInitializationCoordinator as jest.Mock).mockReturnValue(mockInitializationCoordinator);
        rerender(
          <WebSocketProvider>
            <InitializationFlowTestComponent onPhaseChange={(phase) => phaseHistory.push(phase)} />
          </WebSocketProvider>
        );
        jest.advanceTimersByTime(100);
      });
      
      // Should show ready state then transition to app
      await waitFor(() => {
        expect(screen.getByTestId('app-ready')).toBeInTheDocument();
      });
      
      // Verify phase progression
      expect(phaseHistory).toContain('auth');
      expect(phaseHistory).toContain('websocket');
      expect(phaseHistory).toContain('store');
      expect(phaseHistory).toContain('ready');
    });
    
    it('displays smooth progress updates during initialization', async () => {
      const { rerender } = render(
        <WebSocketProvider>
          <InitializationFlowTestComponent />
        </WebSocketProvider>
      );
      
      // Simulate smooth progress increments
      const progressSteps = [0, 10, 20, 33, 40, 50, 66, 75, 85, 95, 100];
      const phases = ['auth', 'auth', 'auth', 'auth', 'websocket', 'websocket', 'websocket', 'store', 'store', 'store', 'ready'];
      
      for (let i = 0; i < progressSteps.length; i++) {
        await act(async () => {
          mockInitializationCoordinator.phase = phases[i] as any;
          mockInitializationCoordinator.progress = progressSteps[i];
          if (phases[i] === 'ready') {
            mockInitializationCoordinator.isInitialized = true;
          }
          (useInitializationCoordinator as jest.Mock).mockReturnValue(mockInitializationCoordinator);
          rerender(
            <WebSocketProvider>
              <InitializationFlowTestComponent />
            </WebSocketProvider>
          );
          jest.advanceTimersByTime(100);
        });
        
        if (progressSteps[i] < 100) {
          expect(screen.getByText(`${progressSteps[i]}% complete`)).toBeInTheDocument();
        }
      }
      
      // Final state should show app ready
      await waitFor(() => {
        expect(screen.getByTestId('app-ready')).toBeInTheDocument();
      });
    });
  });
  
  describe('Error Handling During Initialization', () => {
        setupAntiHang();
      jest.setTimeout(10000);
    it('handles auth phase failure', async () => {
      const { rerender } = render(
        <WebSocketProvider>
          <InitializationFlowTestComponent />
        </WebSocketProvider>
      );
      
      // Simulate auth failure
      await act(async () => {
        mockInitializationCoordinator.phase = 'error';
        mockInitializationCoordinator.progress = 15;
        mockInitializationCoordinator.error = 'Authentication failed';
        (useInitializationCoordinator as jest.Mock).mockReturnValue(mockInitializationCoordinator);
        rerender(
          <WebSocketProvider>
            <InitializationFlowTestComponent />
          </WebSocketProvider>
        );
      });
      
      expect(screen.getByText('Connection issue detected')).toBeInTheDocument();
      expect(screen.queryByTestId('loader')).not.toBeInTheDocument();
    });
    
    it('handles WebSocket connection timeout', async () => {
      const { rerender } = render(
        <WebSocketProvider>
          <InitializationFlowTestComponent />
        </WebSocketProvider>
      );
      
      // Progress to WebSocket phase
      await act(async () => {
        mockInitializationCoordinator.phase = 'websocket';
        mockInitializationCoordinator.progress = 45;
        (useInitializationCoordinator as jest.Mock).mockReturnValue(mockInitializationCoordinator);
        rerender(
          <WebSocketProvider>
            <InitializationFlowTestComponent />
          </WebSocketProvider>
        );
        
        if (mockWebSocketService.onStatusChange) {
          mockWebSocketService.onStatusChange('CONNECTING' as any);
        }
      });
      
      expect(screen.getByText('Connecting to real-time services...')).toBeInTheDocument();
      
      // Simulate timeout
      await act(async () => {
        jest.advanceTimersByTime(3000); // 3 second timeout
        mockInitializationCoordinator.phase = 'error';
        mockInitializationCoordinator.progress = 45;
        mockInitializationCoordinator.error = 'WebSocket connection timeout';
        (useInitializationCoordinator as jest.Mock).mockReturnValue(mockInitializationCoordinator);
        rerender(
          <WebSocketProvider>
            <InitializationFlowTestComponent />
          </WebSocketProvider>
        );
      });
      
      expect(screen.getByText('Connection issue detected')).toBeInTheDocument();
    });
    
    it('handles store loading failure', async () => {
      const { rerender } = render(
        <WebSocketProvider>
          <InitializationFlowTestComponent />
        </WebSocketProvider>
      );
      
      // Progress to store phase
      await act(async () => {
        mockInitializationCoordinator.phase = 'store';
        mockInitializationCoordinator.progress = 75;
        (useInitializationCoordinator as jest.Mock).mockReturnValue(mockInitializationCoordinator);
        rerender(
          <WebSocketProvider>
            <InitializationFlowTestComponent />
          </WebSocketProvider>
        );
      });
      
      expect(screen.getByText('Loading your workspace...')).toBeInTheDocument();
      
      // Simulate store loading failure
      await act(async () => {
        mockInitializationCoordinator.phase = 'error';
        mockInitializationCoordinator.progress = 75;
        mockInitializationCoordinator.error = 'Failed to load application state';
        (useInitializationCoordinator as jest.Mock).mockReturnValue(mockInitializationCoordinator);
        rerender(
          <WebSocketProvider>
            <InitializationFlowTestComponent />
          </WebSocketProvider>
        );
      });
      
      expect(screen.getByText('Connection issue detected')).toBeInTheDocument();
    });
  });
  
  describe('WebSocket Integration During Initialization', () => {
        setupAntiHang();
      jest.setTimeout(10000);
    it('shows WebSocket connection status during websocket phase', async () => {
      const { rerender } = render(
        <WebSocketProvider>
          <InitializationFlowTestComponent />
        </WebSocketProvider>
      );
      
      // Move to WebSocket phase
      await act(async () => {
        mockInitializationCoordinator.phase = 'websocket';
        mockInitializationCoordinator.progress = 50;
        (useInitializationCoordinator as jest.Mock).mockReturnValue(mockInitializationCoordinator);
        rerender(
          <WebSocketProvider>
            <InitializationFlowTestComponent />
          </WebSocketProvider>
        );
      });
      
      // Test different connection states
      await act(async () => {
        if (mockWebSocketService.onStatusChange) {
          mockWebSocketService.onStatusChange('CLOSED' as any);
        }
        jest.advanceTimersByTime(100);
      });
      
      // Status should be visible during websocket phase
      expect(screen.getByText('Status: CLOSED')).toBeInTheDocument();
      
      await act(async () => {
        if (mockWebSocketService.onStatusChange) {
          mockWebSocketService.onStatusChange('CONNECTING' as any);
        }
        jest.advanceTimersByTime(100);
      });
      
      expect(screen.getByText('Status: CONNECTING')).toBeInTheDocument();
      
      await act(async () => {
        if (mockWebSocketService.onStatusChange) {
          mockWebSocketService.onStatusChange('OPEN' as any);
        }
        jest.advanceTimersByTime(100);
      });
      
      expect(screen.getByText('Status: OPEN')).toBeInTheDocument();
    });
    
    it('handles WebSocket reconnection during initialization', async () => {
      const { rerender } = render(
        <WebSocketProvider>
          <InitializationFlowTestComponent />
        </WebSocketProvider>
      );
      
      // Move to WebSocket phase
      await act(async () => {
        mockInitializationCoordinator.phase = 'websocket';
        mockInitializationCoordinator.progress = 50;
        (useInitializationCoordinator as jest.Mock).mockReturnValue(mockInitializationCoordinator);
        rerender(
          <WebSocketProvider>
            <InitializationFlowTestComponent />
          </WebSocketProvider>
        );
        
        // Initial connection attempt
        if (mockWebSocketService.onStatusChange) {
          mockWebSocketService.onStatusChange('CONNECTING' as any);
        }
      });
      
      // Simulate connection failure and retry
      await act(async () => {
        if (mockWebSocketService.onStatusChange) {
          mockWebSocketService.onStatusChange('CLOSED' as any);
        }
        jest.advanceTimersByTime(1000);
      });
      
      expect(screen.getByText('Status: CLOSED')).toBeInTheDocument();
      
      // Simulate reconnection
      await act(async () => {
        if (mockWebSocketService.onStatusChange) {
          mockWebSocketService.onStatusChange('CONNECTING' as any);
        }
        jest.advanceTimersByTime(500);
      });
      
      expect(screen.getByText('Status: CONNECTING')).toBeInTheDocument();
      
      // Successful reconnection
      await act(async () => {
        if (mockWebSocketService.onStatusChange) {
          mockWebSocketService.onStatusChange('OPEN' as any);
        }
        mockInitializationCoordinator.progress = 66;
        (useInitializationCoordinator as jest.Mock).mockReturnValue(mockInitializationCoordinator);
        rerender(
          <WebSocketProvider>
            <InitializationFlowTestComponent />
          </WebSocketProvider>
        );
      });
      
      expect(screen.getByText('Status: OPEN')).toBeInTheDocument();
      expect(screen.getByText('66% complete')).toBeInTheDocument();
    });
  });
  
  describe('Performance and Memory Management', () => {
        setupAntiHang();
      jest.setTimeout(10000);
    it('cleans up properly when component unmounts during initialization', async () => {
      const { unmount } = render(
        <WebSocketProvider>
          <InitializationFlowTestComponent />
        </WebSocketProvider>
      );
      
      // Start initialization
      await act(async () => {
        mockInitializationCoordinator.phase = 'websocket';
        mockInitializationCoordinator.progress = 50;
        (useInitializationCoordinator as jest.Mock).mockReturnValue(mockInitializationCoordinator);
        jest.advanceTimersByTime(100);
      });
      
      // Unmount during initialization
      unmount();
      
      // Verify cleanup
      expect(mockWebSocketService.disconnect).toHaveBeenCalled();
      expect(mockInitializationCoordinator.reset).not.toHaveBeenCalled(); // Hook cleanup happens automatically
    });
    
    it('handles rapid phase changes without memory leaks', async () => {
      const { rerender } = render(
        <WebSocketProvider>
          <InitializationFlowTestComponent />
        </WebSocketProvider>
      );
      
      // Rapidly change phases
      const rapidPhases = ['auth', 'websocket', 'store', 'websocket', 'store', 'ready'];
      const rapidProgress = [10, 40, 70, 50, 80, 100];
      
      for (let i = 0; i < rapidPhases.length; i++) {
        await act(async () => {
          mockInitializationCoordinator.phase = rapidPhases[i] as any;
          mockInitializationCoordinator.progress = rapidProgress[i];
          if (rapidPhases[i] === 'ready') {
            mockInitializationCoordinator.isInitialized = true;
          }
          (useInitializationCoordinator as jest.Mock).mockReturnValue(mockInitializationCoordinator);
          rerender(
            <WebSocketProvider>
              <InitializationFlowTestComponent />
            </WebSocketProvider>
          );
          jest.advanceTimersByTime(50);
        });
      }
      
      // Should complete successfully despite rapid changes
      await waitFor(() => {
        expect(screen.getByTestId('app-ready')).toBeInTheDocument();
      });
    });
  });
});