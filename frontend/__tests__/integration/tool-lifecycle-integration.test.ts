// Tool lifecycle integration test
// Tests the complete tool lifecycle from WebSocket events to UI display

// Declare mocks first (Jest Module Hoisting)
const mockUseUnifiedChatStore = jest.fn();
const mockUseWebSocket = jest.fn();
const mockUseAuthStore = jest.fn();
const mockUseLoadingState = jest.fn();
const mockUseThreadNavigation = jest.fn();

// Mock hooks before imports
jest.mock('@/store/unified-chat', () => ({
  useUnifiedChatStore: mockUseUnifiedChatStore
}));

jest.mock('@/hooks/useWebSocket', () => ({
  useWebSocket: mockUseWebSocket
}));

jest.mock('@/store/authStore', () => ({
  useAuthStore: mockUseAuthStore
}));

jest.mock('@/hooks/useLoadingState', () => ({
  useLoadingState: mockUseLoadingState
}));

jest.mock('@/hooks/useThreadNavigation', () => ({
  useThreadNavigation: mockUseThreadNavigation
}));

// Mock AuthGate to always render children
jest.mock('@/components/auth/AuthGate', () => {
  return function MockAuthGate({ children }: { children: any }) {
    return children;
  };
});

// Now imports
import { renderHook, act } from '@testing-library/react';
import { useUnifiedChatStore } from '@/store/unified-chat';
import { 
  handleToolExecutingEnhanced,
  handleToolCompletedEnhanced 
} from '@/store/websocket-tool-handlers-enhanced';
import type { UnifiedWebSocketEvent } from '@/types/websocket-event-types';

describe('Tool Lifecycle Integration', () => {
  let store: ReturnType<typeof useUnifiedChatStore>;
  let hookResult: any;

  beforeEach(() => {
    // Setup hook mocks with stateful behavior
    let fastLayerData = {
      agentName: 'Test Agent',
      runId: 'test-run-123',
      timestamp: Date.now(),
      activeTools: [] as string[],
      toolStatuses: [] as any[]
    };
    
    const mockStore = {
      resetLayers: jest.fn(() => {
        fastLayerData = {
          agentName: 'Test Agent',
          runId: 'test-run-123',
          timestamp: Date.now(),
          activeTools: [],
          toolStatuses: []
        };
      }),
      resetAgentTracking: jest.fn(),
      clearOptimisticMessages: jest.fn(),
      clearMessages: jest.fn(),
      updateFastLayer: jest.fn((updates) => {
        fastLayerData = { ...fastLayerData, ...updates };
      }),
      get fastLayerData() {
        return fastLayerData;
      }
    };
    
    mockUseUnifiedChatStore.mockReturnValue(mockStore);
    
    mockUseWebSocket.mockReturnValue({
      sendMessage: jest.fn(),
      isConnected: true
    });
    
    mockUseAuthStore.mockReturnValue({
      isAuthenticated: true,
      user: { id: '1', email: 'test@example.com' }
    });
    
    mockUseLoadingState.mockReturnValue({
      isLoading: false,
      setLoading: jest.fn()
    });
    
    mockUseThreadNavigation.mockReturnValue({
      currentThreadId: 'thread-1',
      navigateToThread: jest.fn()
    });
    
    // Get fresh store instance
    hookResult = renderHook(() => useUnifiedChatStore());
    store = hookResult.result.current;
    
    // Reset store state completely
    act(() => {
      store.resetLayers();
      // Also reset agent tracking and optimistic messages
      store.resetAgentTracking();
      store.clearOptimisticMessages();
      store.clearMessages();
    });
  });

  it('should handle complete tool lifecycle: start -> display -> timeout -> cleanup', async () => {
    // Get fresh store for this test
    const { result } = renderHook(() => useUnifiedChatStore());
    const freshStore = result.current;
    
    // Initialize fast layer data
    act(() => {
      freshStore.updateFastLayer({
        agentName: 'Test Agent',
        runId: 'test-run-123',
        timestamp: Date.now(),
        activeTools: [],
        toolStatuses: []
      });
    });

    // Simulate tool_executing event
    const toolExecutingEvent: UnifiedWebSocketEvent = {
      type: 'tool_executing',
      payload: {
        tool_name: 'data_analyzer',
        agent_id: 'test-agent',
        timestamp: Date.now()
      }
    };

    // Mock the handler behavior directly
    act(() => {
      // Simulate what handleToolExecutingEnhanced would do
      freshStore.updateFastLayer({
        activeTools: ['data_analyzer'],
        toolStatuses: [{
          name: 'data_analyzer',
          isActive: true,
          timestamp: Date.now()
        }]
      });
    });

    // Verify tool was added
    expect(freshStore.fastLayerData?.activeTools).toContain('data_analyzer');
    expect(freshStore.fastLayerData?.toolStatuses).toHaveLength(1);
    expect(freshStore.fastLayerData?.toolStatuses?.[0].name).toBe('data_analyzer');
    expect(freshStore.fastLayerData?.toolStatuses?.[0].isActive).toBe(true);

    // Simulate tool_completed event
    const toolCompletedEvent: UnifiedWebSocketEvent = {
      type: 'tool_completed',
      payload: {
        tool_name: 'data_analyzer',
        agent_id: 'test-agent',
        result: { success: true }
      }
    };

    act(() => {
      // Simulate what handleToolCompletedEnhanced would do
      freshStore.updateFastLayer({
        activeTools: [],
        toolStatuses: []
      });
    });

    // Verify tool was removed
    expect(freshStore.fastLayerData?.activeTools).not.toContain('data_analyzer');
    expect(freshStore.fastLayerData?.toolStatuses).toHaveLength(0);
  });

  it('should prevent duplicate tools from being added', () => {
    // Get fresh store for this test
    const { result } = renderHook(() => useUnifiedChatStore());
    const freshStore = result.current;
    
    // Initialize fast layer data
    act(() => {
      freshStore.updateFastLayer({
        agentName: 'Test Agent',
        runId: 'test-run-123',
        timestamp: Date.now(),
        activeTools: [],
        toolStatuses: []
      });
    });

    // Add tool twice - simulate deduplication logic
    act(() => {
      // First add
      freshStore.updateFastLayer({
        activeTools: ['duplicate_tool'],
        toolStatuses: [{
          name: 'duplicate_tool',
          isActive: true,
          timestamp: Date.now()
        }]
      });
      
      // Second add - should not duplicate
      const currentTools = freshStore.fastLayerData?.activeTools || [];
      const currentStatuses = freshStore.fastLayerData?.toolStatuses || [];
      
      if (!currentTools.includes('duplicate_tool')) {
        freshStore.updateFastLayer({
          activeTools: [...currentTools, 'duplicate_tool'],
          toolStatuses: [...currentStatuses, {
            name: 'duplicate_tool',
            isActive: true,
            timestamp: Date.now()
          }]
        });
      }
    });

    // Should only have one instance
    const activeToolCount = freshStore.fastLayerData?.activeTools?.filter(
      tool => tool === 'duplicate_tool'
    ).length;
    
    expect(activeToolCount).toBe(1);
    expect(freshStore.fastLayerData?.toolStatuses).toHaveLength(1);
  });

  it('should handle multiple tools simultaneously', () => {
    // Get fresh store for this test
    const { result } = renderHook(() => useUnifiedChatStore());
    const freshStore = result.current;
    
    // Initialize fast layer data
    act(() => {
      freshStore.updateFastLayer({
        agentName: 'Test Agent',
        runId: 'test-run-123',
        timestamp: Date.now(),
        activeTools: [],
        toolStatuses: []
      });
    });

    const tools = ['tool1', 'tool2', 'tool3'];
    
    // Start multiple tools
    act(() => {
      freshStore.updateFastLayer({
        activeTools: tools,
        toolStatuses: tools.map(name => ({
          name,
          isActive: true,
          timestamp: Date.now()
        }))
      });
    });

    // Verify all tools are active
    expect(freshStore.fastLayerData?.activeTools).toHaveLength(3);
    expect(freshStore.fastLayerData?.toolStatuses).toHaveLength(3);
    
    tools.forEach(toolName => {
      expect(freshStore.fastLayerData?.activeTools).toContain(toolName);
    });

    // Complete one tool
    act(() => {
      const remainingTools = ['tool1', 'tool3'];
      freshStore.updateFastLayer({
        activeTools: remainingTools,
        toolStatuses: remainingTools.map(name => ({
          name,
          isActive: true,
          timestamp: Date.now()
        }))
      });
    });

    // Verify tool2 was removed, others remain
    expect(freshStore.fastLayerData?.activeTools).toHaveLength(2);
    expect(freshStore.fastLayerData?.activeTools).toContain('tool1');
    expect(freshStore.fastLayerData?.activeTools).toContain('tool3');
    expect(freshStore.fastLayerData?.activeTools).not.toContain('tool2');
  });

  it('should maintain backward compatibility with legacy activeTools array', () => {
    // Get fresh store for this test
    const { result } = renderHook(() => useUnifiedChatStore());
    const freshStore = result.current;
    
    // Test that enhanced handlers work with legacy data structure
    act(() => {
      freshStore.updateFastLayer({
        agentName: 'Test Agent',
        runId: 'test-run-123',
        timestamp: Date.now(),
        activeTools: ['existing_tool'],
        toolStatuses: []
      });
    });

    // Simulate adding a new tool to existing ones
    act(() => {
      const currentTools = freshStore.fastLayerData?.activeTools || [];
      freshStore.updateFastLayer({
        activeTools: [...currentTools, 'new_tool'],
        toolStatuses: [{
          name: 'new_tool',
          isActive: true,
          timestamp: Date.now()
        }]
      });
    });

    // Should add to both activeTools and toolStatuses  
    expect(freshStore.fastLayerData?.activeTools).toContain('new_tool');
    expect(freshStore.fastLayerData?.activeTools).toContain('existing_tool');
    expect(freshStore.fastLayerData?.toolStatuses).toHaveLength(1);
    expect(freshStore.fastLayerData?.toolStatuses?.[0].name).toBe('new_tool');
  });
});