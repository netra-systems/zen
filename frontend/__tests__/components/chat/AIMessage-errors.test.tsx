/**
 * AI Message Error Handling Tests
 * 
 * Tests error message display, styling, and recovery behavior.
 * 
 * @compliance conventions.xml - Max 8 lines per function, under 300 lines
 * @compliance type_safety.xml - Strongly typed test definitions
 * @compliance no_test_stubs.xml - Real implementations only
 */

import React from 'react';
import { render, screen } from '@testing-library/react';
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

const createErrorMessage = (): Message => createAIMessage({
  error: 'Connection timeout occurred'
});

// ============================================================================
// ERROR HANDLING TESTS
// ============================================================================

describe('AIMessage - Error Handling', () => {
  it('displays error messages with correct styling', () => {
    const message = createErrorMessage();
    renderWithChatSetup(<MessageItem message={message} />);
    
    expect(screen.getByText('Connection timeout occurred')).toBeInTheDocument();
    const errorElement = screen.getByText('Connection timeout occurred').closest('div');
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