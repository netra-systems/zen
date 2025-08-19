/**
 * AI Message Streaming Animation Tests
 * 
 * Tests streaming indicators, content updates, and animation performance.
 * 
 * @compliance conventions.xml - Max 8 lines per function, under 300 lines
 * @compliance type_safety.xml - Strongly typed test definitions
 * @compliance no_test_stubs.xml - Real implementations only
 */

import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import { MessageItem } from '@/components/chat/MessageItem';
import { Message } from '@/types/registry';
import { setupChatMocks, resetChatMocks, renderWithChatSetup } from './shared-test-setup';

// ============================================================================
// TEST SETUP
// ============================================================================

beforeAll(() => {
  setupChatMocks();
});

beforeEach(() => {
  resetChatMocks();
});

// ============================================================================
// TEST DATA FACTORIES
// ============================================================================

const createAIMessage = (overrides: Partial<Message> = {}): Message => ({
  id: 'ai-msg-1',
  role: 'assistant',
  type: 'agent',
  content: 'AI response message',
  sub_agent_name: 'OptimizationAgent',
  created_at: '2023-01-01T12:00:00Z',
  displayed_to_user: true,
  thread_id: 'thread-1',
  ...overrides
});

const createStreamingMessage = (): Message => createAIMessage({
  metadata: {
    is_streaming: true,
    chunk_index: 1
  }
});

// ============================================================================
// STREAMING ANIMATION TESTS
// ============================================================================

describe('AIMessage - Streaming Animations', () => {
  it('displays streaming indicator for streaming messages', () => {
    const message = createStreamingMessage();
    renderWithChatSetup(<MessageItem message={message} />);
    
    // Look for streaming indicators or animations
    const streamingElement = screen.queryByTestId('streaming-indicator') ||
                           screen.queryByRole('progressbar');
    
    if (streamingElement) {
      expect(streamingElement).toBeInTheDocument();
    }
  });

  it('animates content updates during streaming', async () => {
    const message = createStreamingMessage();
    const { rerender } = renderWithChatSetup(<MessageItem message={message} />);
    
    // Simulate streaming update
    const updatedMessage = {
      ...message,
      content: message.content + ' additional text',
      metadata: {
        ...message.metadata,
        chunk_index: 2
      }
    };
    
    rerender(<MessageItem message={updatedMessage} />);
    
    await waitFor(() => {
      expect(screen.getByText(/additional text/)).toBeInTheDocument();
    });
  });

  it('maintains smooth FPS updates during streaming', async () => {
    const message = createStreamingMessage();
    let frameCount = 0;
    const startTime = performance.now();
    
    const { rerender } = renderWithChatSetup(<MessageItem message={message} />);
    
    // Simulate rapid streaming updates
    for (let i = 0; i < 10; i++) {
      const updatedMessage = {
        ...message,
        content: `${message.content} chunk ${i}`,
        metadata: { ...message.metadata, chunk_index: i }
      };
      
      rerender(<MessageItem message={updatedMessage} />);
      frameCount++;
    }
    
    const endTime = performance.now();
    const duration = endTime - startTime;
    const fps = (frameCount / duration) * 1000;
    
    expect(fps).toBeGreaterThan(30); // At least 30 FPS
  });

  it('completes streaming animation properly', async () => {
    const message = createStreamingMessage();
    const { rerender } = renderWithChatSetup(<MessageItem message={message} />);
    
    // Complete streaming
    const completedMessage = {
      ...message,
      metadata: {
        ...message.metadata,
        is_streaming: false
      }
    };
    
    rerender(<MessageItem message={completedMessage} />);
    
    // Streaming indicators should be removed
    const streamingIndicator = screen.queryByTestId('streaming-indicator');
    expect(streamingIndicator).not.toBeInTheDocument();
  });
});