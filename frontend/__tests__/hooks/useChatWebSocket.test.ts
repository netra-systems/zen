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
    
    expect(mockChatStore.setProcessing).toHaveBeenCalledWith(true);
    expect(mockUnifiedChatStore.setProcessing).toHaveBeenCalledWith(true);
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
    
    expect(mockChatStore.setSubAgentName).toHaveBeenCalledWith('OptimizationAgent');
    expect(mockChatStore.setSubAgentStatus).toHaveBeenCalledWith({
      status: 'running',
      tools: ['analyzer', 'optimizer']
    });
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
    
    expect(mockChatStore.setProcessing).toHaveBeenCalledWith(false);
    expect(mockUnifiedChatStore.setProcessing).toHaveBeenCalledWith(false);
    expect(mockChatStore.addMessage).toHaveBeenCalledWith(
      expect.objectContaining({
        type: 'agent',
        content: 'Task completed successfully.'
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
    
    expect(mockChatStore.setProcessing).toHaveBeenCalledWith(false);
    expect(mockChatStore.addMessage).toHaveBeenCalledWith(
      expect.objectContaining({
        type: 'error',
        content: expect.stringContaining('Connection timeout')
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
    
    expect(mockChatStore.addMessage).toHaveBeenCalledWith(
      expect.objectContaining({
        type: 'tool',
        content: expect.stringContaining('cost_analyzer')
      })
    );
  });

  it('should register and execute tools', async () => {
    const { result } = renderHook(() => useChatWebSocket());
    
    // Register a tool
    act(() => {
      result.current.registerTool({ name: 'test_tool', version: '1.0' });
    });
    
    expect(result.current.registeredTools).toContainEqual({ name: 'test_tool', version: '1.0' });
    
    // Execute a tool
    let toolResult;
    await act(async () => {
      toolResult = await result.current.executeTool('test_tool', { param: 'value' });
    });
    
    expect(toolResult).toEqual({ success: true, data: { param: 'value' } });
    expect(result.current.toolResults['test_tool']).toEqual({ success: true, data: { param: 'value' } });
  });

  it('should handle workflow_progress message', () => {
    const { result, rerender } = renderHook(() => useChatWebSocket());
    
    act(() => {
      mockMessages = [{
        type: 'workflow_progress',
        payload: {
          current_step: 3,
          total_steps: 10
        }
      }];
    });
    
    rerender();
    
    expect(result.current.workflowProgress).toEqual({
      current_step: 3,
      total_steps: 10
    });
  });

  it('should handle message_chunk for streaming', () => {
    const { result, rerender } = renderHook(() => useChatWebSocket());
    
    act(() => {
      mockMessages = [{
        type: 'message_chunk',
        payload: {
          content: 'Partial response...',
          is_complete: false
        }
      }];
    });
    
    rerender();
    
    expect(result.current.streamingMessage).toBe('Partial response...');
    expect(result.current.isStreaming).toBe(true);
  });

  it('should handle validation_result message', () => {
    const { result, rerender } = renderHook(() => useChatWebSocket());
    
    act(() => {
      mockMessages = [{
        type: 'validation_result',
        payload: {
          field: 'memory_limit',
          valid: true
        }
      }];
    });
    
    rerender();
    
    expect(result.current.validationResults).toEqual({
      memory_limit: true
    });
  });

  it('should handle approval_required message', () => {
    const { result, rerender } = renderHook(() => useChatWebSocket());
    
    act(() => {
      mockMessages = [{
        type: 'approval_required',
        payload: {
          message: 'Confirm deletion of resources',
          sub_agent_name: 'ResourceManager'
        }
      }];
    });
    
    rerender();
    
    expect(result.current.pendingApproval).toEqual({
      message: 'Confirm deletion of resources',
      sub_agent_name: 'ResourceManager'
    });
    expect(mockChatStore.addMessage).toHaveBeenCalledWith(
      expect.objectContaining({
        type: 'system',
        content: 'Confirm deletion of resources'
      })
    );
  });

  it('should clear errors', () => {
    const { result, rerender } = renderHook(() => useChatWebSocket());
    
    // Add some errors first
    act(() => {
      mockMessages = [{
        type: 'sub_agent_error',
        payload: {
          sub_agent_name: 'TestAgent',
          error: { type: 'TIMEOUT', message: 'Request timeout' },
          recovery_action: 'RETRY_WITH_FALLBACK'
        }
      }];
    });
    
    rerender();
    
    expect(result.current.errors).toHaveLength(1);
    
    // Clear errors
    act(() => {
      result.current.clearErrors();
    });
    
    expect(result.current.errors).toHaveLength(0);
  });

  it('should not reprocess already processed messages', () => {
    const { rerender } = renderHook(() => useChatWebSocket());
    
    // First batch of messages
    act(() => {
      mockMessages = [{
        type: 'agent_started',
        payload: {}
      }];
    });
    
    rerender();
    
    expect(mockChatStore.setProcessing).toHaveBeenCalledTimes(1);
    
    // Add another message without clearing
    act(() => {
      mockMessages = [
        { type: 'agent_started', payload: {} },
        { type: 'agent_completed', payload: {} }
      ];
    });
    
    rerender();
    
    // Should only process the new message
    expect(mockChatStore.setProcessing).toHaveBeenCalledTimes(2); // Once for start, once for complete
  });
});