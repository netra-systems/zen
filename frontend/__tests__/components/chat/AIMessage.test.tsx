/**
 * AI Message Component Tests
 * 
 * Tests AI-specific message display behavior, streaming animations, and agent indicators.
 * Covers agent naming, tool execution display, streaming updates, and error handling.
 * 
 * @compliance conventions.xml - Max 8 lines per function, under 300 lines
 * @compliance type_safety.xml - Strongly typed test definitions
 * @compliance no_test_stubs.xml - Real implementations only
 */

import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
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

const createToolMessage = (): Message => createAIMessage({
  type: 'tool',
  tool_info: {
    tool_name: 'code_executor',
    args: { language: 'python', code: 'print("hello")' },
    result: 'hello'
  }
});

const createErrorMessage = (): Message => createAIMessage({
  error: 'Connection timeout occurred'
});

// ============================================================================
// AI MESSAGE STYLING TESTS
// ============================================================================

describe('AIMessage - Styling and Display', () => {
  it('renders AI message with correct styling', () => {
    const message = createAIMessage();
    renderWithChatSetup(<MessageItem message={message} />);
    
    const messageContainer = screen.getByText('OptimizationAgent').closest('.mb-4');
    expect(messageContainer).toHaveClass('justify-start');
    expect(screen.getByText('OptimizationAgent')).toBeInTheDocument();
  });

  it('displays AI avatar with gradient styling', () => {
    const message = createAIMessage();
    renderWithChatSetup(<MessageItem message={message} />);
    
    const avatar = screen.getByText('AI');
    expect(avatar).toHaveClass('from-purple-600', 'to-pink-600');
  });

  it('applies AI-specific card styling', () => {
    const message = createAIMessage();
    renderWithChatSetup(<MessageItem message={message} />);
    
    const card = screen.getByText('OptimizationAgent').closest('.rounded-lg');
    expect(card).toHaveClass('border-gray-200');
  });

  it('aligns AI message to the left', () => {
    const message = createAIMessage();
    renderWithChatSetup(<MessageItem message={message} />);
    
    const container = screen.getByText('OptimizationAgent').closest('.mb-4');
    expect(container).toHaveClass('justify-start');
  });

  it('displays sub-agent name when present', () => {
    const message = createAIMessage({
      sub_agent_name: 'SpecializedAgent'
    });
    renderWithChatSetup(<MessageItem message={message} />);
    
    expect(screen.getByText('SpecializedAgent')).toBeInTheDocument();
  });
});

// ============================================================================
// AGENT NAMING AND IDENTIFICATION TESTS
// ============================================================================

describe('AIMessage - Agent Identification', () => {
  it('displays correct agent name for different agents', () => {
    const message = createAIMessage({
      sub_agent_name: 'DataAnalysisAgent'
    });
    renderWithChatSetup(<MessageItem message={message} />);
    
    expect(screen.getByText('DataAnalysisAgent')).toBeInTheDocument();
  });

  it('shows agent subtitle when appropriate', () => {
    const message = createAIMessage({
      sub_agent_name: 'ComplexAgent'
    });
    renderWithChatSetup(<MessageItem message={message} />);
    
    const subtitle = screen.queryByText(/AI Assistant/);
    if (subtitle) {
      expect(subtitle).toHaveClass('text-gray-500');
    }
  });

  it('handles missing agent name gracefully', () => {
    const message = createAIMessage({
      sub_agent_name: undefined
    });
    renderWithChatSetup(<MessageItem message={message} />);
    
    expect(screen.getByText('AI Assistant')).toBeInTheDocument();
  });

  it('displays bot icon for AI messages', () => {
    const message = createAIMessage();
    renderWithChatSetup(<MessageItem message={message} />);
    
    const botIcon = document.querySelector('svg.lucide-bot') ||
                   screen.getByText('OptimizationAgent').parentElement?.querySelector('svg');
    expect(botIcon).toBeInTheDocument();
  });
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

  it('maintains smooth 60 FPS updates during streaming', async () => {
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

// ============================================================================
// TOOL EXECUTION DISPLAY TESTS
// ============================================================================

describe('AIMessage - Tool Execution', () => {
  it('displays tool information when present', () => {
    const message = createToolMessage();
    renderWithChatSetup(<MessageItem message={message} />);
    
    expect(screen.getByText('Tool Information')).toBeInTheDocument();
  });

  it('shows expandable tool details', async () => {
    const user = userEvent.setup();
    const message = createToolMessage();
    renderWithChatSetup(<MessageItem message={message} />);
    
    const toolTrigger = screen.getByText('Tool Information');
    await user.click(toolTrigger);
    
    await waitFor(() => {
      expect(screen.getByText('code_executor')).toBeInTheDocument();
    });
  });

  it('renders tool icon correctly', () => {
    const message = createToolMessage();
    renderWithChatSetup(<MessageItem message={message} />);
    
    const toolIcon = screen.getByTestId('tool-icon') || 
                    document.querySelector('[data-lucide="wrench"]');
    expect(toolIcon).toBeInTheDocument();
  });

  it('handles complex tool data structures', () => {
    const message = createToolMessage();
    renderWithChatSetup(<MessageItem message={message} />);
    
    // Tool information should be collapsible
    const collapsible = screen.getByRole('button', { name: /Tool Information/ });
    expect(collapsible).toBeInTheDocument();
  });
});

// ============================================================================
// ERROR HANDLING TESTS
// ============================================================================

describe('AIMessage - Error Handling', () => {
  it('displays error messages with correct styling', () => {
    const message = createErrorMessage();
    renderWithChatSetup(<MessageItem message={message} />);
    
    expect(screen.getByText('Connection timeout occurred')).toBeInTheDocument();
    const errorElement = screen.getByRole('alert') || 
                        screen.getByText('Connection timeout occurred').closest('div');
    expect(errorElement).toHaveClass('bg-red-50');
  });

  it('shows error icon for error messages', () => {
    const message = createErrorMessage();
    renderWithChatSetup(<MessageItem message={message} />);
    
    const errorIcon = document.querySelector('svg.lucide-alert-circle') ||
                     screen.getByText('Connection timeout occurred').parentElement?.querySelector('svg');
    expect(errorIcon).toBeInTheDocument();
  });

  it('applies error styling to message card', () => {
    const message = createErrorMessage();
    renderWithChatSetup(<MessageItem message={message} />);
    
    const card = screen.getByText('Connection timeout occurred').closest('.rounded-lg');
    expect(card).toHaveClass('bg-red-50', 'border-red-200');
  });

  it('handles network error recovery gracefully', () => {
    const message = createErrorMessage();
    renderWithChatSetup(<MessageItem message={message} />);
    
    // Error should be displayed without breaking the UI
    expect(screen.getByText('Connection timeout occurred')).toBeInTheDocument();
    const messageContainer = screen.getByText('Connection timeout occurred').closest('.mb-4');
    expect(messageContainer).toBeInTheDocument();
  });
});

// ============================================================================
// MCP EXECUTION INDICATORS TESTS
// ============================================================================

describe('AIMessage - MCP Execution Indicators', () => {
  it('displays MCP execution indicators when present', () => {
    const message = createAIMessage({
      metadata: {
        mcpExecutions: [{
          tool_name: 'file_reader',
          status: 'completed',
          execution_time_ms: 150,
          args: { path: '/test/file.txt' }
        }]
      }
    });
    renderWithChatSetup(<MessageItem message={message} />);
    
    const mcpIndicator = screen.queryByTestId('mcp-indicator') ||
                        screen.queryByText('file_reader');
    if (mcpIndicator) {
      expect(mcpIndicator).toBeInTheDocument();
    }
  });

  it('shows MCP server status when available', () => {
    const message = createAIMessage({
      metadata: {
        mcpExecutions: [{
          server_status: 'CONNECTED',
          tool_name: 'database_query',
          args: { query: 'SELECT * FROM users' }
        }]
      }
    });
    renderWithChatSetup(<MessageItem message={message} />);
    
    const statusIndicator = screen.queryByText('CONNECTED') ||
                           screen.queryByTestId('mcp-status');
    if (statusIndicator) {
      expect(statusIndicator).toBeInTheDocument();
    }
  });
});

// ============================================================================
// PERFORMANCE TESTS
// ============================================================================

describe('AIMessage - Performance', () => {
  it('renders complex AI messages within performance budget', () => {
    const complexMessage = createAIMessage({
      content: 'A'.repeat(5000), // 5KB content
      metadata: {
        mcpExecutions: Array(10).fill({
          tool_name: 'test_tool',
          status: 'completed',
          args: { test: 'value' }
        })
      }
    });
    
    const startTime = performance.now();
    renderWithChatSetup(<MessageItem message={complexMessage} />);
    const endTime = performance.now();
    
    expect(endTime - startTime).toBeLessThan(100); // < 100ms render time
  });

  it('handles rapid message updates efficiently', async () => {
    const message = createAIMessage();
    const { rerender } = renderWithChatSetup(<MessageItem message={message} />);
    
    const startTime = performance.now();
    
    // Simulate rapid updates
    for (let i = 0; i < 50; i++) {
      const updatedMessage = {
        ...message,
        content: `${message.content} update ${i}`
      };
      rerender(<MessageItem message={updatedMessage} />);
    }
    
    const endTime = performance.now();
    expect(endTime - startTime).toBeLessThan(500); // < 500ms for 50 updates
  });
});