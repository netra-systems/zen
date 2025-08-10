import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import { ChatInterface } from '@/components/ChatInterface';
import { useWebSocket } from '@/hooks/useWebSocket';
import { useChatStore } from '@/store/chat';
import { useAuthStore } from '@/store/authStore';

// Mock all dependencies
jest.mock('@/hooks/useWebSocket');
jest.mock('@/store/chat');
jest.mock('@/store/authStore');
jest.mock('@/components/chat/MessageList', () => ({
  MessageList: () => <div data-testid="message-list">Message List</div>,
}));
jest.mock('@/components/chat/MessageInput', () => ({
  MessageInput: () => <div data-testid="message-input">Message Input</div>,
}));
jest.mock('@/components/chat/ExamplePrompts', () => ({
  ExamplePrompts: () => <div data-testid="example-prompts">Example Prompts</div>,
}));

describe('ChatInterface', () => {
  const mockWebSocket = {
    isConnected: true,
    sendMessage: jest.fn(),
    lastMessage: null,
  };

  const mockChatStore = {
    messages: [],
    isProcessing: false,
    currentSubAgent: null,
    addMessage: jest.fn(),
    updateMessage: jest.fn(),
    setProcessing: jest.fn(),
    setSubAgent: jest.fn(),
    clearSubAgent: jest.fn(),
  };

  const mockAuth = {
    user: { id: 'user-123', email: 'test@example.com' },
    isAuthenticated: true,
  };

  beforeEach(() => {
    jest.clearAllMocks();
    (useWebSocket as jest.Mock).mockReturnValue(mockWebSocket);
    (useChatStore as jest.Mock).mockReturnValue(mockChatStore);
    (useAuthStore as jest.Mock).mockReturnValue(mockAuth);
  });

  it('should render all chat components', () => {
    render(<ChatInterface />);

    expect(screen.getByTestId('message-list')).toBeInTheDocument();
    expect(screen.getByTestId('message-input')).toBeInTheDocument();
  });

  it('should show example prompts when no messages', () => {
    render(<ChatInterface />);

    expect(screen.getByTestId('example-prompts')).toBeInTheDocument();
  });

  it('should hide example prompts when messages exist', () => {
    (useChatStore as jest.Mock).mockReturnValue({
      ...mockChatStore,
      messages: [
        { id: '1', role: 'user', content: 'Hello', displayed_to_user: true }
      ],
    });

    render(<ChatInterface />);

    expect(screen.queryByTestId('example-prompts')).not.toBeInTheDocument();
  });

  it('should handle incoming WebSocket messages', async () => {
    const { rerender } = render(<ChatInterface />);

    // Simulate incoming agent_started message
    const agentStartedMessage = {
      type: 'agent_started',
      payload: { run_id: 'run-123' },
    };

    (useWebSocket as jest.Mock).mockReturnValue({
      ...mockWebSocket,
      lastMessage: agentStartedMessage,
    });

    rerender(<ChatInterface />);

    await waitFor(() => {
      expect(mockChatStore.setProcessing).toHaveBeenCalledWith(true);
    });
  });

  it('should handle sub-agent updates', async () => {
    const { rerender } = render(<ChatInterface />);

    const subAgentUpdate = {
      type: 'sub_agent_update',
      payload: {
        sub_agent_name: 'DataSubAgent',
        state: {
          messages: ['Analyzing data...'],
          lifecycle: 'RUNNING',
        },
      },
    };

    (useWebSocket as jest.Mock).mockReturnValue({
      ...mockWebSocket,
      lastMessage: subAgentUpdate,
    });

    rerender(<ChatInterface />);

    await waitFor(() => {
      expect(mockChatStore.setSubAgent).toHaveBeenCalledWith(
        'DataSubAgent',
        'RUNNING'
      );
    });
  });

  it('should handle agent completion', async () => {
    const { rerender } = render(<ChatInterface />);

    const agentCompleted = {
      type: 'agent_completed',
      payload: {
        run_id: 'run-123',
        result: {
          final_report: 'Analysis complete. Here are the results...',
        },
      },
    };

    (useWebSocket as jest.Mock).mockReturnValue({
      ...mockWebSocket,
      lastMessage: agentCompleted,
    });

    rerender(<ChatInterface />);

    await waitFor(() => {
      expect(mockChatStore.addMessage).toHaveBeenCalledWith(
        expect.objectContaining({
          role: 'assistant',
          content: 'Analysis complete. Here are the results...',
        })
      );
      expect(mockChatStore.setProcessing).toHaveBeenCalledWith(false);
      expect(mockChatStore.clearSubAgent).toHaveBeenCalled();
    });
  });

  it('should handle errors gracefully', async () => {
    const consoleSpy = jest.spyOn(console, 'error').mockImplementation();
    const { rerender } = render(<ChatInterface />);

    const errorMessage = {
      type: 'error',
      payload: {
        message: 'Something went wrong',
      },
    };

    (useWebSocket as jest.Mock).mockReturnValue({
      ...mockWebSocket,
      lastMessage: errorMessage,
    });

    rerender(<ChatInterface />);

    await waitFor(() => {
      expect(mockChatStore.addMessage).toHaveBeenCalledWith(
        expect.objectContaining({
          role: 'system',
          content: expect.stringContaining('Something went wrong'),
          error: true,
        })
      );
      expect(mockChatStore.setProcessing).toHaveBeenCalledWith(false);
    });

    consoleSpy.mockRestore();
  });

  it('should show connection status', () => {
    (useWebSocket as jest.Mock).mockReturnValue({
      ...mockWebSocket,
      isConnected: false,
    });

    render(<ChatInterface />);

    expect(screen.getByText(/Disconnected/i)).toBeInTheDocument();
  });

  it('should handle message streaming', async () => {
    const { rerender } = render(<ChatInterface />);

    // First, add a message placeholder
    const messageId = 'msg-streaming';
    (useChatStore as jest.Mock).mockReturnValue({
      ...mockChatStore,
      messages: [
        { id: messageId, role: 'assistant', content: '', displayed_to_user: true }
      ],
    });

    rerender(<ChatInterface />);

    // Simulate streaming update
    const streamingMessage = {
      type: 'message_chunk',
      payload: {
        message_id: messageId,
        content: 'Streaming content...',
      },
    };

    (useWebSocket as jest.Mock).mockReturnValue({
      ...mockWebSocket,
      lastMessage: streamingMessage,
    });

    rerender(<ChatInterface />);

    await waitFor(() => {
      expect(mockChatStore.updateMessage).toHaveBeenCalledWith(
        messageId,
        { content: 'Streaming content...' }
      );
    });
  });
});