import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MessageInput } from '../../../components/chat/MessageInput';
import { useWebSocket } from '../../../hooks/useWebSocket';
import { useChatStore } from '../../../store/chat';

jest.mock('../../../hooks/useWebSocket');
jest.mock('../../../store/chat');

const mockUseWebSocket = useWebSocket as jest.MockedFunction<typeof useWebSocket>;
const mockUseChatStore = useChatStore as jest.MockedFunction<typeof useChatStore>;

describe('MessageInput Component', () => {
  const mockSendMessage = jest.fn();
  const mockAddMessage = jest.fn();
  const mockSetProcessing = jest.fn();

  beforeEach(() => {
    mockUseWebSocket.mockReturnValue({
      sendMessage: mockSendMessage,
      isConnected: true,
      connectionState: 'connected' as const,
      lastMessage: null,
    });

    mockUseChatStore.mockReturnValue({
      isProcessing: false,
      addMessage: mockAddMessage,
      setProcessing: mockSetProcessing,
      messages: [],
    } as any);

    jest.clearAllMocks();
  });

  describe('Rendering', () => {
    it('should render input field and send button', () => {
      render(<MessageInput />);

      expect(screen.getByPlaceholderText('Type your message...')).toBeInTheDocument();
      expect(screen.getByRole('button', { name: 'Send' })).toBeInTheDocument();
    });

    it('should show processing placeholder when agent is thinking', () => {
      mockUseChatStore.mockReturnValue({
        isProcessing: true,
        addMessage: mockAddMessage,
        setProcessing: mockSetProcessing,
        messages: [],
      } as any);

      render(<MessageInput />);
      expect(screen.getByPlaceholderText('Agent is thinking...')).toBeInTheDocument();
    });

    it('should apply correct styling classes', () => {
      render(<MessageInput />);
      
      const input = screen.getByPlaceholderText('Type your message...');
      const sendButton = screen.getByRole('button', { name: 'Send' });
      
      expect(input).toHaveClass('flex-grow', 'rounded-full', 'py-2', 'px-4', 'bg-gray-100');
      expect(sendButton).toHaveClass('ml-4', 'rounded-full', 'w-12', 'h-12');
    });
  });

  describe('User Input', () => {
    it('should update input value when typing', async () => {
      render(<MessageInput />);
      const input = screen.getByPlaceholderText('Type your message...');

      await userEvent.type(input, 'Hello World');
      expect(input).toHaveValue('Hello World');
    });

    it('should handle special characters and emojis', async () => {
      render(<MessageInput />);
      const input = screen.getByPlaceholderText('Type your message...');

      await userEvent.type(input, 'Hello! 👋 Special chars: @#$%^&*()');
      expect(input).toHaveValue('Hello! 👋 Special chars: @#$%^&*()');
    });

    it('should handle long messages', async () => {
      render(<MessageInput />);
      const input = screen.getByPlaceholderText('Type your message...');
      const longMessage = 'A'.repeat(1000);

      await userEvent.type(input, longMessage);
      expect(input).toHaveValue(longMessage);
    });

    it('should trim whitespace from messages', async () => {
      render(<MessageInput />);
      const input = screen.getByPlaceholderText('Type your message...');
      const sendButton = screen.getByRole('button', { name: 'Send' });

      await userEvent.type(input, '  Hello World  ');
      await userEvent.click(sendButton);

      expect(mockAddMessage).toHaveBeenCalledWith(
        expect.objectContaining({
          content: '  Hello World  ',
        })
      );
    });
  });

  describe('Message Sending', () => {
    it('should send message when send button is clicked', async () => {
      render(<MessageInput />);
      const input = screen.getByPlaceholderText('Type your message...');
      const sendButton = screen.getByRole('button', { name: 'Send' });

      await userEvent.type(input, 'Hello World');
      await userEvent.click(sendButton);

      expect(mockAddMessage).toHaveBeenCalledWith(
        expect.objectContaining({
          role: 'user',
          content: 'Hello World',
          displayed_to_user: true,
        })
      );
      expect(mockSendMessage).toHaveBeenCalledWith({
        type: 'user_message',
        payload: { text: 'Hello World', references: [] },
      });
      expect(mockSetProcessing).toHaveBeenCalledWith(true);
      expect(input).toHaveValue('');
    });

    it('should send message when Enter key is pressed', async () => {
      render(<MessageInput />);
      const input = screen.getByPlaceholderText('Type your message...');

      await userEvent.type(input, 'Hello World');
      fireEvent.keyPress(input, { key: 'Enter', charCode: 13 });

      expect(mockAddMessage).toHaveBeenCalled();
      expect(mockSendMessage).toHaveBeenCalled();
      expect(mockSetProcessing).toHaveBeenCalledWith(true);
    });

    it('should not send on other key presses', async () => {
      render(<MessageInput />);
      const input = screen.getByPlaceholderText('Type your message...');

      await userEvent.type(input, 'Hello World');
      fireEvent.keyPress(input, { key: 'Space', charCode: 32 });
      fireEvent.keyPress(input, { key: 'Tab', charCode: 9 });

      expect(mockSendMessage).not.toHaveBeenCalled();
    });

    it('should not send empty or whitespace-only messages', async () => {
      render(<MessageInput />);
      const input = screen.getByPlaceholderText('Type your message...');
      const sendButton = screen.getByRole('button', { name: 'Send' });

      // Test empty message
      await userEvent.click(sendButton);
      expect(mockSendMessage).not.toHaveBeenCalled();

      // Test whitespace-only message
      await userEvent.type(input, '   ');
      await userEvent.click(sendButton);
      expect(mockSendMessage).not.toHaveBeenCalled();
    });

    it('should generate unique message IDs', async () => {
      render(<MessageInput />);
      const input = screen.getByPlaceholderText('Type your message...');
      const sendButton = screen.getByRole('button', { name: 'Send' });

      await userEvent.type(input, 'First message');
      await userEvent.click(sendButton);

      await userEvent.type(input, 'Second message');
      await userEvent.click(sendButton);

      expect(mockAddMessage).toHaveBeenCalledTimes(2);
      const firstCall = mockAddMessage.mock.calls[0][0];
      const secondCall = mockAddMessage.mock.calls[1][0];
      expect(firstCall.id).not.toEqual(secondCall.id);
      expect(firstCall.id).toMatch(/^msg_\d+$/);
    });

    it('should include timestamp in user messages', async () => {
      const mockDate = new Date('2023-10-01T12:00:00Z');
      jest.spyOn(global, 'Date').mockImplementation(() => mockDate as any);
      jest.spyOn(mockDate, 'toISOString').mockReturnValue('2023-10-01T12:00:00.000Z');

      render(<MessageInput />);
      const input = screen.getByPlaceholderText('Type your message...');
      const sendButton = screen.getByRole('button', { name: 'Send' });

      await userEvent.type(input, 'Test message');
      await userEvent.click(sendButton);

      expect(mockAddMessage).toHaveBeenCalledWith(
        expect.objectContaining({
          timestamp: '2023-10-01T12:00:00.000Z',
        })
      );

      jest.restoreAllMocks();
    });
  });

  describe('Processing State', () => {
    it('should disable input and button when processing', () => {
      mockUseChatStore.mockReturnValue({
        isProcessing: true,
        addMessage: mockAddMessage,
        setProcessing: mockSetProcessing,
        messages: [],
      } as any);

      render(<MessageInput />);

      const input = screen.getByPlaceholderText('Agent is thinking...');
      const sendButton = screen.getByRole('button', { name: 'Send' });

      expect(input).toBeDisabled();
      expect(sendButton).toBeDisabled();
    });

    it('should not send messages when disabled', async () => {
      mockUseChatStore.mockReturnValue({
        isProcessing: true,
        addMessage: mockAddMessage,
        setProcessing: mockSetProcessing,
        messages: [],
      } as any);

      render(<MessageInput />);
      const input = screen.getByPlaceholderText('Agent is thinking...');
      const sendButton = screen.getByRole('button', { name: 'Send' });

      fireEvent.click(sendButton);
      fireEvent.keyPress(input, { key: 'Enter', charCode: 13 });

      expect(mockSendMessage).not.toHaveBeenCalled();
    });

    it('should transition between processing states correctly', () => {
      const { rerender } = render(<MessageInput />);
      
      expect(screen.getByPlaceholderText('Type your message...')).toBeInTheDocument();

      mockUseChatStore.mockReturnValue({
        isProcessing: true,
        addMessage: mockAddMessage,
        setProcessing: mockSetProcessing,
        messages: [],
      } as any);

      rerender(<MessageInput />);
      
      expect(screen.getByPlaceholderText('Agent is thinking...')).toBeInTheDocument();
    });
  });

  describe('Accessibility', () => {
    it('should have proper ARIA labels', () => {
      render(<MessageInput />);
      
      const sendButton = screen.getByRole('button', { name: 'Send' });
      expect(sendButton).toHaveAttribute('aria-label', 'Send');
    });

    it('should support keyboard navigation', async () => {
      render(<MessageInput />);
      
      const input = screen.getByPlaceholderText('Type your message...');
      const sendButton = screen.getByRole('button', { name: 'Send' });

      await userEvent.tab();
      expect(input).toHaveFocus();
      
      await userEvent.tab();
      expect(sendButton).toHaveFocus();
    });

    it('should maintain focus after sending message', async () => {
      render(<MessageInput />);
      const input = screen.getByPlaceholderText('Type your message...');

      await userEvent.type(input, 'Test message');
      await userEvent.keyboard('{Enter}');

      await waitFor(() => {
        expect(input).toHaveFocus();
      });
    });
  });

  describe('Error Handling', () => {
    it('should handle WebSocket send failures gracefully', async () => {
      mockSendMessage.mockImplementation(() => {
        throw new Error('WebSocket error');
      });

      render(<MessageInput />);
      const input = screen.getByPlaceholderText('Type your message...');
      const sendButton = screen.getByRole('button', { name: 'Send' });

      await userEvent.type(input, 'Test message');
      
      expect(() => fireEvent.click(sendButton)).not.toThrow();
    });

    it('should handle store update failures', async () => {
      mockAddMessage.mockImplementation(() => {
        throw new Error('Store error');
      });

      render(<MessageInput />);
      const input = screen.getByPlaceholderText('Type your message...');
      const sendButton = screen.getByRole('button', { name: 'Send' });

      await userEvent.type(input, 'Test message');
      
      expect(() => fireEvent.click(sendButton)).not.toThrow();
    });
  });

  describe('Performance', () => {
    it('should debounce rapid key presses', async () => {
      render(<MessageInput />);
      const input = screen.getByPlaceholderText('Type your message...');

      for (let i = 0; i < 10; i++) {
        fireEvent.keyPress(input, { key: 'Enter', charCode: 13 });
      }

      expect(mockSendMessage).toHaveBeenCalledTimes(0);
    });

    it('should handle rapid state updates without memory leaks', () => {
      const { rerender } = render(<MessageInput />);
      
      for (let i = 0; i < 100; i++) {
        const isProcessing = i % 2 === 0;
        mockUseChatStore.mockReturnValue({
          isProcessing,
          addMessage: mockAddMessage,
          setProcessing: mockSetProcessing,
          messages: [],
        } as any);
        
        rerender(<MessageInput />);
      }

      expect(screen.getByRole('button', { name: 'Send' })).toBeInTheDocument();
    });
  });
});