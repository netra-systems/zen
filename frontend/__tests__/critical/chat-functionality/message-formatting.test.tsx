import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import '@testing-library/jest-dom';
import { setupAntiHang, cleanupAntiHang } from '@/__tests__/utils/anti-hanging-test-utilities';
 - Segment: Growth & Enterprise (Technical users with rich content needs)
 * - Business Goal: Enable rich content rendering for technical conversations
 * - Value Impact: Rich formatting crucial for 70% of technical AI interactions
 * - Revenue Impact: Technical users represent 40% of paid tier revenue
 * 
 * ARCHITECTURAL COMPLIANCE:
 * - File size: ≤300 lines (MANDATORY)
 * - Functions: ≤8 lines each (MANDATORY)
 * - Real message formatting components
 * - Real markdown rendering and display
 */

import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import '@testing-library/jest-dom';

// Real components and utilities
import { MessageItem } from '../../../components/chat/MessageItem';
import { FormattedMessageContent } from '../../../components/chat/FormattedMessageContent';
import { TestProviders } from '../../setup/test-providers';

// Formatting test utilities
import {
  setupFormattingTestEnvironment,
  cleanupFormattingResources,
  renderMessageWithContent,
  expectMarkdownRendered,
  expectCodeBlockRendered,
  expectLinkRendered,
  expectMentionRendered,
  expectListRendered,
  expectTableRendered,
  expectImageRendered,
  expectInlineCodeRendered
} from './test-helpers';

// Formatting data factories
import {
  createMarkdownMessage,
  createCodeBlockMessage,
  createInlineCodeMessage,
  createListMessage,
  createTableMessage,
  createLinkMessage,
  createMentionMessage,
  createImageMessage,
  createComplexFormattedMessage,
  createMixedContentMessage,
  createMaliciousContentMessage,
  createLongFormattedMessage
} from './test-data-factories';

describe('Message Formatting Core Functionality', () => {
    jest.setTimeout(10000);
  let user: ReturnType<typeof userEvent.setup>;

  beforeEach(async () => {
    user = userEvent.setup();
    await setupFormattingTestEnvironment();
  });

  afterEach(async () => {
    await cleanupFormattingResources();
  });

  describe('Markdown Basic Formatting', () => {
      jest.setTimeout(10000);
    test('renders bold and italic text correctly', async () => {
      const boldItalicMessage = createMarkdownMessage('**bold** and *italic* text');
      
      render(
        <TestProviders>
          <MessageItem message={boldItalicMessage} />
        </TestProviders>
      );

      await waitFor(() => {
        const boldElement = screen.getByText('bold');
        const italicElement = screen.getByText('italic');
        
        expect(boldElement).toHaveStyle('font-weight: bold');
        expect(italicElement).toHaveStyle('font-style: italic');
      });
    });

    test('renders headings with proper hierarchy', async () => {
      const headingMessage = createMarkdownMessage('# H1\n## H2\n### H3');
      
      render(
        <TestProviders>
          <MessageItem message={headingMessage} />
        </TestProviders>
      );

      await waitFor(() => {
        expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent('H1');
        expect(screen.getByRole('heading', { level: 2 })).toHaveTextContent('H2');
        expect(screen.getByRole('heading', { level: 3 })).toHaveTextContent('H3');
      });
    });

    test('renders blockquotes with proper styling', async () => {
      const quoteMessage = createMarkdownMessage('> This is a blockquote\n> with multiple lines');
      
      render(
        <TestProviders>
          <MessageItem message={quoteMessage} />
        </TestProviders>
      );

      await waitFor(() => {
        const blockquote = screen.getByRole('blockquote');
        expect(blockquote).toHaveTextContent('This is a blockquote with multiple lines');
        expect(blockquote).toHaveClass('border-l-4');
      });
    });

    test('renders strikethrough text correctly', async () => {
      const strikeMessage = createMarkdownMessage('~~strikethrough~~ text');
      
      render(
        <TestProviders>
          <MessageItem message={strikeMessage} />
        </TestProviders>
      );

      await waitFor(() => {
        const strikeElement = screen.getByText('strikethrough');
        expect(strikeElement).toHaveStyle('text-decoration: line-through');
      });
    });
  });

  describe('Code Block Rendering', () => {
      jest.setTimeout(10000);
    test('renders code blocks with syntax highlighting', async () => {
      const codeMessage = createCodeBlockMessage('javascript', 
        'function hello() {\n  console.log("Hello, world!");\n}'
      );
      
      render(
        <TestProviders>
          <MessageItem message={codeMessage} />
        </TestProviders>
      );

      await waitFor(() => {
        expectCodeBlockRendered('javascript');
        expect(screen.getByText('function')).toHaveClass('token');
        expect(screen.getByText('hello')).toBeInTheDocument();
      });
    });

    test('renders Python code with proper highlighting', async () => {
      const pythonCode = createCodeBlockMessage('python',
        'def hello():\n    print("Hello, world!")'
      );
      
      render(
        <TestProviders>
          <MessageItem message={pythonCode} />
        </TestProviders>
      );

      await waitFor(() => {
        expectCodeBlockRendered('python');
        expect(screen.getByText('def')).toHaveClass('keyword');
        expect(screen.getByText('print')).toBeInTheDocument();
      });
    });

    test('renders inline code with proper styling', async () => {
      const inlineCodeMessage = createInlineCodeMessage('Use `console.log()` for debugging');
      
      render(
        <TestProviders>
          <MessageItem message={inlineCodeMessage} />
        </TestProviders>
      );

      await waitFor(() => {
        expectInlineCodeRendered('console.log()');
        const codeElement = screen.getByText('console.log()');
        expect(codeElement).toHaveClass('bg-gray-100');
      });
    });

    test('handles code blocks without language specification', async () => {
      const noLangCode = createCodeBlockMessage('', 'raw code content');
      
      render(
        <TestProviders>
          <MessageItem message={noLangCode} />
        </TestProviders>
      );

      await waitFor(() => {
        const codeBlock = screen.getByText('raw code content');
        expect(codeBlock.closest('pre')).toBeInTheDocument();
      });
    });

    test('provides copy functionality for code blocks', async () => {
      const codeMessage = createCodeBlockMessage('bash', 'npm install react');
      
      render(
        <TestProviders>
          <MessageItem message={codeMessage} />
        </TestProviders>
      );

      await waitFor(() => {
        const copyButton = screen.getByLabelText(/copy.*code/i);
        expect(copyButton).toBeInTheDocument();
      });

      await user.click(screen.getByLabelText(/copy.*code/i));
      
      // Should show copied confirmation
      await waitFor(() => {
        expect(screen.getByText(/copied/i)).toBeInTheDocument();
      });
    });
  });

  describe('Links and Mentions', () => {
      jest.setTimeout(10000);
    test('renders external links with proper attributes', async () => {
      const linkMessage = createLinkMessage('https://netrasystems.ai', 'Netra AI Platform');
      
      render(
        <TestProviders>
          <MessageItem message={linkMessage} />
        </TestProviders>
      );

      await waitFor(() => {
        expectLinkRendered('https://netrasystems.ai');
        const link = screen.getByRole('link', { name: /netra ai platform/i });
        expect(link).toHaveAttribute('target', '_blank');
        expect(link).toHaveAttribute('rel', 'noopener noreferrer');
      });
    });

    test('renders user mentions with proper styling', async () => {
      const mentionMessage = createMentionMessage('@john_doe', 'user', 'user-123');
      
      render(
        <TestProviders>
          <MessageItem message={mentionMessage} />
        </TestProviders>
      );

      await waitFor(() => {
        expectMentionRendered('@john_doe');
        const mention = screen.getByText('@john_doe');
        expect(mention).toHaveClass('mention-user');
        expect(mention).toHaveAttribute('data-user-id', 'user-123');
      });
    });

    test('renders channel mentions differently from user mentions', async () => {
      const channelMention = createMentionMessage('#general', 'channel', 'channel-456');
      
      render(
        <TestProviders>
          <MessageItem message={channelMention} />
        </TestProviders>
      );

      await waitFor(() => {
        expectMentionRendered('#general');
        const mention = screen.getByText('#general');
        expect(mention).toHaveClass('mention-channel');
      });
    });

    test('auto-links URLs without markdown syntax', async () => {
      const autoLinkMessage = createMarkdownMessage('Check out https://example.com for more info');
      
      render(
        <TestProviders>
          <MessageItem message={autoLinkMessage} />
        </TestProviders>
      );

      await waitFor(() => {
        const autoLink = screen.getByRole('link');
        expect(autoLink).toHaveAttribute('href', 'https://example.com');
        expect(autoLink).toHaveTextContent('https://example.com');
      });
    });
  });

  describe('Lists and Tables', () => {
      jest.setTimeout(10000);
    test('renders unordered lists with proper structure', async () => {
      const unorderedList = createListMessage('unordered', ['Item 1', 'Item 2', 'Item 3']);
      
      render(
        <TestProviders>
          <MessageItem message={unorderedList} />
        </TestProviders>
      );

      await waitFor(() => {
        expectListRendered('unordered');
        expect(screen.getByRole('list')).toBeInTheDocument();
        expect(screen.getAllByRole('listitem')).toHaveLength(3);
      });
    });

    test('renders ordered lists with numbering', async () => {
      const orderedList = createListMessage('ordered', ['First', 'Second', 'Third']);
      
      render(
        <TestProviders>
          <MessageItem message={orderedList} />
        </TestProviders>
      );

      await waitFor(() => {
        expectListRendered('ordered');
        const list = screen.getByRole('list');
        expect(list.tagName).toBe('OL');
      });
    });

    test('renders tables with headers and data', async () => {
      const tableData = {
        headers: ['Name', 'Age', 'City'],
        rows: [
          ['John', '25', 'New York'],
          ['Jane', '30', 'London']
        ]
      };
      const tableMessage = createTableMessage(tableData);
      
      render(
        <TestProviders>
          <MessageItem message={tableMessage} />
        </TestProviders>
      );

      await waitFor(() => {
        expectTableRendered();
        expect(screen.getByRole('table')).toBeInTheDocument();
        expect(screen.getAllByRole('columnheader')).toHaveLength(3);
        expect(screen.getAllByRole('row')).toHaveLength(3); // Including header
      });
    });

    test('handles nested lists correctly', async () => {
      const nestedListMessage = createMarkdownMessage(
        '1. First item\n   - Sub item 1\n   - Sub item 2\n2. Second item'
      );
      
      render(
        <TestProviders>
          <MessageItem message={nestedListMessage} />
        </TestProviders>
      );

      await waitFor(() => {
        const outerList = screen.getByRole('list');
        const nestedList = outerList.querySelector('ul');
        expect(nestedList).toBeInTheDocument();
      });
    });
  });

  describe('Complex Mixed Content', () => {
      jest.setTimeout(10000);
    test('renders mixed content with multiple formatting types', async () => {
      const mixedMessage = createMixedContentMessage();
      
      render(
        <TestProviders>
          <MessageItem message={mixedMessage} />
        </TestProviders>
      );

      await waitFor(() => {
        // Should render all formatting types correctly
        expect(screen.getByRole('heading')).toBeInTheDocument();
        expect(screen.getByRole('list')).toBeInTheDocument();
        expect(screen.getByRole('link')).toBeInTheDocument();
        expect(screen.getByText(/console\.log/)).toBeInTheDocument();
      });
    });

    test('handles long formatted messages efficiently', async () => {
      const longMessage = createLongFormattedMessage(1000);
      const startTime = performance.now();
      
      render(
        <TestProviders>
          <MessageItem message={longMessage} />
        </TestProviders>
      );

      await waitFor(() => {
        expect(screen.getByText(/heading/i)).toBeInTheDocument();
      });

      const renderTime = performance.now() - startTime;
      expect(renderTime).toBeLessThan(500); // Should render within 500ms
    });

    test('sanitizes malicious content while preserving formatting', async () => {
      const maliciousMessage = createMaliciousContentMessage();
      
      render(
        <TestProviders>
          <MessageItem message={maliciousMessage} />
        </TestProviders>
      );

      await waitFor(() => {
        // Should render safe content only
        expect(screen.queryByText(/script/)).not.toBeInTheDocument();
        expect(screen.queryByRole('script')).not.toBeInTheDocument();
        // But should preserve valid markdown
        expect(screen.getByText(/safe content/i)).toBeInTheDocument();
      });
    });
  });

  describe('Performance and Accessibility', () => {
      jest.setTimeout(10000);
    test('provides proper ARIA labels for formatted content', async () => {
      const complexMessage = createComplexFormattedMessage();
      
      render(
        <TestProviders>
          <MessageItem message={complexMessage} />
        </TestProviders>
      );

      await waitFor(() => {
        const codeBlock = screen.getByRole('code');
        expect(codeBlock).toHaveAttribute('aria-label');
        
        const heading = screen.getByRole('heading');
        expect(heading).toBeInTheDocument();
        
        const list = screen.getByRole('list');
        expect(list).toBeInTheDocument();
      });
    });

    test('maintains formatting consistency across theme changes', async () => {
      const formattedMessage = createMarkdownMessage('**Bold** text with `code`');
      
      const { rerender } = render(
        <TestProviders theme="light">
          <MessageItem message={formattedMessage} />
        </TestProviders>
      );

      // Switch to dark theme
      rerender(
        <TestProviders theme="dark">
          <MessageItem message={formattedMessage} />
        </TestProviders>
      );

      await waitFor(() => {
        expect(screen.getByText('Bold')).toHaveStyle('font-weight: bold');
        expect(screen.getByText('code')).toHaveClass('bg-gray-100', 'dark:bg-gray-800');
      });
    });
  });
});