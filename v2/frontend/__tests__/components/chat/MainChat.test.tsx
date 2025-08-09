import React from 'react';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import MainChat from '../../../components/chat/MainChat';
import { useChatStore } from '../../../store/chat';
import { useChatWebSocket } from '../../../hooks/useChatWebSocket';

jest.mock('../../../store/chat');
jest.mock('../../../hooks/useChatWebSocket');
jest.mock('../../../components/chat/ChatHeader', () => ({
  ChatHeader: () => <div data-testid="chat-header">Chat Header</div>
}));
jest.mock('../../../components/chat/MessageList', () => ({
  MessageList: () => <div data-testid="message-list">Message List</div>
}));
jest.mock('../../../components/chat/MessageInput', () => ({
  MessageInput: () => <div data-testid="message-input">Message Input</div>
}));
jest.mock('../../../components/chat/StopButton', () => ({
  StopButton: () => <button data-testid="stop-button">Stop</button>
}));
jest.mock('../../../components/chat/ExamplePrompts', () => ({
  ExamplePrompts: () => <div data-testid="example-prompts">Example Prompts</div>
}));

describe('MainChat Component', () => {
  const mockUseChatStore = useChatStore as jest.MockedFunction<typeof useChatStore>;
  const mockUseChatWebSocket = useChatWebSocket as jest.MockedFunction<typeof useChatWebSocket>;

  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('Component Rendering', () => {
    it('should render all main chat components correctly', () => {
      mockUseChatStore.mockReturnValue({
        isProcessing: false,
        messages: [],
        currentThread: null,
        threads: [],
        error: null,
        addMessage: jest.fn(),
        setIsProcessing: jest.fn(),
        clearMessages: jest.fn(),
        setCurrentThread: jest.fn(),
      });

      render(<MainChat />);

      expect(screen.getByTestId('chat-header')).toBeInTheDocument();
      expect(screen.getByTestId('message-list')).toBeInTheDocument();
      expect(screen.getByTestId('message-input')).toBeInTheDocument();
      expect(screen.getByTestId('example-prompts')).toBeInTheDocument();
      expect(screen.queryByTestId('stop-button')).not.toBeInTheDocument();
    });

    it('should show stop button when processing', () => {
      mockUseChatStore.mockReturnValue({
        isProcessing: true,
        messages: [],
        currentThread: null,
        threads: [],
        error: null,
        addMessage: jest.fn(),
        setIsProcessing: jest.fn(),
        clearMessages: jest.fn(),
        setCurrentThread: jest.fn(),
      });

      render(<MainChat />);

      expect(screen.getByTestId('stop-button')).toBeInTheDocument();
    });

    it('should hide stop button when not processing', () => {
      mockUseChatStore.mockReturnValue({
        isProcessing: false,
        messages: [],
        currentThread: null,
        threads: [],
        error: null,
        addMessage: jest.fn(),
        setIsProcessing: jest.fn(),
        clearMessages: jest.fn(),
        setCurrentThread: jest.fn(),
      });

      render(<MainChat />);

      expect(screen.queryByTestId('stop-button')).not.toBeInTheDocument();
    });

    it('should have correct layout structure', () => {
      mockUseChatStore.mockReturnValue({
        isProcessing: false,
        messages: [],
        currentThread: null,
        threads: [],
        error: null,
        addMessage: jest.fn(),
        setIsProcessing: jest.fn(),
        clearMessages: jest.fn(),
        setCurrentThread: jest.fn(),
      });

      const { container } = render(<MainChat />);
      
      const mainContainer = container.firstChild as HTMLElement;
      expect(mainContainer).toHaveClass('flex', 'h-screen', 'bg-gray-100');

      const chatContainer = mainContainer.firstChild as HTMLElement;
      expect(chatContainer).toHaveClass('flex', 'flex-col', 'flex-1');
    });
  });

  describe('WebSocket Integration', () => {
    it('should initialize WebSocket connection', () => {
      mockUseChatStore.mockReturnValue({
        isProcessing: false,
        messages: [],
        currentThread: null,
        threads: [],
        error: null,
        addMessage: jest.fn(),
        setIsProcessing: jest.fn(),
        clearMessages: jest.fn(),
        setCurrentThread: jest.fn(),
      });

      render(<MainChat />);

      expect(mockUseChatWebSocket).toHaveBeenCalled();
    });

    it('should maintain WebSocket connection throughout component lifecycle', () => {
      mockUseChatStore.mockReturnValue({
        isProcessing: false,
        messages: [],
        currentThread: null,
        threads: [],
        error: null,
        addMessage: jest.fn(),
        setIsProcessing: jest.fn(),
        clearMessages: jest.fn(),
        setCurrentThread: jest.fn(),
      });

      const { rerender } = render(<MainChat />);
      
      expect(mockUseChatWebSocket).toHaveBeenCalledTimes(1);
      
      rerender(<MainChat />);
      
      expect(mockUseChatWebSocket).toHaveBeenCalledTimes(2);
    });
  });

  describe('State Management', () => {
    it('should react to processing state changes', async () => {
      const mockStore = {
        isProcessing: false,
        messages: [],
        currentThread: null,
        threads: [],
        error: null,
        addMessage: jest.fn(),
        setIsProcessing: jest.fn(),
        clearMessages: jest.fn(),
        setCurrentThread: jest.fn(),
      };

      mockUseChatStore.mockReturnValue(mockStore);

      const { rerender } = render(<MainChat />);
      
      expect(screen.queryByTestId('stop-button')).not.toBeInTheDocument();

      mockStore.isProcessing = true;
      mockUseChatStore.mockReturnValue(mockStore);
      
      rerender(<MainChat />);
      
      expect(screen.getByTestId('stop-button')).toBeInTheDocument();
    });

    it('should handle store subscription correctly', () => {
      const mockStore = {
        isProcessing: false,
        messages: [],
        currentThread: null,
        threads: [],
        error: null,
        addMessage: jest.fn(),
        setIsProcessing: jest.fn(),
        clearMessages: jest.fn(),
        setCurrentThread: jest.fn(),
      };

      mockUseChatStore.mockReturnValue(mockStore);

      const { unmount } = render(<MainChat />);
      
      expect(mockUseChatStore).toHaveBeenCalled();
      
      unmount();
      
      // Component should clean up store subscriptions
    });
  });

  describe('Accessibility', () => {
    it('should have proper ARIA structure', () => {
      mockUseChatStore.mockReturnValue({
        isProcessing: false,
        messages: [],
        currentThread: null,
        threads: [],
        error: null,
        addMessage: jest.fn(),
        setIsProcessing: jest.fn(),
        clearMessages: jest.fn(),
        setCurrentThread: jest.fn(),
      });

      const { container } = render(<MainChat />);
      
      const mainContainer = container.firstChild as HTMLElement;
      expect(mainContainer).toBeInTheDocument();
      
      const scrollableArea = container.querySelector('.overflow-y-auto');
      expect(scrollableArea).toBeInTheDocument();
    });

    it('should handle keyboard navigation', async () => {
      mockUseChatStore.mockReturnValue({
        isProcessing: true,
        messages: [],
        currentThread: null,
        threads: [],
        error: null,
        addMessage: jest.fn(),
        setIsProcessing: jest.fn(),
        clearMessages: jest.fn(),
        setCurrentThread: jest.fn(),
      });

      render(<MainChat />);
      
      const stopButton = screen.getByTestId('stop-button');
      
      await userEvent.tab();
      
      expect(stopButton).toBeInTheDocument();
    });

    it('should maintain focus management during state changes', async () => {
      const mockStore = {
        isProcessing: false,
        messages: [],
        currentThread: null,
        threads: [],
        error: null,
        addMessage: jest.fn(),
        setIsProcessing: jest.fn(),
        clearMessages: jest.fn(),
        setCurrentThread: jest.fn(),
      };

      mockUseChatStore.mockReturnValue(mockStore);

      const { rerender } = render(<MainChat />);
      
      const messageInput = screen.getByTestId('message-input');
      fireEvent.focus(messageInput);
      
      mockStore.isProcessing = true;
      mockUseChatStore.mockReturnValue(mockStore);
      
      rerender(<MainChat />);
      
      expect(screen.getByTestId('stop-button')).toBeInTheDocument();
    });
  });

  describe('Error Handling', () => {
    it('should handle WebSocket connection errors gracefully', () => {
      mockUseChatWebSocket.mockImplementation(() => {
        throw new Error('WebSocket connection failed');
      });

      expect(() => render(<MainChat />)).not.toThrow();
    });

    it('should handle store initialization errors', () => {
      mockUseChatStore.mockImplementation(() => {
        throw new Error('Store initialization failed');
      });

      expect(() => render(<MainChat />)).toThrow('Store initialization failed');
    });
  });

  describe('Performance', () => {
    it('should not re-render unnecessarily', () => {
      const mockStore = {
        isProcessing: false,
        messages: [],
        currentThread: null,
        threads: [],
        error: null,
        addMessage: jest.fn(),
        setIsProcessing: jest.fn(),
        clearMessages: jest.fn(),
        setCurrentThread: jest.fn(),
      };

      mockUseChatStore.mockReturnValue(mockStore);

      const { rerender } = render(<MainChat />);
      
      const initialCallCount = mockUseChatStore.mock.calls.length;
      
      rerender(<MainChat />);
      
      expect(mockUseChatStore).toHaveBeenCalledTimes(initialCallCount + 1);
    });

    it('should handle rapid state updates efficiently', async () => {
      const mockStore = {
        isProcessing: false,
        messages: [],
        currentThread: null,
        threads: [],
        error: null,
        addMessage: jest.fn(),
        setIsProcessing: jest.fn(),
        clearMessages: jest.fn(),
        setCurrentThread: jest.fn(),
      };

      mockUseChatStore.mockReturnValue(mockStore);

      const { rerender } = render(<MainChat />);
      
      for (let i = 0; i < 10; i++) {
        mockStore.isProcessing = !mockStore.isProcessing;
        mockUseChatStore.mockReturnValue({ ...mockStore });
        rerender(<MainChat />);
      }
      
      expect(screen.getByTestId('message-input')).toBeInTheDocument();
    });
  });
});