/**
 * Test suite for useChatWebSocket hook
 * This hook processes WebSocket messages and updates various states
 */

import { renderHook, act, waitFor } from '@testing-library/react';
import { useChatWebSocket } from '@/hooks/useChatWebSocket';
import { useChatStore } from '@/store/chat';
import { useUnifiedChatStore } from '@/store/unified-chat';

// Mock stores
jest.mock('@/store/chat');
jest.mock('@/store/unified-chat');

// Mock useWebSocket hook to return controllable messages
let mockMessages: any[] = [];
jest.mock('@/hooks/useWebSocket', () => ({
  useWebSocket: () => ({
    messages: mockMessages,
    sendMessage: jest.fn(),
    isConnected: true,
    connect: jest.fn(),
    disconnect: jest.fn(),
    error: null
  })
}));

describe('useChatWebSocket', () => {
  const mockChatStore = {
    addMessage: jest.fn(),
    setProcessing: jest.fn(),
    setSubAgentStatus: jest.fn(),
    setSubAgentName: jest.fn(),
    subAgentName: 'TestAgent',
  };
  
  const mockUnifiedChatStore = {
    handleWebSocketEvent: jest.fn(),
    setProcessing: jest.fn(),
    addMessage: jest.fn(),
    clearMessages: jest.fn(),
    messages: [],
    currentMessage: null,
    isProcessing: false,
    fastLayerData: null,
    mediumLayerData: null,
    slowLayerData: null,
  };

  beforeEach(() => {
    jest.clearAllMocks();
    mockMessages = [];
    
    // Setup mock returns
    (useChatStore as unknown as jest.Mock).mockReturnValue(mockChatStore);
    (useUnifiedChatStore as unknown as jest.Mock).mockReturnValue(mockUnifiedChatStore);
    
    // Mock getState for chat store
    (useChatStore as any).getState = jest.fn().mockReturnValue(mockChatStore);
  });

  it('should initialize with default state', () => {
    const { result } = renderHook(() => useChatWebSocket());
    
    expect(result.current.isConnected).toBe(true);
    expect(result.current.agentStatus).toBe('IDLE');
    expect(result.current.errors).toEqual([]);
    expect(result.current.workflowProgress.current_step).toBe(0);
    expect(typeof result.current.registerTool).toBe('function');
    expect(typeof result.current.executeTool).toBe('function');
  });

  it('should handle agent_started message', () => {
    const { rerender } = renderHook(() => useChatWebSocket());
    
    // Add a message to trigger processing
    act(() => {
      mockMessages = [{
        type: 'agent_started',
        payload: { total_steps: 5, estimated_duration: 120 }
      }];
    });
    
    // Re-render to trigger useEffect
    rerender();
    
    // The hook now delegates to unified store's handleWebSocketEvent
    expect(mockUnifiedChatStore.handleWebSocketEvent).toHaveBeenCalledWith(
      expect.objectContaining({
        type: 'agent_started',
        payload: { total_steps: 5, estimated_duration: 120 }
      })
    );
  });

  it('should handle sub_agent_update message', () => {
    const { rerender } = renderHook(() => useChatWebSocket());
    
    act(() => {
      mockMessages = [{
        type: 'sub_agent_update',
        payload: {
          sub_agent_name: 'OptimizationAgent',
          state: {
            lifecycle: 'running',
            tools: ['analyzer', 'optimizer']
          }
        }
      }];
    });
    
    rerender();
    
    // The hook now delegates to unified store's handleWebSocketEvent
    expect(mockUnifiedChatStore.handleWebSocketEvent).toHaveBeenCalledWith(
      expect.objectContaining({
        type: 'sub_agent_update',
        payload: expect.objectContaining({
          sub_agent_name: 'OptimizationAgent'
        })
      })
    );
  });

  it('should handle agent_completed message', () => {
    const { rerender } = renderHook(() => useChatWebSocket());
    
    act(() => {
      mockMessages = [{
        type: 'agent_completed',
        payload: {}
      }];
    });
    
    rerender();
    
    // The hook now delegates to unified store's handleWebSocketEvent
    expect(mockUnifiedChatStore.handleWebSocketEvent).toHaveBeenCalledWith(
      expect.objectContaining({
        type: 'agent_completed',
        payload: {}
      })
    );
  });

  it('should handle error message', () => {
    const { rerender } = renderHook(() => useChatWebSocket());
    
    act(() => {
      mockMessages = [{
        type: 'error',
        payload: {
          error: 'Connection timeout',
          sub_agent_name: 'NetworkAgent'
        }
      }];
    });
    
    rerender();
    
    // The hook now delegates to unified store's handleWebSocketEvent
    expect(mockUnifiedChatStore.handleWebSocketEvent).toHaveBeenCalledWith(
      expect.objectContaining({
        type: 'error',
        payload: expect.objectContaining({
          error: 'Connection timeout'
        })
      })
    );
  });

  it('should handle tool_call message', () => {
    const { rerender } = renderHook(() => useChatWebSocket());
    
    act(() => {
      mockMessages = [{
        type: 'tool_call',
        payload: {
          tool_name: 'cost_analyzer',
          tool_args: { region: 'us-east-1' },
          sub_agent_name: 'AnalysisAgent'
        }
      }];
    });
    
    rerender();
    
    // The hook now delegates to unified store's handleWebSocketEvent
    expect(mockUnifiedChatStore.handleWebSocketEvent).toHaveBeenCalledWith(
      expect.objectContaining({
        type: 'tool_call',
        payload: expect.objectContaining({
          tool_name: 'cost_analyzer'
        })
      })
    );
  });

  it('should register and execute tools', () => {
    const { result } = renderHook(() => useChatWebSocket());
    
    // Test tool registration (now a no-op but should not error)
    act(() => {
      result.current.registerTool({
        name: 'test_tool',
        version: '1.0'
      });
    });
    
    // Since these are now no-ops, just verify they don't throw
    expect(result.current.registeredTools).toEqual([]);
    
    // Test tool execution (now a no-op but should not error)
    act(() => {
      result.current.executeTool('test_tool', { param: 'value' });
    });
    
    // Since these are now no-ops, just verify they don't throw
    expect(result.current.toolExecutionStatus).toBe('idle');
  });

  it('should handle workflow progress update', () => {
    // Update unified store to simulate progress with fastLayerData
    mockUnifiedChatStore.fastLayerData = {
      agentName: 'TestAgent',
      activeTools: ['tool1']
    };
    
    (useUnifiedChatStore as unknown as jest.Mock).mockReturnValue(mockUnifiedChatStore);
    
    const { result } = renderHook(() => useChatWebSocket());
    
    expect(result.current.workflowProgress.current_step).toBe(1);
    expect(result.current.workflowProgress.total_steps).toBe(3);
  });

  it('should handle streaming updates', () => {
    // Update unified store to simulate streaming with mediumLayerData
    mockUnifiedChatStore.mediumLayerData = {
      partialContent: 'Streaming content...'
    };
    
    (useUnifiedChatStore as unknown as jest.Mock).mockReturnValue(mockUnifiedChatStore);
    
    const { result } = renderHook(() => useChatWebSocket());
    
    expect(result.current.isStreaming).toBe(true);
    expect(result.current.streamingMessage).toBe('Streaming content...');
  });

  it('should handle multiple messages in sequence', () => {
    const { rerender } = renderHook(() => useChatWebSocket());
    
    // Add multiple messages
    act(() => {
      mockMessages = [
        { type: 'agent_started', payload: {} },
        { type: 'sub_agent_update', payload: { sub_agent_name: 'Agent1' } },
        { type: 'agent_completed', payload: {} }
      ];
    });
    
    rerender();
    
    // All messages should be handled
    expect(mockUnifiedChatStore.handleWebSocketEvent).toHaveBeenCalledTimes(3);
  });

  it('should not reprocess messages on re-render', () => {
    const { rerender } = renderHook(() => useChatWebSocket());
    
    // Add a message
    act(() => {
      mockMessages = [{ type: 'agent_started', payload: {} }];
    });
    
    rerender();
    
    // Should be called once
    expect(mockUnifiedChatStore.handleWebSocketEvent).toHaveBeenCalledTimes(1);
    
    // Re-render without new messages
    rerender();
    
    // Should still be called only once
    expect(mockUnifiedChatStore.handleWebSocketEvent).toHaveBeenCalledTimes(1);
  });

  it('should filter error messages correctly', () => {
    // The hook now returns empty errors array by default
    (useUnifiedChatStore as unknown as jest.Mock).mockReturnValue(mockUnifiedChatStore);
    
    const { result } = renderHook(() => useChatWebSocket());
    
    // Errors are handled via connectionError in unified store, not in errors array
    expect(result.current.errors).toHaveLength(0);
  });

  it('should derive agent status from processing state', () => {
    // Test idle state
    mockUnifiedChatStore.isProcessing = false;
    (useUnifiedChatStore as unknown as jest.Mock).mockReturnValue(mockUnifiedChatStore);
    
    let { result, rerender } = renderHook(() => useChatWebSocket());
    expect(result.current.agentStatus).toBe('IDLE');
    
    // Test running state
    mockUnifiedChatStore.isProcessing = true;
    (useUnifiedChatStore as unknown as jest.Mock).mockReturnValue(mockUnifiedChatStore);
    
    rerender();
    expect(result.current.agentStatus).toBe('RUNNING');
  });

  it('should provide action methods from unified store', () => {
    const { result } = renderHook(() => useChatWebSocket());
    
    // Test addMessage
    const testMessage = { type: 'user', content: 'Test' };
    act(() => {
      result.current.addMessage(testMessage);
    });
    expect(mockUnifiedChatStore.addMessage).toHaveBeenCalledWith(testMessage);
    
    // Test setProcessing
    act(() => {
      result.current.setProcessing(true);
    });
    expect(mockUnifiedChatStore.setProcessing).toHaveBeenCalledWith(true);
    
    // Test clearMessages
    act(() => {
      result.current.clearMessages();
    });
    expect(mockUnifiedChatStore.clearMessages).toHaveBeenCalled();
  });
});