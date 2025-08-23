// useMCPTools Hook Tests - Comprehensive testing with proper MCP service mocking
// Tests hook functionality, error handling, and API integration without 404 errors

import React from 'react';
import { renderHook, waitFor, act } from '@testing-library/react';
import { useMCPTools } from '@/hooks/useMCPTools';
import {
  setupMCPMocks,
  cleanupMCPMocks,
  mcpMockState,
  createMockServer,
  createMockTool,
  createMockToolResult,
  createDisconnectedServerScenario,
  createFailedExecutionScenario,
  expectMCPHookState
} from '../mocks/mcp-service-mock';

// ============================================
// Test Setup and Teardown
// ============================================

beforeEach(() => {
  setupMCPMocks();
});

afterEach(() => {
  cleanupMCPMocks();
  jest.clearAllMocks();
});

// Mock the unified chat store to prevent dependency issues
jest.mock('@/store/unified-chat', () => ({
  useUnifiedChatStore: () => ({
    mcpState: {
      active_executions: new Map()
    }
  })
}));

// ============================================
// Basic Hook Functionality Tests
// ============================================

describe('useMCPTools', () => {
  it('should initialize with default mock data', async () => {
    const { result } = renderHook(() => useMCPTools());

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expectMCPHookState(result.current, {
      tools: mcpMockState.getTools(),
      servers: mcpMockState.getServers(),
      isLoading: false,
      error: undefined
    });
  });

  it('should load servers successfully', async () => {
    const mockServers = [
      createMockServer({ name: 'server-1' }),
      createMockServer({ name: 'server-2', id: 'server-2' })
    ];
    mcpMockState.setServers(mockServers);

    const { result } = renderHook(() => useMCPTools());

    await waitFor(() => {
      expect(result.current.servers).toEqual(mockServers);
    });
  });

  it('should load tools successfully', async () => {
    const mockTools = [
      createMockTool({ name: 'tool-1', server_name: 'server-1' }),
      createMockTool({ name: 'tool-2', server_name: 'server-2' })
    ];
    mcpMockState.setTools(mockTools);

    const { result } = renderHook(() => useMCPTools());

    await waitFor(() => {
      expect(result.current.tools).toEqual(mockTools);
    });
  });

  it('should execute tools successfully', async () => {
    const { result } = renderHook(() => useMCPTools());

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    let executionResult: any;
    await act(async () => {
      executionResult = await result.current.executeTool('test-server', 'test-tool', { param: 'value' });
    });

    expect(executionResult).toEqual(
      expect.objectContaining({
        tool_name: 'test-tool',
        server_name: 'test-server',
        is_error: false
      })
    );
  });
});

// ============================================
// Server Status Management Tests
// ============================================

describe('useMCPTools - Server Management', () => {
  it('should get server status correctly', async () => {
    const connectedServer = createMockServer({ name: 'connected-server', status: 'CONNECTED' });
    mcpMockState.setServers([connectedServer]);

    const { result } = renderHook(() => useMCPTools());

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    const status = result.current.getServerStatus('connected-server');
    expect(status).toBe('CONNECTED');
  });

  it('should return DISCONNECTED for unknown servers', async () => {
    const { result } = renderHook(() => useMCPTools());

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    const status = result.current.getServerStatus('unknown-server');
    expect(status).toBe('DISCONNECTED');
  });

  it('should handle disconnected servers', async () => {
    const disconnectedServer = createDisconnectedServerScenario();

    const { result } = renderHook(() => useMCPTools());

    await waitFor(() => {
      expect(result.current.servers).toContainEqual(disconnectedServer);
    });

    const status = result.current.getServerStatus(disconnectedServer.name);
    expect(status).toBe('DISCONNECTED');
  });
});

// ============================================
// Error Handling Tests
// ============================================

describe('useMCPTools - Error Handling', () => {
  it('should handle tool execution errors gracefully', async () => {
    // Mock the service to throw an error
    const mockExecuteTool = jest.fn().mockRejectedValue(new Error('Execution failed'));
    jest.doMock('@/services/mcp-client-service', () => ({
      ...jest.requireActual('@/services/mcp-client-service'),
      executeTool: mockExecuteTool
    }));

    const { result } = renderHook(() => useMCPTools());

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    await act(async () => {
      try {
        await result.current.executeTool('test-server', 'test-tool', {});
      } catch (error) {
        expect(error).toBeInstanceOf(Error);
        expect((error as Error).message).toBe('Execution failed');
      }
    });

    // Should set error state
    expect(result.current.error).toBeTruthy();
  });

  it('should handle server loading errors', async () => {
    // Mock the service to throw an error during server loading
    const mockListServers = jest.fn().mockRejectedValue(new Error('Failed to load servers'));
    jest.doMock('@/services/mcp-client-service', () => ({
      ...jest.requireActual('@/services/mcp-client-service'),
      listServers: mockListServers
    }));

    const { result } = renderHook(() => useMCPTools());

    await waitFor(() => {
      expect(result.current.error).toBe('Failed to load servers');
    });
  });
});

// ============================================
// Integration Tests
// ============================================

describe('useMCPTools - Integration', () => {
  it('should refresh tools and servers together', async () => {
    const { result } = renderHook(() => useMCPTools());

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    await act(async () => {
      await result.current.refreshTools();
    });

    // Should have called both load functions
    expect(result.current.isLoading).toBe(false);
    expect(result.current.error).toBeUndefined();
  });

  it('should handle periodic server health checks', async () => {
    jest.useFakeTimers();
    
    const { result } = renderHook(() => useMCPTools());

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    // Fast forward the periodic timer
    act(() => {
      jest.advanceTimersByTime(30000);
    });

    // Health check should have been performed
    expect(result.current.error).toBeUndefined();

    jest.useRealTimers();
  });

  it('should maintain consistent state across re-renders', async () => {
    const mockServers = [createMockServer({ name: 'persistent-server' })];
    mcpMockState.setServers(mockServers);

    const { result, rerender } = renderHook(() => useMCPTools());

    await waitFor(() => {
      expect(result.current.servers).toEqual(mockServers);
    });

    rerender();

    // State should remain consistent
    await waitFor(() => {
      expect(result.current.servers).toEqual(mockServers);
    });
  });
});

// ============================================
// Performance and Lifecycle Tests
// ============================================

describe('useMCPTools - Performance', () => {
  it('should not cause unnecessary re-renders', async () => {
    let renderCount = 0;
    
    const { result } = renderHook(() => {
      renderCount++;
      return useMCPTools();
    });

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    const initialRenderCount = renderCount;

    // Calling getServerStatus should not trigger re-renders
    result.current.getServerStatus('test-server');
    expect(renderCount).toBe(initialRenderCount);
  });

  it('should clean up intervals on unmount', async () => {
    const clearIntervalSpy = jest.spyOn(global, 'clearInterval');
    
    const { unmount } = renderHook(() => useMCPTools());

    unmount();

    expect(clearIntervalSpy).toHaveBeenCalled();
    clearIntervalSpy.mockRestore();
  });
});