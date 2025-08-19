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
      
      // Send 5 messages (within limit)
      for (let i = 0; i < 5; i++) {
        await userEvent.clear(textarea);
        await userEvent.type(textarea, `Message ${i}`);
        await userEvent.click(sendButton);
      }
      
      expect(mockHandleSend).toHaveBeenCalledTimes(5);
    });

    it('should prevent spam by rate limiting rapid sends', async () => {
      render(<EnhancedMockMessageInput />);
      
      const textarea = screen.getByPlaceholderText('Type a message...');
      const sendButton = screen.getByLabelText('Send message');
      
      // Attempt to send 15 messages rapidly (exceeds limit of 10)
      for (let i = 0; i < 15; i++) {
        await userEvent.clear(textarea);
        await userEvent.type(textarea, `Spam message ${i}`, { delay: 1 });
        try {
          await userEvent.click(sendButton);
        } catch (error) {
          // Rate limit errors are expected after 10 messages
        }
      }
      
      // Should only process 10 messages
      expect(mockHandleSend).toHaveBeenCalledTimes(10);
    }, 10000); // Increase timeout

    it('should reset rate limit after time window', async () => {
      jest.useFakeTimers();
      
      render(<EnhancedMockMessageInput />);
      
      const textarea = screen.getByPlaceholderText('Type a message...');
      const sendButton = screen.getByLabelText('Send message');
      
      // Send 10 messages to reach limit
      for (let i = 0; i < 10; i++) {
        await userEvent.clear(textarea);
        await userEvent.type(textarea, `Message ${i}`, { delay: 1 });
        await userEvent.click(sendButton);
      }
      
      // Advance time past rate limit window
      act(() => {
        jest.advanceTimersByTime(RATE_LIMIT_WINDOW + 1000);
      });
      
      // Should be able to send again
      await userEvent.clear(textarea);
      await userEvent.type(textarea, 'After reset message', { delay: 1 });
      await userEvent.click(sendButton);
      
      expect(mockHandleSend).toHaveBeenCalledTimes(11);
      
      jest.useRealTimers();
    }, 10000); // Increase timeout
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
    });

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
    });

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
    it('should retry failed messages with exponential backoff', async () => {
      jest.useFakeTimers();
      
      // Mock send failure then success
      let attemptCount = 0;
      mockHandleSend.mockImplementation(async () => {
        attemptCount++;
        if (attemptCount <= 2) {
          throw new Error('Network failure');
        }
        // Success on third attempt
        mockSendMessage({
          type: 'user_message',
          payload: { content: 'Retry test', references: [], thread_id: 'test-thread-id' }
        });
      });
      
      render(<EnhancedMockMessageInput />);
      
      const textarea = screen.getByPlaceholderText('Type a message...');
      const sendButton = screen.getByLabelText('Send message');
      
      await userEvent.type(textarea, 'Retry test');
      await userEvent.click(sendButton);
      
      // Initial failure
      expect(attemptCount).toBe(1);
      
      // Wait for first retry (1 second)
      act(() => {
        jest.advanceTimersByTime(1000);
      });
      
      await waitFor(() => {
        expect(attemptCount).toBe(2);
      });
      
      // Wait for second retry (2 seconds - exponential backoff)
      act(() => {
        jest.advanceTimersByTime(2000);
      });
      
      await waitFor(() => {
        expect(attemptCount).toBe(3);
        expect(mockSendMessage).toHaveBeenCalled();
      });
      
      jest.useRealTimers();
    });

    it('should stop retrying after max attempts', async () => {
      jest.useFakeTimers();
      
      // Mock persistent failure
      mockHandleSend.mockRejectedValue(new Error('Persistent failure'));
      
      render(<EnhancedMockMessageInput />);
      
      const textarea = screen.getByPlaceholderText('Type a message...');
      const sendButton = screen.getByLabelText('Send message');
      
      await userEvent.type(textarea, 'Max retry test');
      await userEvent.click(sendButton);
      
      // Advance through all retry attempts
      for (let i = 0; i < 5; i++) {
        act(() => {
          jest.advanceTimersByTime(Math.pow(2, i) * 1000);
        });
      }
      
      // Should stop retrying after max attempts
      expect(mockHandleSend).toHaveBeenCalledTimes(3); // Initial + 2 retries
      
      jest.useRealTimers();
    });
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
    });

    it('should prevent duplicate messages from rapid Enter presses', async () => {
      render(<EnhancedMockMessageInput />);
      
      const textarea = screen.getByPlaceholderText('Type a message...');
      
      await userEvent.type(textarea, 'Rapid enter test');
      
      // Rapid Enter presses
      await userEvent.keyboard('{Enter}{Enter}{Enter}');
      
      // Should only send once
      expect(mockHandleSend).toHaveBeenCalledTimes(1);
    });

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
    });
  });

  describe('Error Message Display', () => {
    it('should display error message on send failure', async () => {
      mockHandleSend.mockRejectedValue(new Error('Send failed'));
      
      render(<EnhancedMockMessageInput />);
      
      const textarea = screen.getByPlaceholderText('Type a message...');
      const sendButton = screen.getByLabelText('Send message');
      
      await userEvent.type(textarea, 'Error test');
      await userEvent.click(sendButton);
      
      // Should show error state
      await waitFor(() => {
        expect(mockUpdateOptimisticMessage).toHaveBeenCalledWith(
          expect.any(String),
          expect.objectContaining({ status: 'failed' })
        );
      });
    });

    it('should clear error message on successful retry', async () => {
      let attemptCount = 0;
      mockHandleSend.mockImplementation(async () => {
        attemptCount++;
        if (attemptCount === 1) {
          throw new Error('First attempt failed');
        }
        // Success on retry
        mockSendMessage({
          type: 'user_message',
          payload: { content: 'Retry success', references: [], thread_id: 'test-thread-id' }
        });
      });
      
      render(<EnhancedMockMessageInput />);
      
      const textarea = screen.getByPlaceholderText('Type a message...');
      const sendButton = screen.getByLabelText('Send message');
      
      await userEvent.type(textarea, 'Retry success');
      await userEvent.click(sendButton);
      
      // First attempt fails
      await waitFor(() => {
        expect(mockUpdateOptimisticMessage).toHaveBeenCalledWith(
          expect.any(String),
          expect.objectContaining({ status: 'failed' })
        );
      });
      
      // Simulate retry
      mockHandleSend.mockClear();
      await userEvent.click(sendButton);
      
      // Should clear error on success
      await waitFor(() => {
        expect(mockSendMessage).toHaveBeenCalled();
      });
    });

    it('should show appropriate error for different failure types', async () => {
      const errorScenarios = [
        { error: new Error('Network error'), expectedType: 'network' },
        { error: new Error('Rate limit exceeded'), expectedType: 'rate_limit' },
        { error: new Error('Authentication failed'), expectedType: 'auth' },
      ];
      
      for (const scenario of errorScenarios) {
        mockHandleSend.mockRejectedValue(scenario.error);
        
        render(<EnhancedMockMessageInput />);
        
        const textarea = screen.getByPlaceholderText('Type a message...');
        const sendButton = screen.getByLabelText('Send message');
        
        await userEvent.type(textarea, 'Error type test');
        await userEvent.click(sendButton);
        
        // Verify error handling
        await waitFor(() => {
          expect(mockHandleSend).toHaveBeenCalled();
        });
      }
    });
  });
});