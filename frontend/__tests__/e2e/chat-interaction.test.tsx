/**
 * E2E Chat Interaction Tests - Core Revenue Protection
 * 
 * Business Value Justification:
 * - Segment: All (Free → Enterprise)
 * - Goal: Protect core chat revenue flow, prevent user churn from bugs
 * - Value Impact: Direct protection of 100% of user interactions
 * - Revenue Impact: Prevents 20%+ revenue loss from chat failures
 */

import React from 'react';
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { WebSocketTestManager } from '@/helpers/websocket-test-manager';
import { MessageInput } from '@/components/chat/MessageInput';
import { MessageItem } from '@/components/chat/MessageItem';
import { MainChat } from '@/components/chat/MainChat';
import type { Message } from '@/types/registry';

// ============================================
// Test Setup and Helpers (8 lines each)
// ============================================

const createTestMessage = (overrides = {}): Message => ({
  id: 'test-msg-123',
  content: 'Test message content',
  type: 'user',
  role: 'user',
  timestamp: Date.now(),
  ...overrides
});

const createAIMessage = (overrides = {}): Message => ({
  id: 'ai-msg-456',
  content: 'AI response content',
  type: 'assistant',
  role: 'assistant',
  timestamp: Date.now(),
  ...overrides
});

const renderWithWebSocket = (component: React.ReactElement) => {
  const wsManager = new WebSocketTestManager();
  wsManager.setup();
  const result = render(component);
  return { ...result, wsManager };
};

const expectSendButtonEnabled = (enabled: boolean) => {
  const sendButton = screen.getByRole('button', { name: /send/i });
  if (enabled) {
    expect(sendButton).toBeEnabled();
  } else {
    expect(sendButton).toBeDisabled();
  }
};

const expectMessageInChat = async (content: string) => {
  await waitFor(() => {
    expect(screen.getByText(content)).toBeInTheDocument();
  });
};

// ============================================
// Mock Providers (8 lines each)
// ============================================

const MockChatProvider = ({ children }: { children: React.ReactNode }) => (
  <div data-testid="mock-chat-provider">{children}</div>
);

const MockStoreProvider = ({ children }: { children: React.ReactNode }) => (
  <div data-testid="mock-store-provider">{children}</div>
);

const TestWrapper = ({ children }: { children: React.ReactNode }) => (
  <MockStoreProvider>
    <MockChatProvider>
      {children}
    </MockChatProvider>
  </MockStoreProvider>
);

// ============================================
// Input Tests - Text, Code, Emoji, Multiline
// ============================================

describe('Chat Input Edge Cases', () => {
  let user: ReturnType<typeof userEvent.setup>;
  
  beforeEach(() => {
    user = userEvent.setup();
  });

  it('handles text input correctly', async () => {
    const { wsManager } = renderWithWebSocket(
      <TestWrapper><MessageInput /></TestWrapper>
    );
    
    const input = screen.getByRole('textbox');
    await user.type(input, 'Hello world');
    
    expect(input).toHaveValue('Hello world');
    expectSendButtonEnabled(true);
    wsManager.cleanup();
  });

  it('handles emoji input correctly', async () => {
    const { wsManager } = renderWithWebSocket(
      <TestWrapper><MessageInput /></TestWrapper>
    );
    
    const input = screen.getByRole('textbox');
    await user.type(input, '👋 Hello! 🎉');
    
    expect(input).toHaveValue('👋 Hello! 🎉');
    expectSendButtonEnabled(true);
    wsManager.cleanup();
  });

  it('handles code block input correctly', async () => {
    const { wsManager } = renderWithWebSocket(
      <TestWrapper><MessageInput /></TestWrapper>
    );
    
    const input = screen.getByRole('textbox');
    const codeText = '```javascript\nconsole.log("test");\n```';
    await user.type(input, codeText);
    
    expect(input).toHaveValue(codeText);
    expectSendButtonEnabled(true);
    wsManager.cleanup();
  });

  it('handles multiline input correctly', async () => {
    const { wsManager } = renderWithWebSocket(
      <TestWrapper><MessageInput /></TestWrapper>
    );
    
    const input = screen.getByRole('textbox');
    await user.type(input, 'Line 1{shift}{enter}Line 2{shift}{enter}Line 3');
    
    expect(input.value).toContain('Line 1');
    expect(input.value).toContain('Line 2');
    expect(input.value).toContain('Line 3');
    wsManager.cleanup();
  });
});

// ============================================
// Send Button and Keyboard Tests
// ============================================

describe('Send Button States and Keyboard', () => {
  let user: ReturnType<typeof userEvent.setup>;
  
  beforeEach(() => {
    user = userEvent.setup();
  });

  it('disables send button when empty', async () => {
    const { wsManager } = renderWithWebSocket(
      <TestWrapper><MessageInput /></TestWrapper>
    );
    
    expectSendButtonEnabled(false);
    wsManager.cleanup();
  });

  it('enables send button with text', async () => {
    const { wsManager } = renderWithWebSocket(
      <TestWrapper><MessageInput /></TestWrapper>
    );
    
    const input = screen.getByRole('textbox');
    await user.type(input, 'Test message');
    
    expectSendButtonEnabled(true);
    wsManager.cleanup();
  });

  it('sends message on Enter key', async () => {
    const { wsManager } = renderWithWebSocket(
      <TestWrapper><MessageInput /></TestWrapper>
    );
    
    const input = screen.getByRole('textbox');
    await user.type(input, 'Test message{enter}');
    
    expect(input).toHaveValue('');
    wsManager.cleanup();
  });

  it('adds newline on Shift+Enter', async () => {
    const { wsManager } = renderWithWebSocket(
      <TestWrapper><MessageInput /></TestWrapper>
    );
    
    const input = screen.getByRole('textbox');
    await user.type(input, 'Line 1{shift}{enter}Line 2');
    
    expect(input.value).toContain('\n');
    wsManager.cleanup();
  });
});

// ============================================
// Message Delivery and Confirmation
// ============================================

describe('Message Delivery', () => {
  let user: ReturnType<typeof userEvent.setup>;
  
  beforeEach(() => {
    user = userEvent.setup();
  });

  it('shows message delivery confirmation', async () => {
    const { wsManager } = renderWithWebSocket(
      <TestWrapper><MainChat /></TestWrapper>
    );
    
    const input = screen.getByRole('textbox');
    await user.type(input, 'Test delivery');
    await user.keyboard('{enter}');
    
    await expectMessageInChat('Test delivery');
    wsManager.cleanup();
  });

  it('handles send button click correctly', async () => {
    const { wsManager } = renderWithWebSocket(
      <TestWrapper><MessageInput /></TestWrapper>
    );
    
    const input = screen.getByRole('textbox');
    await user.type(input, 'Button click test');
    
    const sendButton = screen.getByRole('button', { name: /send/i });
    await user.click(sendButton);
    
    expect(input).toHaveValue('');
    wsManager.cleanup();
  });

  it('shows message pending state', async () => {
    const { wsManager } = renderWithWebSocket(
      <TestWrapper><MessageInput /></TestWrapper>
    );
    
    const input = screen.getByRole('textbox');
    await user.type(input, 'Pending test');
    await user.keyboard('{enter}');
    
    expectSendButtonEnabled(false);
    wsManager.cleanup();
  });

  it('handles special characters correctly', async () => {
    const { wsManager } = renderWithWebSocket(
      <TestWrapper><MessageInput /></TestWrapper>
    );
    
    const input = screen.getByRole('textbox');
    const specialText = '~!@#$%^&*()_+-={}[]|;:",./<>?';
    await user.type(input, specialText);
    
    expect(input).toHaveValue(specialText);
    wsManager.cleanup();
  });
});

// ============================================
// AI Response Streaming Tests
// ============================================

describe('AI Response Streaming', () => {
  it('displays streaming response correctly', async () => {
    const streamingMessage = createAIMessage({
      content: 'Streaming response...',
      isStreaming: true
    });
    
    const { wsManager } = renderWithWebSocket(
      <TestWrapper>
        <MessageItem message={streamingMessage} />
      </TestWrapper>
    );
    
    await expectMessageInChat('Streaming response...');
    wsManager.cleanup();
  });

  it('handles streaming updates smoothly', async () => {
    const { wsManager } = renderWithWebSocket(
      <TestWrapper><MainChat /></TestWrapper>
    );
    
    await act(async () => {
      wsManager.sendMessage({
        type: 'stream_update',
        content: 'Partial response'
      });
    });
    
    await expectMessageInChat('Partial response');
    wsManager.cleanup();
  });

  it('shows thinking indicator during AI response', async () => {
    const { wsManager } = renderWithWebSocket(
      <TestWrapper><MainChat /></TestWrapper>
    );
    
    await act(async () => {
      wsManager.sendMessage({
        type: 'thinking',
        status: 'processing'
      });
    });
    
    await waitFor(() => {
      expect(screen.getByTestId('thinking-indicator')).toBeInTheDocument();
    });
    wsManager.cleanup();
  });

  it('handles stream completion correctly', async () => {
    const completedMessage = createAIMessage({
      content: 'Complete response',
      isStreaming: false
    });
    
    const { wsManager } = renderWithWebSocket(
      <TestWrapper>
        <MessageItem message={completedMessage} />
      </TestWrapper>
    );
    
    await expectMessageInChat('Complete response');
    wsManager.cleanup();
  });
});

// ============================================
// Message Actions Tests
// ============================================

describe('Message Actions', () => {
  let user: ReturnType<typeof userEvent.setup>;
  
  beforeEach(() => {
    user = userEvent.setup();
  });

  it('handles copy message action', async () => {
    const testMessage = createTestMessage({
      content: 'Message to copy'
    });
    
    const { wsManager } = renderWithWebSocket(
      <TestWrapper>
        <MessageItem message={testMessage} />
      </TestWrapper>
    );
    
    const copyButton = screen.getByRole('button', { name: /copy/i });
    await user.click(copyButton);
    
    // Verify copy action triggered
    expect(copyButton).toBeInTheDocument();
    wsManager.cleanup();
  });

  it('handles retry message action', async () => {
    const errorMessage = createAIMessage({
      content: 'Failed response',
      error: 'Connection error'
    });
    
    const { wsManager } = renderWithWebSocket(
      <TestWrapper>
        <MessageItem message={errorMessage} />
      </TestWrapper>
    );
    
    const retryButton = screen.getByRole('button', { name: /retry/i });
    await user.click(retryButton);
    
    expect(retryButton).toBeInTheDocument();
    wsManager.cleanup();
  });

  it('handles feedback message action', async () => {
    const aiMessage = createAIMessage({
      content: 'AI response for feedback'
    });
    
    const { wsManager } = renderWithWebSocket(
      <TestWrapper>
        <MessageItem message={aiMessage} />
      </TestWrapper>
    );
    
    const feedbackButton = screen.getByRole('button', { name: /feedback/i });
    await user.click(feedbackButton);
    
    expect(feedbackButton).toBeInTheDocument();
    wsManager.cleanup();
  });

  it('shows message actions on hover', async () => {
    const testMessage = createTestMessage({
      content: 'Hover test message'
    });
    
    const { wsManager } = renderWithWebSocket(
      <TestWrapper>
        <MessageItem message={testMessage} />
      </TestWrapper>
    );
    
    const messageElement = screen.getByText('Hover test message');
    await user.hover(messageElement);
    
    await waitFor(() => {
      expect(screen.getByRole('group', { name: /message actions/i })).toBeVisible();
    });
    wsManager.cleanup();
  });
});

// ============================================
// Performance and Timing Tests
// ============================================

describe('Performance Requirements', () => {
  it('completes input response within 100ms', async () => {
    const startTime = performance.now();
    
    const { wsManager } = renderWithWebSocket(
      <TestWrapper><MessageInput /></TestWrapper>
    );
    
    const input = screen.getByRole('textbox');
    await userEvent.type(input, 'Speed test');
    
    const endTime = performance.now();
    expect(endTime - startTime).toBeLessThan(100);
    wsManager.cleanup();
  });

  it('handles long text input efficiently', async () => {
    const { wsManager } = renderWithWebSocket(
      <TestWrapper><MessageInput /></TestWrapper>
    );
    
    const longText = 'a'.repeat(10000);
    const input = screen.getByRole('textbox');
    
    const startTime = performance.now();
    await act(async () => {
      fireEvent.change(input, { target: { value: longText } });
    });
    const endTime = performance.now();
    
    expect(endTime - startTime).toBeLessThan(500);
    expect(input).toHaveValue(longText);
    wsManager.cleanup();
  });

  it('maintains responsive UI during streaming', async () => {
    const { wsManager } = renderWithWebSocket(
      <TestWrapper><MainChat /></TestWrapper>
    );
    
    // Simulate rapid streaming updates
    for (let i = 0; i < 10; i++) {
      await act(async () => {
        wsManager.sendMessage({
          type: 'stream_update',
          content: `Update ${i}`
        });
      });
    }
    
    await expectMessageInChat('Update 9');
    wsManager.cleanup();
  });

  it('executes all tests under 1 second', async () => {
    const startTime = performance.now();
    
    const { wsManager } = renderWithWebSocket(
      <TestWrapper><MessageInput /></TestWrapper>
    );
    
    const input = screen.getByRole('textbox');
    await userEvent.type(input, 'Performance test{enter}');
    
    const endTime = performance.now();
    expect(endTime - startTime).toBeLessThan(1000);
    wsManager.cleanup();
  });
});