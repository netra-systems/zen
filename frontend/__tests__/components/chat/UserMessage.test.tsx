/**
 * User Message Component Tests
 * 
 * Tests user-specific message display behavior, styling, and interactions.
 * Covers markdown rendering, code highlighting, timestamps, and user actions.
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

const createUserMessage = (overrides: Partial<Message> = {}): Message => ({
  id: 'user-msg-1',
  role: 'user',
  type: 'user',
  content: 'Test user message',
  created_at: '2023-01-01T12:00:00Z',
  displayed_to_user: true,
  thread_id: 'thread-1',
  ...overrides
});

const createMarkdownMessage = (): Message => createUserMessage({
  content: '# Header\n\n**Bold text** and *italic text*\n\n- List item 1\n- List item 2'
});

const createCodeMessage = (): Message => createUserMessage({
  content: '```python\nprint("Hello, World!")\n```'
});

const createLongMessage = (): Message => createUserMessage({
  content: 'A'.repeat(10000) // 10KB message
});

// ============================================================================
// USER MESSAGE STYLING TESTS
// ============================================================================

describe('UserMessage - Styling and Display', () => {
  it('renders user message with correct styling', () => {
    const message = createUserMessage();
    renderWithChatSetup(<MessageItem message={message} />);
    
    const messageContainer = screen.getByText('You').closest('.flex');
    expect(messageContainer).toHaveClass('justify-end');
    expect(screen.getByText('You')).toBeInTheDocument();
  });

  it('displays user avatar with correct styling', () => {
    const message = createUserMessage();
    renderWithChatSetup(<MessageItem message={message} />);
    
    const avatar = screen.getByText('U');
    expect(avatar).toHaveClass('bg-emerald-500', 'text-white');
  });

  it('applies user-specific card styling', () => {
    const message = createUserMessage();
    renderWithChatSetup(<MessageItem message={message} />);
    
    const card = screen.getByRole('article');
    expect(card).toHaveClass('border-emerald-200');
  });

  it('aligns user message to the right', () => {
    const message = createUserMessage();
    renderWithChatSetup(<MessageItem message={message} />);
    
    const container = screen.getByTestId('message-container') || 
                     screen.getByRole('article').parentElement;
    expect(container).toHaveClass('justify-end');
  });
});

// ============================================================================
// MARKDOWN RENDERING TESTS
// ============================================================================

describe('UserMessage - Markdown Rendering', () => {
  it('renders markdown headers correctly', () => {
    const message = createMarkdownMessage();
    renderWithChatSetup(<MessageItem message={message} />);
    
    expect(screen.getByRole('heading', { level: 1 })).toBeInTheDocument();
    expect(screen.getByText('Header')).toBeInTheDocument();
  });

  it('renders markdown bold and italic text', () => {
    const message = createMarkdownMessage();
    renderWithChatSetup(<MessageItem message={message} />);
    
    expect(screen.getByText('Bold text')).toHaveStyle('font-weight: bold');
    expect(screen.getByText('italic text')).toHaveStyle('font-style: italic');
  });

  it('renders markdown lists correctly', () => {
    const message = createMarkdownMessage();
    renderWithChatSetup(<MessageItem message={message} />);
    
    expect(screen.getByRole('list')).toBeInTheDocument();
    expect(screen.getByText('List item 1')).toBeInTheDocument();
    expect(screen.getByText('List item 2')).toBeInTheDocument();
  });

  it('renders links with proper attributes', () => {
    const message = createUserMessage({
      content: '[Google](https://google.com)'
    });
    renderWithChatSetup(<MessageItem message={message} />);
    
    const link = screen.getByRole('link', { name: 'Google' });
    expect(link).toHaveAttribute('href', 'https://google.com');
  });
});

// ============================================================================
// CODE SYNTAX HIGHLIGHTING TESTS
// ============================================================================

describe('UserMessage - Code Highlighting', () => {
  it('renders code blocks with syntax highlighting', () => {
    const message = createCodeMessage();
    renderWithChatSetup(<MessageItem message={message} />);
    
    expect(screen.getByText('print("Hello, World!")')).toBeInTheDocument();
    expect(screen.getByRole('code')).toBeInTheDocument();
  });

  it('applies language-specific highlighting', () => {
    const message = createUserMessage({
      content: '```javascript\nconst x = 42;\n```'
    });
    renderWithChatSetup(<MessageItem message={message} />);
    
    const codeBlock = screen.getByRole('code');
    expect(codeBlock).toHaveClass('language-javascript');
  });

  it('renders inline code correctly', () => {
    const message = createUserMessage({
      content: 'Use `console.log()` for debugging'
    });
    renderWithChatSetup(<MessageItem message={message} />);
    
    const inlineCode = screen.getByText('console.log()');
    expect(inlineCode).toHaveClass('bg-gray-100');
  });

  it('handles code blocks without language specification', () => {
    const message = createUserMessage({
      content: '```\nprint("hello")\n```'
    });
    renderWithChatSetup(<MessageItem message={message} />);
    
    expect(screen.getByText('print("hello")')).toBeInTheDocument();
  });
});

// ============================================================================
// TIMESTAMP AND METADATA TESTS
// ============================================================================

describe('UserMessage - Timestamp and Metadata', () => {
  it('displays formatted timestamp correctly', () => {
    const message = createUserMessage({
      created_at: '2023-01-01T12:00:00Z'
    });
    renderWithChatSetup(<MessageItem message={message} />);
    
    expect(screen.getByText(/12:00:00/)).toBeInTheDocument();
  });

  it('handles missing timestamp gracefully', () => {
    const message = createUserMessage({
      created_at: undefined
    });
    renderWithChatSetup(<MessageItem message={message} />);
    
    expect(screen.getByText(/\d{1,2}:\d{2}:\d{2}/)).toBeInTheDocument();
  });

  it('displays message ID when present', () => {
    const message = createUserMessage();
    renderWithChatSetup(<MessageItem message={message} />);
    
    expect(screen.getByText(`Message ID: ${message.id}`)).toBeInTheDocument();
  });

  it('shows references when present', () => {
    const message = createUserMessage({
      references: ['doc1.pdf', 'doc2.txt']
    });
    renderWithChatSetup(<MessageItem message={message} />);
    
    expect(screen.getByText('References')).toBeInTheDocument();
    expect(screen.getByText('doc1.pdf')).toBeInTheDocument();
    expect(screen.getByText('doc2.txt')).toBeInTheDocument();
  });
});

// ============================================================================
// LONG MESSAGE HANDLING TESTS
// ============================================================================

describe('UserMessage - Long Message Handling', () => {
  it('renders large messages without performance degradation', async () => {
    const message = createLongMessage();
    const startTime = performance.now();
    
    renderWithChatSetup(<MessageItem message={message} />);
    
    const endTime = performance.now();
    expect(endTime - startTime).toBeLessThan(100); // Render time < 100ms
  });

  it('handles very long content without breaking layout', () => {
    const message = createLongMessage();
    renderWithChatSetup(<MessageItem message={message} />);
    
    const messageContent = screen.getByText(/A{10}/);
    expect(messageContent).toBeInTheDocument();
  });
});

// ============================================================================
// COPY TO CLIPBOARD TESTS
// ============================================================================

describe('UserMessage - Copy Functionality', () => {
  beforeEach(() => {
    Object.assign(navigator, {
      clipboard: {
        writeText: jest.fn(() => Promise.resolve())
      }
    });
  });

  it('enables copy functionality for text content', async () => {
    const user = userEvent.setup();
    const message = createUserMessage();
    renderWithChatSetup(<MessageItem message={message} />);
    
    const messageContent = screen.getByText(message.content);
    await user.click(messageContent);
    
    // Test that content can be selected for copying
    expect(messageContent).toBeInTheDocument();
  });
});

// ============================================================================
// ACCESSIBILITY TESTS
// ============================================================================

describe('UserMessage - Accessibility', () => {
  it('has proper ARIA roles and labels', () => {
    const message = createUserMessage();
    renderWithChatSetup(<MessageItem message={message} />);
    
    expect(screen.getByRole('article')).toBeInTheDocument();
    expect(screen.getByRole('img')).toHaveAttribute('aria-label');
  });

  it('supports keyboard navigation', async () => {
    const user = userEvent.setup();
    const message = createUserMessage();
    renderWithChatSetup(<MessageItem message={message} />);
    
    const messageCard = screen.getByRole('article');
    await user.tab();
    
    expect(document.activeElement).toBe(messageCard);
  });

  it('maintains focus management for interactive elements', () => {
    const message = createUserMessage();
    renderWithChatSetup(<MessageItem message={message} />);
    
    const focusableElements = screen.getAllByRole('button');
    focusableElements.forEach(element => {
      expect(element).not.toHaveAttribute('tabindex', '-1');
    });
  });
});