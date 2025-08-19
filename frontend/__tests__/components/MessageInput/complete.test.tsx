/**
 * Complete MessageInput Component Tests - Revenue Critical
 * 
 * Business Value Justification:
 * - Segment: All (Free → Enterprise) 
 * - Goal: Protect primary user input interface, prevent conversion loss
 * - Value Impact: Ensures 100% of user messages can be entered and sent
 * - Revenue Impact: Prevents 30%+ conversion loss from input failures
 */

import React from 'react';
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { WebSocketTestManager } from '../../helpers/websocket-test-manager';
import { MessageInput } from '@/components/chat/MessageInput';

// ============================================
// Test Setup and Mocks (8 lines each)
// ============================================

const mockUnifiedStore = {
  activeThreadId: 'thread-123',
  isProcessing: false,
  sendMessage: jest.fn(),
  addOptimisticMessage: jest.fn()
};

const mockThreadStore = {
  currentThreadId: 'thread-123',
  createThread: jest.fn(),
  switchThread: jest.fn()
};

const mockAuthStore = {
  isAuthenticated: true,
  user: { id: 'user-123', email: 'test@test.com' },
  login: jest.fn(),
  logout: jest.fn()
};

const mockMessageSending = {
  isSending: false,
  handleSend: jest.fn(),
  sendError: null,
  resetError: jest.fn()
};

// ============================================
// Mock Hooks and Providers
// ============================================

jest.mock('@/store/unified-chat', () => ({
  useUnifiedChatStore: () => mockUnifiedStore
}));

jest.mock('@/store/threadStore', () => ({
  useThreadStore: () => mockThreadStore
}));

jest.mock('@/store/authStore', () => ({
  useAuthStore: () => mockAuthStore
}));

jest.mock('@/components/chat/hooks/useMessageSending', () => ({
  useMessageSending: () => mockMessageSending
}));

const TestWrapper = ({ children }: { children: React.ReactNode }) => (
  <div data-testid="message-input-wrapper">{children}</div>
);

// ============================================
// Input Validation Tests
// ============================================

describe('MessageInput - Text Input Validation', () => {
  let user: ReturnType<typeof userEvent.setup>;
  let wsManager: WebSocketTestManager;
  
  beforeEach(() => {
    user = userEvent.setup();
    wsManager = new WebSocketTestManager();
    wsManager.setup();
    jest.clearAllMocks();
  });
  
  afterEach(() => {
    wsManager.cleanup();
  });

  it('accepts standard text input', async () => {
    render(<TestWrapper><MessageInput /></TestWrapper>);
    
    const input = screen.getByRole('textbox');
    await user.type(input, 'Hello world');
    
    expect(input).toHaveValue('Hello world');
    expect(screen.getByRole('button', { name: /send/i })).toBeEnabled();
  });

  it('handles emoji characters correctly', async () => {
    render(<TestWrapper><MessageInput /></TestWrapper>);
    
    const input = screen.getByRole('textbox');
    await user.type(input, '🚀 Hello! 👋 Testing 🎉');
    
    expect(input).toHaveValue('🚀 Hello! 👋 Testing 🎉');
  });

  it('processes special characters properly', async () => {
    render(<TestWrapper><MessageInput /></TestWrapper>);
    
    const input = screen.getByRole('textbox');
    const specialChars = '~!@#$%^&*()_+-={}[]|\\:";\'<>?,./"';
    await user.type(input, specialChars);
    
    expect(input).toHaveValue(specialChars);
  });

  it('handles unicode characters correctly', async () => {
    render(<TestWrapper><MessageInput /></TestWrapper>);
    
    const input = screen.getByRole('textbox');
    await user.type(input, 'Testing: αβγδε 中文测试 العربية');
    
    expect(input).toHaveValue('Testing: αβγδε 中文测试 العربية');
  });

  it('accepts code block formatting', async () => {
    render(<TestWrapper><MessageInput /></TestWrapper>);
    
    const input = screen.getByRole('textbox');
    const codeBlock = '```javascript\nconst test = "hello";\nconsole.log(test);\n```';
    await user.type(input, codeBlock);
    
    expect(input).toHaveValue(codeBlock);
  });

  it('processes markdown syntax correctly', async () => {
    render(<TestWrapper><MessageInput /></TestWrapper>);
    
    const input = screen.getByRole('textbox');
    const markdown = '# Header\n**bold** *italic* [link](url)';
    await user.type(input, markdown);
    
    expect(input).toHaveValue(markdown);
  });

  it('handles very long text input', async () => {
    render(<TestWrapper><MessageInput /></TestWrapper>);
    
    const input = screen.getByRole('textbox');
    const longText = 'A'.repeat(5000);
    
    await act(async () => {
      fireEvent.change(input, { target: { value: longText } });
    });
    
    expect(input).toHaveValue(longText);
  });

  it('trims whitespace on send', async () => {
    render(<TestWrapper><MessageInput /></TestWrapper>);
    
    const input = screen.getByRole('textbox');
    await user.type(input, '  hello world  ');
    await user.keyboard('{enter}');
    
    expect(mockMessageSending.handleSend).toHaveBeenCalledWith(
      expect.objectContaining({
        message: 'hello world'
      })
    );
  });
});

// ============================================
// Send Button State Management Tests
// ============================================

describe('MessageInput - Send Button States', () => {
  let user: ReturnType<typeof userEvent.setup>;
  let wsManager: WebSocketTestManager;
  
  beforeEach(() => {
    user = userEvent.setup();
    wsManager = new WebSocketTestManager();
    wsManager.setup();
    jest.clearAllMocks();
  });
  
  afterEach(() => {
    wsManager.cleanup();
  });

  it('disables send button when empty', () => {
    render(<TestWrapper><MessageInput /></TestWrapper>);
    
    const sendButton = screen.getByRole('button', { name: /send/i });
    expect(sendButton).toBeDisabled();
  });

  it('enables send button with text', async () => {
    render(<TestWrapper><MessageInput /></TestWrapper>);
    
    const input = screen.getByRole('textbox');
    await user.type(input, 'Test message');
    
    const sendButton = screen.getByRole('button', { name: /send/i });
    expect(sendButton).toBeEnabled();
  });

  it('disables send when processing', () => {
    mockUnifiedStore.isProcessing = true;
    render(<TestWrapper><MessageInput /></TestWrapper>);
    
    const sendButton = screen.getByRole('button', { name: /send/i });
    expect(sendButton).toBeDisabled();
    mockUnifiedStore.isProcessing = false;
  });

  it('disables send when not authenticated', () => {
    mockAuthStore.isAuthenticated = false;
    render(<TestWrapper><MessageInput /></TestWrapper>);
    
    const sendButton = screen.getByRole('button', { name: /send/i });
    expect(sendButton).toBeDisabled();
    mockAuthStore.isAuthenticated = true;
  });

  it('disables send when currently sending', () => {
    mockMessageSending.isSending = true;
    render(<TestWrapper><MessageInput /></TestWrapper>);
    
    const sendButton = screen.getByRole('button', { name: /send/i });
    expect(sendButton).toBeDisabled();
    mockMessageSending.isSending = false;
  });

  it('shows loading state during send', async () => {
    mockMessageSending.isSending = true;
    render(<TestWrapper><MessageInput /></TestWrapper>);
    
    const input = screen.getByRole('textbox');
    await user.type(input, 'Loading test');
    
    expect(input).toBeDisabled();
    mockMessageSending.isSending = false;
  });

  it('re-enables after send completion', async () => {
    render(<TestWrapper><MessageInput /></TestWrapper>);
    
    const input = screen.getByRole('textbox');
    await user.type(input, 'Complete test');
    await user.keyboard('{enter}');
    
    await waitFor(() => {
      expect(input).toBeEnabled();
    });
  });

  it('handles rapid button clicks gracefully', async () => {
    render(<TestWrapper><MessageInput /></TestWrapper>);
    
    const input = screen.getByRole('textbox');
    await user.type(input, 'Rapid click test');
    
    const sendButton = screen.getByRole('button', { name: /send/i });
    await user.click(sendButton);
    await user.click(sendButton);
    await user.click(sendButton);
    
    expect(mockMessageSending.handleSend).toHaveBeenCalledTimes(1);
  });
});

// ============================================
// Keyboard Shortcut Tests
// ============================================

describe('MessageInput - Keyboard Shortcuts', () => {
  let user: ReturnType<typeof userEvent.setup>;
  let wsManager: WebSocketTestManager;
  
  beforeEach(() => {
    user = userEvent.setup();
    wsManager = new WebSocketTestManager();
    wsManager.setup();
    jest.clearAllMocks();
  });
  
  afterEach(() => {
    wsManager.cleanup();
  });

  it('sends message on Enter key', async () => {
    render(<TestWrapper><MessageInput /></TestWrapper>);
    
    const input = screen.getByRole('textbox');
    await user.type(input, 'Enter test');
    await user.keyboard('{enter}');
    
    expect(mockMessageSending.handleSend).toHaveBeenCalled();
    expect(input).toHaveValue('');
  });

  it('adds newline on Shift+Enter', async () => {
    render(<TestWrapper><MessageInput /></TestWrapper>);
    
    const input = screen.getByRole('textbox');
    await user.type(input, 'Line 1{shift}{enter}Line 2');
    
    expect(input.value).toContain('\n');
    expect(mockMessageSending.handleSend).not.toHaveBeenCalled();
  });

  it('prevents sending empty messages with Enter', async () => {
    render(<TestWrapper><MessageInput /></TestWrapper>);
    
    const input = screen.getByRole('textbox');
    await user.click(input);
    await user.keyboard('{enter}');
    
    expect(mockMessageSending.handleSend).not.toHaveBeenCalled();
  });

  it('handles message history navigation', async () => {
    render(<TestWrapper><MessageInput /></TestWrapper>);
    
    const input = screen.getByRole('textbox');
    await user.click(input);
    await user.keyboard('{arrowup}');
    
    // Should navigate history when input is empty
    expect(input).toHaveFocus();
  });

  it('ignores history navigation with text', async () => {
    render(<TestWrapper><MessageInput /></TestWrapper>);
    
    const input = screen.getByRole('textbox');
    await user.type(input, 'Some text');
    await user.keyboard('{arrowup}');
    
    expect(input).toHaveValue('Some text');
  });

  it('supports keyboard navigation to send button', async () => {
    render(<TestWrapper><MessageInput /></TestWrapper>);
    
    const input = screen.getByRole('textbox');
    await user.type(input, 'Tab test');
    await user.keyboard('{tab}');
    
    const sendButton = screen.getByRole('button', { name: /send/i });
    expect(sendButton).toHaveFocus();
  });

  it('activates send button with Space when focused', async () => {
    render(<TestWrapper><MessageInput /></TestWrapper>);
    
    const input = screen.getByRole('textbox');
    await user.type(input, 'Space test');
    await user.keyboard('{tab}');
    await user.keyboard(' ');
    
    expect(mockMessageSending.handleSend).toHaveBeenCalled();
  });

  it('activates send button with Enter when focused', async () => {
    render(<TestWrapper><MessageInput /></TestWrapper>);
    
    const input = screen.getByRole('textbox');
    await user.type(input, 'Enter button test');
    await user.keyboard('{tab}');
    await user.keyboard('{enter}');
    
    expect(mockMessageSending.handleSend).toHaveBeenCalled();
  });
});

// ============================================
// Multiline and Auto-resize Tests
// ============================================

describe('MessageInput - Multiline and Auto-resize', () => {
  let user: ReturnType<typeof userEvent.setup>;
  let wsManager: WebSocketTestManager;
  
  beforeEach(() => {
    user = userEvent.setup();
    wsManager = new WebSocketTestManager();
    wsManager.setup();
    jest.clearAllMocks();
  });
  
  afterEach(() => {
    wsManager.cleanup();
  });

  it('expands for multiline content', async () => {
    render(<TestWrapper><MessageInput /></TestWrapper>);
    
    const input = screen.getByRole('textbox');
    const multilineText = 'Line 1\nLine 2\nLine 3\nLine 4';
    
    await act(async () => {
      fireEvent.change(input, { target: { value: multilineText } });
    });
    
    expect(input).toHaveValue(multilineText);
    expect(parseInt(input.style.height)).toBeGreaterThan(48);
  });

  it('maintains minimum height', () => {
    render(<TestWrapper><MessageInput /></TestWrapper>);
    
    const input = screen.getByRole('textbox');
    expect(input.style.minHeight).toBe('48px');
  });

  it('respects maximum height limit', async () => {
    render(<TestWrapper><MessageInput /></TestWrapper>);
    
    const input = screen.getByRole('textbox');
    const manyLines = Array(20).fill('Line').join('\n');
    
    await act(async () => {
      fireEvent.change(input, { target: { value: manyLines } });
    });
    
    expect(input).toHaveValue(manyLines);
    // Should not exceed max height
    const maxHeight = parseInt(input.style.maxHeight);
    expect(maxHeight).toBeLessThan(1000);
  });

  it('adjusts height dynamically on typing', async () => {
    render(<TestWrapper><MessageInput /></TestWrapper>);
    
    const input = screen.getByRole('textbox');
    const initialHeight = parseInt(input.style.height || '48');
    
    await user.type(input, 'Line 1{shift}{enter}Line 2{shift}{enter}Line 3');
    
    const newHeight = parseInt(input.style.height || '48');
    expect(newHeight).toBeGreaterThan(initialHeight);
  });

  it('shrinks when text is deleted', async () => {
    render(<TestWrapper><MessageInput /></TestWrapper>);
    
    const input = screen.getByRole('textbox');
    await user.type(input, 'Line 1{shift}{enter}Line 2{shift}{enter}Line 3');
    
    const expandedHeight = parseInt(input.style.height || '48');
    
    await user.clear(input);
    await user.type(input, 'Short');
    
    const shrunkHeight = parseInt(input.style.height || '48');
    expect(shrunkHeight).toBeLessThan(expandedHeight);
  });

  it('handles paste operations correctly', async () => {
    render(<TestWrapper><MessageInput /></TestWrapper>);
    
    const input = screen.getByRole('textbox');
    const pasteText = 'Pasted\nMultiline\nContent\nHere';
    
    await act(async () => {
      fireEvent.paste(input, {
        clipboardData: {
          getData: () => pasteText
        }
      });
    });
    
    expect(input).toHaveValue(pasteText);
  });

  it('preserves cursor position during resize', async () => {
    render(<TestWrapper><MessageInput /></TestWrapper>);
    
    const input = screen.getByRole('textbox');
    await user.type(input, 'Start');
    await user.keyboard('{shift}{enter}');
    await user.type(input, 'Middle');
    
    // Move cursor to middle
    input.setSelectionRange(5, 5);
    await user.type(input, ' INSERTED');
    
    expect(input.value).toContain('Start INSERTED');
  });

  it('handles rapid text changes smoothly', async () => {
    render(<TestWrapper><MessageInput /></TestWrapper>);
    
    const input = screen.getByRole('textbox');
    
    for (let i = 0; i < 10; i++) {
      await act(async () => {
        fireEvent.change(input, { 
          target: { value: `Line ${i}\n`.repeat(i + 1) }
        });
      });
    }
    
    expect(input.value).toContain('Line 9');
  });
});

// ============================================
// Error Handling and Edge Cases
// ============================================

describe('MessageInput - Error Handling', () => {
  let user: ReturnType<typeof userEvent.setup>;
  let wsManager: WebSocketTestManager;
  
  beforeEach(() => {
    user = userEvent.setup();
    wsManager = new WebSocketTestManager();
    wsManager.setup();
    jest.clearAllMocks();
  });
  
  afterEach(() => {
    wsManager.cleanup();
  });

  it('handles send failure gracefully', async () => {
    mockMessageSending.handleSend.mockRejectedValue(new Error('Send failed'));
    render(<TestWrapper><MessageInput /></TestWrapper>);
    
    const input = screen.getByRole('textbox');
    await user.type(input, 'Failure test');
    await user.keyboard('{enter}');
    
    // Should restore input value on failure
    await waitFor(() => {
      expect(input).toHaveValue('Failure test');
    });
  });

  it('shows error state appropriately', () => {
    mockMessageSending.sendError = 'Connection failed';
    render(<TestWrapper><MessageInput /></TestWrapper>);
    
    expect(screen.getByText(/connection failed/i)).toBeInTheDocument();
  });

  it('clears error on new input', async () => {
    mockMessageSending.sendError = 'Previous error';
    render(<TestWrapper><MessageInput /></TestWrapper>);
    
    const input = screen.getByRole('textbox');
    await user.type(input, 'Clear error test');
    
    expect(mockMessageSending.resetError).toHaveBeenCalled();
  });

  it('handles network disconnection state', () => {
    mockUnifiedStore.isProcessing = true;
    render(<TestWrapper><MessageInput /></TestWrapper>);
    
    const input = screen.getByRole('textbox');
    expect(input.placeholder).toContain('Connecting');
  });

  it('recovers from temporary failures', async () => {
    mockMessageSending.handleSend
      .mockRejectedValueOnce(new Error('Temporary error'))
      .mockResolvedValueOnce(undefined);
    
    render(<TestWrapper><MessageInput /></TestWrapper>);
    
    const input = screen.getByRole('textbox');
    await user.type(input, 'Recovery test');
    await user.keyboard('{enter}');
    
    // Should allow retry
    await user.keyboard('{enter}');
    expect(mockMessageSending.handleSend).toHaveBeenCalledTimes(2);
  });

  it('prevents XSS in input content', async () => {
    render(<TestWrapper><MessageInput /></TestWrapper>);
    
    const input = screen.getByRole('textbox');
    const xssAttempt = '<script>alert("xss")</script>';
    await user.type(input, xssAttempt);
    
    expect(input).toHaveValue(xssAttempt);
    // Content should be treated as plain text
  });

  it('handles extremely large input gracefully', async () => {
    render(<TestWrapper><MessageInput /></TestWrapper>);
    
    const input = screen.getByRole('textbox');
    const hugeText = 'A'.repeat(100000);
    
    await act(async () => {
      fireEvent.change(input, { target: { value: hugeText } });
    });
    
    expect(input).toHaveValue(hugeText);
    expect(screen.getByRole('button', { name: /send/i })).toBeEnabled();
  });

  it('maintains focus after failed send', async () => {
    mockMessageSending.handleSend.mockRejectedValue(new Error('Send failed'));
    render(<TestWrapper><MessageInput /></TestWrapper>);
    
    const input = screen.getByRole('textbox');
    await user.type(input, 'Focus test');
    await user.keyboard('{enter}');
    
    await waitFor(() => {
      expect(input).toHaveFocus();
    });
  });
});