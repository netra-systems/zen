import React from 'react';
import { render, screen } from '@testing-library/react';
import ChatHistory from '@/components/chat/ChatHistory';
import { useWebSocketContext } from '@/providers/WebSocketProvider';
import { TestProviders } from '../test-utils/providers';

// Mock dependencies
jest.mock('@/providers/WebSocketProvider', () => ({
  useWebSocketContext: jest.fn()
}));

jest.mock('@/components/chat/MessageItem', () => ({
  MessageItem: ({ message }: any) => (
    <div data-testid={`message-${message.id}`}>
      {message.content}
    </div>
  )
}));

describe('ChatHistory Component', () => {
  const mockWebSocketContext = {
    messages: [],
    connected: true,
    error: null,
    sendMessage: jest.fn()
  };

  beforeEach(() => {
    jest.clearAllMocks();
    (useWebSocketContext as jest.Mock).mockReturnValue(mockWebSocketContext);
  });

  const renderWithProvider = (component: React.ReactElement) => {
    return render(
      <TestProviders>
        {component}
      </TestProviders>
    );
  };

  describe('Basic Rendering', () => {
    it('should show loading when WebSocket context is not available', () => {
      (useWebSocketContext as jest.Mock).mockReturnValue(null);
      
      renderWithProvider(<ChatHistory />);
      
      expect(screen.getByText('Loading...')).toBeInTheDocument();
    });

    it('should render messages when WebSocket context has messages', () => {
      const mockMessages = [
        {
          type: 'user_message',
          sender: 'user',
          payload: { content: 'Hello, how can I help?' }
        },
        {
          type: 'assistant_message',
          sender: 'assistant',
          payload: { content: 'I can help with optimization' }
        }
      ];
      
      (useWebSocketContext as jest.Mock).mockReturnValue({
        ...mockWebSocketContext,
        messages: mockMessages
      });
      
      renderWithProvider(<ChatHistory />);
      
      expect(screen.getByText('Hello, how can I help?')).toBeInTheDocument();
      expect(screen.getByText('I can help with optimization')).toBeInTheDocument();
    });

    it('should handle empty message list', () => {
      (useWebSocketContext as jest.Mock).mockReturnValue({
        ...mockWebSocketContext,
        messages: []
      });
      
      renderWithProvider(<ChatHistory />);
      
      // Should render empty container
      expect(screen.queryByTestId(/message-/)).not.toBeInTheDocument();
    });

    it('should transform messages correctly', () => {
      const mockMessages = [
        {
          type: 'error',
          sender: 'system',
          payload: { error: 'Connection failed', message: 'Unable to connect' }
        },
        {
          type: 'data',
          sender: 'agent',
          payload: { 
            sub_agent_name: 'DataProcessor',
            tool_info: { name: 'analyze' },
            raw_data: { result: 'success' }
          }
        }
      ];
      
      (useWebSocketContext as jest.Mock).mockReturnValue({
        ...mockWebSocketContext,
        messages: mockMessages
      });
      
      renderWithProvider(<ChatHistory />);
      
      // Check error message transformation - uses first non-null value
      expect(screen.getByTestId('message-msg-0')).toHaveTextContent('Unable to connect');
      
      // Check data message transformation
      const dataMessage = screen.getByTestId('message-msg-1');
      expect(dataMessage).toBeInTheDocument();
    });

    it('should handle messages with different payload structures', () => {
      const mockMessages = [
        {
          type: 'info',
          payload: { message: 'Info message' }
        },
        {
          type: 'text',
          payload: { content: 'Text content' }
        },
        {
          type: 'custom',
          payload: { customField: 'custom value' }
        }
      ];
      
      (useWebSocketContext as jest.Mock).mockReturnValue({
        ...mockWebSocketContext,
        messages: mockMessages
      });
      
      renderWithProvider(<ChatHistory />);
      
      // Should handle different payload structures
      expect(screen.getByText('Info message')).toBeInTheDocument();
      expect(screen.getByText('Text content')).toBeInTheDocument();
      expect(screen.getByText(/"customField":"custom value"/)).toBeInTheDocument();
    });

    it('should generate unique ids for messages', () => {
      const mockMessages = [
        { type: 'msg1', payload: { content: 'First' } },
        { type: 'msg2', payload: { content: 'Second' } },
        { type: 'msg3', payload: { content: 'Third' } }
      ];
      
      (useWebSocketContext as jest.Mock).mockReturnValue({
        ...mockWebSocketContext,
        messages: mockMessages
      });
      
      renderWithProvider(<ChatHistory />);
      
      // Check that each message has a unique id
      expect(screen.getByTestId('message-msg-0')).toBeInTheDocument();
      expect(screen.getByTestId('message-msg-1')).toBeInTheDocument();
      expect(screen.getByTestId('message-msg-2')).toBeInTheDocument();
    });

    it('should pass correct props to MessageItem', () => {
      const mockMessage = {
        type: 'user_message',
        sender: 'user',
        payload: { 
          content: 'Test message',
          references: ['ref1', 'ref2']
        }
      };
      
      (useWebSocketContext as jest.Mock).mockReturnValue({
        ...mockWebSocketContext,
        messages: [mockMessage]
      });
      
      renderWithProvider(<ChatHistory />);
      
      // MessageItem should receive transformed message
      const messageElement = screen.getByTestId('message-msg-0');
      expect(messageElement).toHaveTextContent('Test message');
    });
  });

  describe('Container Styling', () => {
    it('should have correct container classes', () => {
      (useWebSocketContext as jest.Mock).mockReturnValue(mockWebSocketContext);
      
      const { container } = renderWithProvider(<ChatHistory />);
      
      const chatContainer = container.firstChild;
      expect(chatContainer).toHaveClass('flex-1', 'overflow-y-auto', 'p-4');
    });
  });
});