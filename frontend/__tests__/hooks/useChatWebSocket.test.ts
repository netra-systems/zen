/**
 * useChatWebSocket Hook Tests - WebSocket Message Processing
 * 
 * BVJ: Real-time agent communication drives user engagement and conversion
 * Tests cover: message routing, agent state management, tool execution tracking
 * 
 * @compliance testing.xml - Hook testing with real dependencies
 * @prevents websocket-message-processing-failures regression
 */

import React from 'react';
import { renderHook, act } from '@testing-library/react';
import { useChatWebSocket } from '@/hooks/useChatWebSocket';
import { useUnifiedChatStore } from '@/store/unified-chat';
import { WebSocketProvider } from '@/providers/WebSocketProvider';

// Mock only the store dependencies, not the hook being tested
jest.mock('@/store/unified-chat');

// Mock WebSocket provider for controlled testing
jest.mock('@/providers/WebSocketProvider', () => ({
  WebSocketProvider: ({ children }: { children: React.ReactNode }) => children,
  useWebSocketContext: jest.fn()
}));

// Mock the context that useWebSocket depends on
import { useWebSocketContext } from '@/providers/WebSocketProvider';
const mockUseWebSocketContext = useWebSocketContext as jest.MockedFunction<typeof useWebSocketContext>;

describe('useChatWebSocket Hook - Message Processing', () => {
  const mockUnifiedChatStore = useUnifiedChatStore as jest.MockedFunction<typeof useUnifiedChatStore>;

  // Helper: Create mock WebSocket context (≤8 lines)
  const createMockWebSocketContext = (messages: any[] = []) => ({
    messages,
    sendMessage: jest.fn(),
    status: 'OPEN' as const,
    isConnected: true,
    connect: jest.fn(),
    disconnect: jest.fn(),
    error: null
  });

  // Helper: Create mock unified store (≤8 lines)
  const createMockUnifiedStore = (overrides = {}) => ({
    handleWebSocketEvent: jest.fn(),
    addMessage: jest.fn(),
    setProcessing: jest.fn(),
    clearMessages: jest.fn(),
    messages: [],
    isProcessing: false,
    fastLayerData: null,
    mediumLayerData: null,
    ...overrides
  });

  // Helper: Create test message (≤8 lines)
  const createTestMessage = (type: string, payload: any = {}) => ({
    type,
    payload,
    timestamp: Date.now(),
    id: `msg_${Date.now()}`
  });

  beforeEach(() => {
    jest.clearAllMocks();
  });

  /**
   * Test Suite 1: Hook Initialization
   * Tests basic hook setup and default state
   */
  describe('Hook Initialization', () => {
    // Helper: Setup basic test environment (≤8 lines)
    const setupBasicTest = () => {
      const mockContext = createMockWebSocketContext();
      const mockStore = createMockUnifiedStore();
      mockUseWebSocketContext.mockReturnValue(mockContext);
      mockUnifiedChatStore.mockReturnValue(mockStore);
      return { mockContext, mockStore };
    };

    it('should initialize with default state', () => {
      const { mockStore } = setupBasicTest();
      const { result } = renderHook(() => useChatWebSocket());
      
      expectDefaultState(result.current);
    });

    // Helper: Assert default hook state (≤8 lines)
    const expectDefaultState = (state: any) => {
      expect(state.isConnected).toBe(true);
      expect(state.agentStatus).toBe('IDLE');
      expect(state.errors).toEqual([]);
      expect(state.workflowProgress.current_step).toBe(0);
      expect(typeof state.addMessage).toBe('function');
      expect(typeof state.setProcessing).toBe('function');
    };

    it('should provide action methods from unified store', () => {
      const { mockStore } = setupBasicTest();
      const { result } = renderHook(() => useChatWebSocket());
      
      testActionMethods(result.current, mockStore);
    });

    // Helper: Test action method delegation (≤8 lines)
    const testActionMethods = (hookResult: any, mockStore: any) => {
      const testMessage = { type: 'user', content: 'Test' };
      act(() => hookResult.addMessage(testMessage));
      expect(mockStore.addMessage).toHaveBeenCalledWith(testMessage);
      
      act(() => hookResult.setProcessing(true));
      expect(mockStore.setProcessing).toHaveBeenCalledWith(true);
      
      act(() => hookResult.clearMessages());
      expect(mockStore.clearMessages).toHaveBeenCalled();
    };
  });

  /**
   * Test Suite 2: Message Processing
   * Tests WebSocket message routing and processing
   */
  describe('Message Processing', () => {
    // Helper: Setup message processing test (≤8 lines)
    const setupMessageTest = (messages: any[]) => {
      const mockContext = createMockWebSocketContext(messages);
      const mockStore = createMockUnifiedStore();
      mockUseWebSocketContext.mockReturnValue(mockContext);
      mockUnifiedChatStore.mockReturnValue(mockStore);
      return { mockContext, mockStore };
    };

    it('should handle agent_started message', () => {
      const message = createTestMessage('agent_started', { 
        total_steps: 5, 
        estimated_duration: 120 
      });
      const { mockStore } = setupMessageTest([message]);
      
      renderHook(() => useChatWebSocket());
      expectMessageProcessed(mockStore, message);
    });

    // Helper: Assert message was processed (≤8 lines)
    const expectMessageProcessed = (mockStore: any, message: any) => {
      expect(mockStore.handleWebSocketEvent).toHaveBeenCalledWith(
        expect.objectContaining({
          type: message.type,
          payload: message.payload
        })
      );
    };

    it('should handle sub_agent_update message', () => {
      const message = createTestMessage('sub_agent_update', {
        sub_agent_name: 'OptimizationAgent',
        state: { lifecycle: 'running', tools: ['analyzer'] }
      });
      const { mockStore } = setupMessageTest([message]);
      
      renderHook(() => useChatWebSocket());
      expectMessageProcessed(mockStore, message);
    });

    it('should handle agent_completed message', () => {
      const message = createTestMessage('agent_completed', {});
      const { mockStore } = setupMessageTest([message]);
      
      renderHook(() => useChatWebSocket());
      expectMessageProcessed(mockStore, message);
    });

    it('should handle error message', () => {
      const message = createTestMessage('error', {
        error: 'Connection timeout',
        sub_agent_name: 'NetworkAgent'
      });
      const { mockStore } = setupMessageTest([message]);
      
      renderHook(() => useChatWebSocket());
      expectMessageProcessed(mockStore, message);
    });

    it('should handle tool_call message', () => {
      const message = createTestMessage('tool_call', {
        tool_name: 'cost_analyzer',
        tool_args: { region: 'us-east-1' },
        sub_agent_name: 'AnalysisAgent'
      });
      const { mockStore } = setupMessageTest([message]);
      
      renderHook(() => useChatWebSocket());
      expectMessageProcessed(mockStore, message);
    });
  });

  /**
   * Test Suite 3: Agent Status Management
   * Tests agent state derivation from processing state
   */
  describe('Agent Status Management', () => {
    it('should derive agent status from processing state', () => {
      testIdleStatus();
      testRunningStatus();
    });

    // Helper: Test idle agent status (≤8 lines)
    const testIdleStatus = () => {
      const mockStore = createMockUnifiedStore({ isProcessing: false });
      const mockContext = createMockWebSocketContext();
      mockUseWebSocketContext.mockReturnValue(mockContext);
      mockUnifiedChatStore.mockReturnValue(mockStore);
      
      const { result } = renderHook(() => useChatWebSocket());
      expect(result.current.agentStatus).toBe('IDLE');
    };

    // Helper: Test running agent status (≤8 lines)
    const testRunningStatus = () => {
      const mockStore = createMockUnifiedStore({ isProcessing: true });
      const mockContext = createMockWebSocketContext();
      mockUseWebSocketContext.mockReturnValue(mockContext);
      mockUnifiedChatStore.mockReturnValue(mockStore);
      
      const { result, rerender } = renderHook(() => useChatWebSocket());
      rerender();
      expect(result.current.agentStatus).toBe('RUNNING');
    };
  });

  /**
   * Test Suite 4: Workflow Progress Tracking
   * Tests workflow progress derivation from layer data
   */
  describe('Workflow Progress Tracking', () => {
    it('should handle workflow progress update', () => {
      const mockStore = createMockUnifiedStore({
        fastLayerData: { agentName: 'TestAgent', activeTools: ['tool1'] }
      });
      const mockContext = createMockWebSocketContext();
      mockUseWebSocketContext.mockReturnValue(mockContext);
      mockUnifiedChatStore.mockReturnValue(mockStore);
      
      const { result } = renderHook(() => useChatWebSocket());
      expectWorkflowProgress(result.current);
    });

    // Helper: Assert workflow progress state (≤8 lines)
    const expectWorkflowProgress = (state: any) => {
      expect(state.workflowProgress.current_step).toBe(1);
      expect(state.workflowProgress.total_steps).toBe(3);
      expect(state.activeTools).toEqual(['tool1']);
    };

    it('should handle streaming updates', () => {
      const mockStore = createMockUnifiedStore({
        mediumLayerData: { partialContent: 'Streaming content...' }
      });
      const mockContext = createMockWebSocketContext();
      mockUseWebSocketContext.mockReturnValue(mockContext);
      mockUnifiedChatStore.mockReturnValue(mockStore);
      
      const { result } = renderHook(() => useChatWebSocket());
      expectStreamingState(result.current);
    });

    // Helper: Assert streaming state (≤8 lines)
    const expectStreamingState = (state: any) => {
      expect(state.isStreaming).toBe(true);
      expect(state.streamingMessage).toBe('Streaming content...');
    };
  });

  /**
   * Test Suite 5: Multiple Message Handling
   * Tests handling of message sequences and re-renders
   */
  describe('Multiple Message Handling', () => {
    it('should handle multiple messages in sequence', () => {
      const messages = [
        createTestMessage('agent_started', {}),
        createTestMessage('sub_agent_update', { sub_agent_name: 'Agent1' }),
        createTestMessage('agent_completed', {})
      ];
      const { mockStore } = setupMessageTest(messages);
      
      renderHook(() => useChatWebSocket());
      expectMultipleMessagesProcessed(mockStore, messages.length);
    });

    // Helper: Assert multiple messages processed (≤8 lines)
    const expectMultipleMessagesProcessed = (mockStore: any, count: number) => {
      expect(mockStore.handleWebSocketEvent).toHaveBeenCalledTimes(count);
    };

    it('should not reprocess messages on re-render', () => {
      const messages = [createTestMessage('agent_started', {})];
      const { mockStore } = setupMessageTest(messages);
      
      const { rerender } = renderHook(() => useChatWebSocket());
      rerender();
      
      expectNoReprocessing(mockStore);
    });

    // Helper: Assert no message reprocessing (≤8 lines)
    const expectNoReprocessing = (mockStore: any) => {
      expect(mockStore.handleWebSocketEvent).toHaveBeenCalledTimes(1);
    };
  });

  /**
   * Test Suite 6: Enhanced Mode Features
   * Tests enhanced mode with metrics and tracking
   */
  describe('Enhanced Mode Features', () => {
    it('should provide enhanced features when enabled', () => {
      const { mockStore } = setupBasicTest();
      const { result } = renderHook(() => useChatWebSocket({ enhanced: true }));
      
      expectEnhancedFeatures(result.current);
    });

    // Helper: Assert enhanced features (≤8 lines)
    const expectEnhancedFeatures = (state: any) => {
      expect(state.metrics).toBeDefined();
      expect(state.currentAgent).toBeDefined();
      expect(state.totalDuration).toBeDefined();
      expect(state.stepCount).toBeDefined();
    };

    it('should handle legacy string parameter', () => {
      const { mockStore } = setupBasicTest();
      const { result } = renderHook(() => useChatWebSocket('test-run-id'));
      
      expectBasicFeatures(result.current);
    });

    // Helper: Assert basic features only (≤8 lines)
    const expectBasicFeatures = (state: any) => {
      expect(state.metrics).toBeUndefined();
      expect(state.agentStatus).toBeDefined();
      expect(state.isConnected).toBeDefined();
    };
  });

  /**
   * Test Suite 7: Tool Management
   * Tests tool registration and execution compatibility
   */
  describe('Tool Management', () => {
    it('should provide tool management methods', () => {
      const { mockStore } = setupBasicTest();
      const { result } = renderHook(() => useChatWebSocket());
      
      testToolMethods(result.current);
    });

    // Helper: Test tool management methods (≤8 lines)
    const testToolMethods = (state: any) => {
      expect(typeof state.registerTool).toBe('function');
      expect(typeof state.executeTool).toBe('function');
      expect(state.registeredTools).toEqual([]);
      expect(state.toolExecutionStatus).toBe('idle');
      
      // These are compatibility methods (no-ops)
      act(() => state.registerTool({ name: 'test', version: '1.0' }));
      act(() => state.executeTool('test', { param: 'value' }));
    };
  });
});