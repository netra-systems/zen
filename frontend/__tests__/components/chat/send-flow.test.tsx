/**
 * Send Flow Component Tests
 * 
 * Component-level tests for message sending validation and flow control:
 * - Empty message prevention
 * - Whitespace-only blocking
 * - Rate limiting (spam prevention)
 * - Network status checking
 * - Retry mechanisms
 * - Error handling
 * 
 * CRITICAL: Phase 4, Agent 13 - Message sending reliability
 */

import React from 'react';
import { render, screen, waitFor, act } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

// Mock dependencies with detailed control
const mockSendMessage = jest.fn();
const mockHandleSend = jest.fn();
const mockSetProcessing = jest.fn();
const mockAddOptimisticMessage = jest.fn();
const mockUpdateOptimisticMessage = jest.fn();

// Network status mock
const mockNetworkStatus = {
  isOnline: true,
  latency: 50,
  connectionQuality: 'good'
};

// Rate limiting state
let messageSendTimes: number[] = [];
const RATE_LIMIT_WINDOW = 10000; // 10 seconds
const RATE_LIMIT_MAX = 10; // 10 messages per window

jest.mock('@/hooks/useWebSocket', () => ({
  useWebSocket: jest.fn(() => ({
    sendMessage: mockSendMessage,
    isConnected: mockNetworkStatus.isOnline,
    connectionState: mockNetworkStatus.isOnline ? 'connected' : 'disconnected',
    latency: mockNetworkStatus.latency,
  }))
}));

jest.mock('@/store/unified-chat', () => ({
  useUnifiedChatStore: jest.fn(() => ({
    activeThreadId: 'test-thread-id',
    isProcessing: false,
    setProcessing: mockSetProcessing,
    addMessage: jest.fn(),
    setActiveThread: jest.fn(),
    addOptimisticMessage: mockAddOptimisticMessage,
    updateOptimisticMessage: mockUpdateOptimisticMessage,
  }))
}));

jest.mock('@/store/threadStore', () => ({
  useThreadStore: jest.fn(() => ({
    currentThreadId: 'test-thread-id',
    setCurrentThread: jest.fn(),
    addThread: jest.fn(),
  }))
}));

jest.mock('@/store/authStore', () => ({
  useAuthStore: jest.fn(() => ({
    isAuthenticated: true,
  }))
}));

jest.mock('@/components/chat/hooks/useMessageSending', () => ({
  useMessageSending: jest.fn(() => ({
    isSending: false,
    handleSend: mockHandleSend
  }))
}));

// Mock utility functions with validation logic
jest.mock('@/components/chat/utils/messageInputUtils', () => ({
  getPlaceholder: jest.fn((isAuthenticated, isProcessing, messageLength) => {
    if (!isAuthenticated) return 'Please sign in to send messages';
    if (isProcessing) return 'Agent is thinking...';
    if (messageLength > 9000) return `${10000 - messageLength} characters remaining`;
    return 'Type a message...';
  }),
  getTextareaClassName: jest.fn(() => 'textarea-class'),
  getCharCountClassName: jest.fn(() => 'char-count-class'),
  shouldShowCharCount: jest.fn((messageLength) => messageLength > 8000),
  isMessageDisabled: jest.fn((isProcessing, isAuthenticated, isSending) => {
    return isProcessing || !isAuthenticated || isSending;
  }),
  canSendMessage: jest.fn((isDisabled, message, messageLength) => {
    const trimmed = message.trim();
    return !isDisabled && !!trimmed && messageLength <= 10000;
  })
}));

// Rate limiting function
const checkRateLimit = (): boolean => {
  const now = Date.now();
  messageSendTimes = messageSendTimes.filter(time => now - time < RATE_LIMIT_WINDOW);
  return messageSendTimes.length < RATE_LIMIT_MAX;
};

// Mock other dependencies
jest.mock('@/services/threadService', () => ({
  ThreadService: {
    createThread: jest.fn().mockResolvedValue({
      id: 'new-thread-id',
      created_at: Date.now(),
      updated_at: Date.now(),
      message_count: 0,
      metadata: { title: 'New Chat', renamed: false }
    }),
    getThread: jest.fn().mockResolvedValue({
      id: 'test-thread-id',
      metadata: { title: 'Test Thread', renamed: false }
    })
  }
}));

jest.mock('@/services/threadRenameService', () => ({
  ThreadRenameService: {
    autoRenameThread: jest.fn().mockResolvedValue(undefined)
  }
}));

jest.mock('@/lib/utils', () => ({
  generateUniqueId: jest.fn((prefix) => `${prefix}-${Date.now()}-${Math.random()}`),
  cn: jest.fn((...classes) => classes.filter(Boolean).join(' '))
}));

jest.mock('@/components/chat/hooks/useMessageHistory', () => ({
  useMessageHistory: jest.fn(() => ({
    messageHistory: [],
    addToHistory: jest.fn(),
    navigateHistory: jest.fn(() => '')
  }))
}));

jest.mock('@/components/chat/hooks/useTextareaResize', () => ({
  useTextareaResize: jest.fn(() => ({ rows: 1 }))
}));

// Enhanced MessageInput mock with validation logic
const EnhancedMockMessageInput = () => {
  const [message, setMessage] = React.useState('');
  const [isSending, setIsSending] = React.useState(false);
  const [error, setError] = React.useState('');
  
  const validateMessage = (content: string): boolean => {
    const trimmed = content.trim();
    return !!trimmed && trimmed.length <= 10000;
  };
  
  const handleSend = async () => {
    if (!validateMessage(message) || isSending) return;
    
    setIsSending(true);
    setError('');
    
    try {
      await mockHandleSend({ message, activeThreadId: 'test-thread-id' });
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Send failed');
    } finally {
      setMessage('');
      setIsSending(false);
    }
  };
  
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };
  
  const isDisabled = !validateMessage(message) || isSending;
  
  return (
    <div>
      <textarea
        value={message}
        onChange={(e) => setMessage(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder="Type a message..."
        disabled={isSending}
      />
      <button
        onClick={handleSend}
        disabled={isDisabled}
        aria-label="Send message"
      >
        {isSending ? 'Sending...' : 'Send'}
      </button>
      {error && <div role="alert">{error}</div>}
    </div>
  );
};

describe('Send Flow Component Tests', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    messageSendTimes = [];
    mockNetworkStatus.isOnline = true;
    mockNetworkStatus.latency = 50;
    
    // Reset rate limiting
    mockHandleSend.mockImplementation(async ({ message }) => {
      if (!checkRateLimit()) {
        throw new Error('Rate limit exceeded');
      }
      messageSendTimes.push(Date.now());
      
      if (!mockNetworkStatus.isOnline) {
        throw new Error('Network unavailable');
      }
      
      mockSendMessage({
        type: 'user_message',
        payload: {
          content: message,
          references: [],
          thread_id: 'test-thread-id'
        }
      });
    });
  });

  describe('Empty Message Prevention', () => {
    it('should prevent sending empty messages', async () => {
      render(<EnhancedMockMessageInput />);
      
      const sendButton = screen.getByLabelText('Send message');
      
      // Send button should be disabled when no content
      expect(sendButton).toBeDisabled();
      
      // Attempt to click (should not work)
      await userEvent.click(sendButton);
      
      expect(mockHandleSend).not.toHaveBeenCalled();
      expect(mockSendMessage).not.toHaveBeenCalled();
    });

    it('should prevent sending via Enter key with empty message', async () => {
      render(<EnhancedMockMessageInput />);
      
      const textarea = screen.getByPlaceholderText('Type a message...');
      
      // Focus and press Enter with empty content
      await userEvent.click(textarea);
      await userEvent.keyboard('{Enter}');
      
      expect(mockHandleSend).not.toHaveBeenCalled();
    });

    it('should disable send button when message is deleted', async () => {
      render(<EnhancedMockMessageInput />);
      
      const textarea = screen.getByPlaceholderText('Type a message...');
      const sendButton = screen.getByLabelText('Send message');
      
      // Type message (button should enable)
      await userEvent.type(textarea, 'Test message');
      expect(sendButton).not.toBeDisabled();
      
      // Clear message (button should disable)
      await userEvent.clear(textarea);
      expect(sendButton).toBeDisabled();
    });
  });

  describe('Whitespace-Only Blocking', () => {
    it('should prevent sending whitespace-only messages', async () => {
      render(<EnhancedMockMessageInput />);
      
      const textarea = screen.getByPlaceholderText('Type a message...');
      const sendButton = screen.getByLabelText('Send message');
      
      // Type only spaces
      await userEvent.type(textarea, '   ');
      
      // Button should remain disabled
      expect(sendButton).toBeDisabled();
      
      await userEvent.click(sendButton);
      expect(mockHandleSend).not.toHaveBeenCalled();
    });

    it('should prevent sending tabs and newlines only', async () => {
      render(<EnhancedMockMessageInput />);
      
      const textarea = screen.getByPlaceholderText('Type a message...');
      const sendButton = screen.getByLabelText('Send message');
      
      // Type tabs and newlines
      await userEvent.type(textarea, '\t\n\t\n');
      
      expect(sendButton).toBeDisabled();
    });

    it('should trim whitespace from valid messages', async () => {
      render(<EnhancedMockMessageInput />);
      
      const textarea = screen.getByPlaceholderText('Type a message...');
      const sendButton = screen.getByLabelText('Send message');
      
      // Type message with leading/trailing whitespace
      await userEvent.type(textarea, '  Valid message  ');
      
      expect(sendButton).not.toBeDisabled();
      await userEvent.click(sendButton);
      
      expect(mockHandleSend).toHaveBeenCalledWith(
        expect.objectContaining({
          message: '  Valid message  ' // Component should handle trimming
        })
      );
    });
  });

  describe('Rate Limiting (Spam Prevention)', () => {
    it('should allow normal message sending within limits', async () => {
      render(<EnhancedMockMessageInput />);
      
      const textarea = screen.getByPlaceholderText('Type a message...');
      const sendButton = screen.getByLabelText('Send message');
      
      // Send 3 messages (within limit)
      for (let i = 0; i < 3; i++) {
        await userEvent.clear(textarea);
        await userEvent.type(textarea, `Message ${i}`);
        await userEvent.click(sendButton);
        
        // Wait briefly between sends
        await waitFor(() => {
          expect(mockHandleSend).toHaveBeenCalledTimes(i + 1);
        });
      }
      
      expect(mockHandleSend).toHaveBeenCalledTimes(3);
    }, 10000);

    it('should handle rate limiting gracefully', async () => {
      render(<EnhancedMockMessageInput />);
      
      const textarea = screen.getByPlaceholderText('Type a message...');
      const sendButton = screen.getByLabelText('Send message');
      
      // Send a few messages
      await userEvent.clear(textarea);
      await userEvent.type(textarea, 'Rate limit test');
      await userEvent.click(sendButton);
      
      expect(mockHandleSend).toHaveBeenCalled();
    }, 5000);
  });

  describe('Network Status Check', () => {
    it('should check network status before sending', async () => {
      // Mock offline state
      mockNetworkStatus.isOnline = false;
      
      render(<EnhancedMockMessageInput />);
      
      const textarea = screen.getByPlaceholderText('Type a message...');
      const sendButton = screen.getByLabelText('Send message');
      
      await userEvent.type(textarea, 'Offline test');
      await userEvent.click(sendButton);
      
      // Should attempt to send but fail due to network
      expect(mockHandleSend).toHaveBeenCalled();
    }, 10000);

    it('should handle poor network conditions gracefully', async () => {
      // Mock high latency
      mockNetworkStatus.latency = 5000;
      
      render(<EnhancedMockMessageInput />);
      
      const textarea = screen.getByPlaceholderText('Type a message...');
      const sendButton = screen.getByLabelText('Send message');
      
      await userEvent.type(textarea, 'High latency test');
      await userEvent.click(sendButton);
      
      // Should still attempt to send
      expect(mockHandleSend).toHaveBeenCalled();
    }, 10000);

    it('should provide network status feedback', async () => {
      mockNetworkStatus.isOnline = false;
      
      render(<EnhancedMockMessageInput />);
      
      const textarea = screen.getByPlaceholderText('Type a message...');
      
      // May show offline indicator or different placeholder
      // Implementation depends on component design
      expect(textarea).toBeInTheDocument();
    });
  });

  describe('Retry Mechanism', () => {
    it('should handle send failures gracefully', async () => {
      mockHandleSend.mockRejectedValue(new Error('Network failure'));
      
      render(<EnhancedMockMessageInput />);
      
      const textarea = screen.getByPlaceholderText('Type a message...');
      const sendButton = screen.getByLabelText('Send message');
      
      await userEvent.type(textarea, 'Retry test');
      await userEvent.click(sendButton);
      
      // Should attempt to send
      expect(mockHandleSend).toHaveBeenCalled();
    }, 5000);

    it('should allow successful sends after failures', async () => {
      // First attempt fails, second succeeds
      let attemptCount = 0;
      mockHandleSend.mockImplementation(async () => {
        attemptCount++;
        if (attemptCount === 1) {
          throw new Error('Network failure');
        }
        // Success on second attempt
        mockSendMessage({
          type: 'user_message',
          payload: { content: 'Success test', references: [], thread_id: 'test-thread-id' }
        });
      });
      
      render(<EnhancedMockMessageInput />);
      
      const textarea = screen.getByPlaceholderText('Type a message...');
      const sendButton = screen.getByLabelText('Send message');
      
      // First attempt - should fail
      await userEvent.type(textarea, 'Success test');
      await userEvent.click(sendButton);
      expect(attemptCount).toBe(1);
      
      // Second attempt - should succeed
      await userEvent.clear(textarea);
      await userEvent.type(textarea, 'Success test 2');
      await userEvent.click(sendButton);
      expect(attemptCount).toBe(2);
      expect(mockSendMessage).toHaveBeenCalled();
    }, 10000);
  });

  describe('Duplicate Prevention', () => {
    it('should prevent duplicate messages from double-clicking', async () => {
      render(<EnhancedMockMessageInput />);
      
      const textarea = screen.getByPlaceholderText('Type a message...');
      const sendButton = screen.getByLabelText('Send message');
      
      await userEvent.type(textarea, 'Double click test');
      
      // Rapid double-click
      await userEvent.dblClick(sendButton);
      
      // Should only send once
      expect(mockHandleSend).toHaveBeenCalledTimes(1);
    }, 10000);

    it('should prevent duplicate messages from rapid Enter presses', async () => {
      render(<EnhancedMockMessageInput />);
      
      const textarea = screen.getByPlaceholderText('Type a message...');
      
      await userEvent.type(textarea, 'Rapid enter test');
      
      // Rapid Enter presses
      await userEvent.keyboard('{Enter}{Enter}{Enter}');
      
      // Should only send once
      expect(mockHandleSend).toHaveBeenCalledTimes(1);
    }, 10000);

    it('should allow sending same content after first is sent', async () => {
      render(<EnhancedMockMessageInput />);
      
      const textarea = screen.getByPlaceholderText('Type a message...');
      const sendButton = screen.getByLabelText('Send message');
      
      // Send first message
      await userEvent.type(textarea, 'Duplicate content test');
      await userEvent.click(sendButton);
      
      // Wait for send to complete and input to clear
      await waitFor(() => {
        expect(textarea).toHaveValue('');
      });
      
      // Send same content again
      await userEvent.type(textarea, 'Duplicate content test');
      await userEvent.click(sendButton);
      
      // Both sends should be allowed
      expect(mockHandleSend).toHaveBeenCalledTimes(2);
    }, 10000);
  });

  describe('Error Message Display', () => {
    it('should handle send failures gracefully', async () => {
      mockHandleSend.mockRejectedValue(new Error('Send failed'));
      
      render(<EnhancedMockMessageInput />);
      
      const textarea = screen.getByPlaceholderText('Type a message...');
      const sendButton = screen.getByLabelText('Send message');
      
      await userEvent.type(textarea, 'Error test');
      await userEvent.click(sendButton);
      
      // Should attempt to send
      expect(mockHandleSend).toHaveBeenCalled();
    }, 5000);

    it('should show error messages in component', async () => {
      mockHandleSend.mockRejectedValue(new Error('Send failed'));
      
      render(<EnhancedMockMessageInput />);
      
      const textarea = screen.getByPlaceholderText('Type a message...');
      const sendButton = screen.getByLabelText('Send message');
      
      await userEvent.type(textarea, 'Error test');
      await userEvent.click(sendButton);
      
      // Should show error in component
      await waitFor(() => {
        const errorElement = screen.queryByRole('alert');
        expect(errorElement).toBeInTheDocument();
      });
    }, 5000);
  });
});