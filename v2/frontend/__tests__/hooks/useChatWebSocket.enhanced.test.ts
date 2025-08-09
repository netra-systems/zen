import { renderHook, act } from '@testing-library/react';
import { useChatWebSocket } from '../../hooks/useChatWebSocket';
import { useWebSocket } from '../../hooks/useWebSocket';
import { useChatStore } from '../../store/chat';
import { Message } from '../../types/chat';

jest.mock('../../hooks/useWebSocket');
jest.mock('../../store/chat');

describe('useChatWebSocket', () => {
  const mockUseWebSocket = useWebSocket as jest.MockedFunction<typeof useWebSocket>;
  const mockUseChatStore = useChatStore as jest.MockedFunction<typeof useChatStore>;
  
  const mockAddMessage = jest.fn();
  const mockSetSubAgentName = jest.fn();
  const mockSetSubAgentStatus = jest.fn();
  const mockSetProcessing = jest.fn();
  const mockGetState = jest.fn();

  beforeEach(() => {
    mockUseWebSocket.mockReturnValue({
      messages: [],
      sendMessage: jest.fn(),
      isConnected: true,
      connectionState: 'connected' as const,
      lastMessage: null,
    });

    mockUseChatStore.mockReturnValue({
      addMessage: mockAddMessage,
      setSubAgentName: mockSetSubAgentName,
      setSubAgentStatus: mockSetSubAgentStatus,
      setProcessing: mockSetProcessing,
      messages: [],
    } as any);

    (useChatStore as any).getState = mockGetState;
    mockGetState.mockReturnValue({
      subAgentName: 'TestAgent',
    });

    jest.clearAllMocks();
  });

  describe('WebSocket Message Processing', () => {
    it('should process sub_agent_update messages correctly', () => {
      const messages = [{
        type: 'sub_agent_update',
        payload: {
          sub_agent_name: 'DataAgent',
          state: {
            lifecycle: 'running',
            tools: ['analyzer', 'processor']
          }
        }
      }];

      mockUseWebSocket.mockReturnValue({
        messages,
        sendMessage: jest.fn(),
        isConnected: true,
        connectionState: 'connected',
        lastMessage: null,
      });

      renderHook(() => useChatWebSocket());

      expect(mockSetSubAgentName).toHaveBeenCalledWith('DataAgent');
      expect(mockSetSubAgentStatus).toHaveBeenCalledWith({
        status: 'running',
        tools: ['analyzer', 'processor']
      });
    });

    it('should handle agent_started messages', () => {
      const messages = [{
        type: 'agent_started',
        payload: {}
      }];

      mockUseWebSocket.mockReturnValue({
        messages,
        sendMessage: jest.fn(),
        isConnected: true,
        connectionState: 'connected',
        lastMessage: null,
      });

      renderHook(() => useChatWebSocket());

      expect(mockSetProcessing).toHaveBeenCalledWith(true);
    });

    it('should handle agent_finished messages', () => {
      const messages = [{
        type: 'agent_finished',
        payload: {}
      }];

      mockUseWebSocket.mockReturnValue({
        messages,
        sendMessage: jest.fn(),
        isConnected: true,
        connectionState: 'connected',
        lastMessage: null,
      });

      renderHook(() => useChatWebSocket());

      expect(mockSetProcessing).toHaveBeenCalledWith(false);
      expect(mockAddMessage).toHaveBeenCalledWith(
        expect.objectContaining({
          role: 'assistant',
          content: 'Task completed successfully.',
          subAgentName: 'TestAgent'
        })
      );
    });

    it('should handle agent_completed messages', () => {
      const messages = [{
        type: 'agent_completed',
        payload: {}
      }];

      mockUseWebSocket.mockReturnValue({
        messages,
        sendMessage: jest.fn(),
        isConnected: true,
        connectionState: 'connected',
        lastMessage: null,
      });

      renderHook(() => useChatWebSocket());

      expect(mockSetProcessing).toHaveBeenCalledWith(false);
      expect(mockAddMessage).toHaveBeenCalledWith(
        expect.objectContaining({
          content: 'Task completed successfully.'
        })
      );
    });

    it('should handle error messages', () => {
      const messages = [{
        type: 'error',
        payload: {
          error: 'Connection failed'
        }
      }];

      mockUseWebSocket.mockReturnValue({
        messages,
        sendMessage: jest.fn(),
        isConnected: true,
        connectionState: 'connected',
        lastMessage: null,
      });

      renderHook(() => useChatWebSocket());

      expect(mockSetProcessing).toHaveBeenCalledWith(false);
      expect(mockAddMessage).toHaveBeenCalledWith(
        expect.objectContaining({
          role: 'assistant',
          content: 'Error: Connection failed',
          subAgentName: 'System',
          error: true
        })
      );
    });

    it('should handle agent_stopped messages', () => {
      const messages = [{
        type: 'agent_stopped',
        payload: {}
      }];

      mockUseWebSocket.mockReturnValue({
        messages,
        sendMessage: jest.fn(),
        isConnected: true,
        connectionState: 'connected',
        lastMessage: null,
      });

      renderHook(() => useChatWebSocket());

      expect(mockSetProcessing).toHaveBeenCalledWith(false);
      expect(mockAddMessage).toHaveBeenCalledWith(
        expect.objectContaining({
          content: 'Processing stopped.',
          subAgentName: 'System'
        })
      );
    });

    it('should handle messages with displayed_to_user flag', () => {
      const messages = [{
        type: 'custom_message',
        payload: { data: 'test' },
        displayed_to_user: true,
        role: 'assistant',
        content: 'Custom message content',
        subAgentName: 'CustomAgent'
      }];

      mockUseWebSocket.mockReturnValue({
        messages,
        sendMessage: jest.fn(),
        isConnected: true,
        connectionState: 'connected',
        lastMessage: null,
      });

      renderHook(() => useChatWebSocket());

      expect(mockAddMessage).toHaveBeenCalledWith(
        expect.objectContaining({
          role: 'assistant',
          content: 'Custom message content',
          subAgentName: 'CustomAgent',
          displayed_to_user: true,
          metadata: { data: 'test' }
        })
      );
    });

    it('should skip message_received acknowledgments', () => {
      const messages = [{
        type: 'message_received',
        payload: {}
      }];

      mockUseWebSocket.mockReturnValue({
        messages,
        sendMessage: jest.fn(),
        isConnected: true,
        connectionState: 'connected',
        lastMessage: null,
      });

      renderHook(() => useChatWebSocket());

      expect(mockAddMessage).not.toHaveBeenCalled();
    });
  });

  describe('Message Processing Optimization', () => {
    it('should only process new messages and avoid reprocessing', () => {
      const initialMessages = [{
        type: 'agent_started',
        payload: {}
      }];

      const { rerender } = renderHook(() => useChatWebSocket());

      mockUseWebSocket.mockReturnValue({
        messages: initialMessages,
        sendMessage: jest.fn(),
        isConnected: true,
        connectionState: 'connected',
        lastMessage: null,
      });

      rerender();

      expect(mockSetProcessing).toHaveBeenCalledWith(true);
      expect(mockSetProcessing).toHaveBeenCalledTimes(1);

      // Add new message
      const updatedMessages = [
        ...initialMessages,
        {
          type: 'agent_finished',
          payload: {}
        }
      ];

      mockUseWebSocket.mockReturnValue({
        messages: updatedMessages,
        sendMessage: jest.fn(),
        isConnected: true,
        connectionState: 'connected',
        lastMessage: null,
      });

      rerender();

      // Should only process the new message
      expect(mockSetProcessing).toHaveBeenCalledWith(false);
      expect(mockSetProcessing).toHaveBeenCalledTimes(2);
    });

    it('should handle rapid message updates efficiently', () => {
      const messages = Array.from({ length: 100 }, (_, i) => ({
        type: 'sub_agent_update',
        payload: {
          sub_agent_name: `Agent${i}`,
          state: { lifecycle: 'running' }
        }
      }));

      mockUseWebSocket.mockReturnValue({
        messages,
        sendMessage: jest.fn(),
        isConnected: true,
        connectionState: 'connected',
        lastMessage: null,
      });

      renderHook(() => useChatWebSocket());

      expect(mockSetSubAgentName).toHaveBeenCalledTimes(100);
      expect(mockSetSubAgentStatus).toHaveBeenCalledTimes(100);
    });

    it('should maintain message processing order', () => {
      const messages = [
        { type: 'agent_started', payload: {} },
        { type: 'sub_agent_update', payload: { sub_agent_name: 'Agent1' } },
        { type: 'sub_agent_update', payload: { sub_agent_name: 'Agent2' } },
        { type: 'agent_finished', payload: {} }
      ];

      mockUseWebSocket.mockReturnValue({
        messages,
        sendMessage: jest.fn(),
        isConnected: true,
        connectionState: 'connected',
        lastMessage: null,
      });

      renderHook(() => useChatWebSocket());

      const setProcessingCalls = mockSetProcessing.mock.calls;
      expect(setProcessingCalls[0][0]).toBe(true);  // agent_started
      expect(setProcessingCalls[1][0]).toBe(false); // agent_finished

      const setSubAgentNameCalls = mockSetSubAgentName.mock.calls;
      expect(setSubAgentNameCalls[0][0]).toBe('Agent1');
      expect(setSubAgentNameCalls[1][0]).toBe('Agent2');
    });
  });

  describe('Error Handling', () => {
    it('should handle malformed messages gracefully', () => {
      const messages = [
        { type: 'error', payload: null },
        { type: 'sub_agent_update', payload: undefined },
        { type: undefined, payload: {} }
      ];

      mockUseWebSocket.mockReturnValue({
        messages: messages as any,
        sendMessage: jest.fn(),
        isConnected: true,
        connectionState: 'connected',
        lastMessage: null,
      });

      expect(() => {
        renderHook(() => useChatWebSocket());
      }).not.toThrow();

      expect(mockAddMessage).toHaveBeenCalledWith(
        expect.objectContaining({
          content: 'Error: An error occurred'
        })
      );
    });

    it('should handle store method failures gracefully', () => {
      mockSetSubAgentName.mockImplementation(() => {
        throw new Error('Store error');
      });

      const messages = [{
        type: 'sub_agent_update',
        payload: { sub_agent_name: 'TestAgent' }
      }];

      mockUseWebSocket.mockReturnValue({
        messages,
        sendMessage: jest.fn(),
        isConnected: true,
        connectionState: 'connected',
        lastMessage: null,
      });

      expect(() => {
        renderHook(() => useChatWebSocket());
      }).not.toThrow();
    });

    it('should handle missing payload data', () => {
      const messages = [
        { type: 'sub_agent_update', payload: {} },
        { type: 'sub_agent_update', payload: { state: {} } }
      ];

      mockUseWebSocket.mockReturnValue({
        messages,
        sendMessage: jest.fn(),
        isConnected: true,
        connectionState: 'connected',
        lastMessage: null,
      });

      renderHook(() => useChatWebSocket());

      expect(mockSetSubAgentStatus).toHaveBeenCalledWith({
        status: 'idle',
        tools: []
      });
    });
  });

  describe('Message ID Generation', () => {
    it('should generate unique message IDs', () => {
      const messages = [
        { type: 'agent_finished', payload: {} },
        { type: 'agent_stopped', payload: {} },
        { type: 'error', payload: { error: 'Test error' } }
      ];

      mockUseWebSocket.mockReturnValue({
        messages,
        sendMessage: jest.fn(),
        isConnected: true,
        connectionState: 'connected',
        lastMessage: null,
      });

      renderHook(() => useChatWebSocket());

      const addMessageCalls = mockAddMessage.mock.calls;
      const messageIds = addMessageCalls.map(call => call[0].id);
      
      expect(new Set(messageIds).size).toBe(messageIds.length);
      messageIds.forEach(id => {
        expect(id).toMatch(/^msg_\d+$/);
      });
    });

    it('should include timestamps in generated messages', () => {
      const mockDate = new Date('2023-10-01T12:00:00Z');
      jest.spyOn(global, 'Date').mockImplementation(() => mockDate as any);
      jest.spyOn(mockDate, 'toISOString').mockReturnValue('2023-10-01T12:00:00.000Z');

      const messages = [{ type: 'agent_finished', payload: {} }];

      mockUseWebSocket.mockReturnValue({
        messages,
        sendMessage: jest.fn(),
        isConnected: true,
        connectionState: 'connected',
        lastMessage: null,
      });

      renderHook(() => useChatWebSocket());

      expect(mockAddMessage).toHaveBeenCalledWith(
        expect.objectContaining({
          timestamp: '2023-10-01T12:00:00.000Z'
        })
      );

      jest.restoreAllMocks();
    });
  });

  describe('Hook Lifecycle', () => {
    it('should handle unmounting gracefully', () => {
      const messages = [{ type: 'agent_started', payload: {} }];

      mockUseWebSocket.mockReturnValue({
        messages,
        sendMessage: jest.fn(),
        isConnected: true,
        connectionState: 'connected',
        lastMessage: null,
      });

      const { unmount } = renderHook(() => useChatWebSocket());
      
      expect(() => unmount()).not.toThrow();
    });

    it('should handle rapid mount/unmount cycles', () => {
      const messages = [{ type: 'agent_started', payload: {} }];

      mockUseWebSocket.mockReturnValue({
        messages,
        sendMessage: jest.fn(),
        isConnected: true,
        connectionState: 'connected',
        lastMessage: null,
      });

      for (let i = 0; i < 10; i++) {
        const { unmount } = renderHook(() => useChatWebSocket());
        unmount();
      }

      expect(mockSetProcessing).toHaveBeenCalledTimes(10);
    });
  });

  describe('Complex Message Scenarios', () => {
    it('should handle multi-step agent workflow', () => {
      const messages = [
        { type: 'agent_started', payload: {} },
        { type: 'sub_agent_update', payload: { sub_agent_name: 'TriageAgent', state: { lifecycle: 'running' } } },
        { type: 'sub_agent_update', payload: { sub_agent_name: 'DataAgent', state: { lifecycle: 'running' } } },
        { type: 'sub_agent_update', payload: { sub_agent_name: 'ReportingAgent', state: { lifecycle: 'running' } } },
        { type: 'agent_finished', payload: {} }
      ];

      mockUseWebSocket.mockReturnValue({
        messages,
        sendMessage: jest.fn(),
        isConnected: true,
        connectionState: 'connected',
        lastMessage: null,
      });

      renderHook(() => useChatWebSocket());

      expect(mockSetProcessing).toHaveBeenCalledWith(true);
      expect(mockSetSubAgentName).toHaveBeenCalledWith('TriageAgent');
      expect(mockSetSubAgentName).toHaveBeenCalledWith('DataAgent');
      expect(mockSetSubAgentName).toHaveBeenCalledWith('ReportingAgent');
      expect(mockSetProcessing).toHaveBeenCalledWith(false);
      expect(mockAddMessage).toHaveBeenCalledWith(
        expect.objectContaining({
          content: 'Task completed successfully.'
        })
      );
    });

    it('should handle error recovery scenarios', () => {
      const messages = [
        { type: 'agent_started', payload: {} },
        { type: 'sub_agent_update', payload: { sub_agent_name: 'DataAgent' } },
        { type: 'error', payload: { error: 'Network timeout' } },
        { type: 'agent_started', payload: {} },
        { type: 'agent_finished', payload: {} }
      ];

      mockUseWebSocket.mockReturnValue({
        messages,
        sendMessage: jest.fn(),
        isConnected: true,
        connectionState: 'connected',
        lastMessage: null,
      });

      renderHook(() => useChatWebSocket());

      const setProcessingCalls = mockSetProcessing.mock.calls;
      expect(setProcessingCalls).toEqual([
        [true],   // First agent_started
        [false],  // Error
        [true],   // Second agent_started
        [false]   // agent_finished
      ]);

      expect(mockAddMessage).toHaveBeenCalledWith(
        expect.objectContaining({
          content: 'Error: Network timeout',
          error: true
        })
      );
    });
  });
});