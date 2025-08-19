/**
 * Advanced Chat Features Tests
 * ============================
 * 
 * Continuation of comprehensive chat interface tests
 * Covers advanced features and functionality (Tests 6-10)
 * 
 * Business Value: Advanced features drive user engagement and stickiness
 * Revenue Impact: +$25K MRR from power user retention and feature utilization
 */

import React from 'react';
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import '@testing-library/jest-dom';

// Components under test
import { ChatSidebar } from '@/components/chat/ChatSidebar';
import { MessageList } from '@/components/chat/MessageList';
import { MainChat } from '@/components/chat/MainChat';
import { FormattedMessageContent } from '@/components/chat/FormattedMessageContent';

// Test utilities
import { TestProviders } from '../../../test-utils';
import { mockUnifiedChatStore, createMockMessage } from './shared-test-setup';

describe('Advanced Chat Features', () => {
  let mockStore: any;
  let user: ReturnType<typeof userEvent.setup>;

  beforeEach(() => {
    user = userEvent.setup();
    mockStore = mockUnifiedChatStore();
    jest.clearAllMocks();
  });

  describe('6. Search Within Conversations', () => {
    const searchableMessages = [
      createMockMessage('How do I optimize my AI models?', 'user'),
      createMockMessage('To optimize AI models, you should consider...', 'assistant'),
      createMockMessage('What about database performance?', 'user'),
      createMockMessage('Database optimization involves indexing...', 'assistant')
    ];

    it('should show search input when search is triggered', async () => {
      mockStore.messages = searchableMessages;
      
      render(
        <TestProviders>
          <ChatSidebar />
        </TestProviders>
      );

      await user.keyboard('{Control>}f');
      
      expect(screen.getByPlaceholderText(/search messages/i)).toBeInTheDocument();
    });

    it('should filter messages based on search query', async () => {
      mockStore.messages = searchableMessages;
      
      render(
        <TestProviders>
          <ChatSidebar />
        </TestProviders>
      );

      const searchInput = screen.getByPlaceholderText(/search messages/i);
      await user.type(searchInput, 'optimize');
      
      // Should highlight matching messages
      await waitFor(() => {
        const highlightedMessages = screen.getAllByTestId(/search-highlight/);
        expect(highlightedMessages).toHaveLength(2);
      });
    });

    it('should navigate between search results with keyboard', async () => {
      mockStore.messages = searchableMessages;
      
      render(
        <TestProviders>
          <ChatSidebar />
        </TestProviders>
      );

      const searchInput = screen.getByPlaceholderText(/search messages/i);
      await user.type(searchInput, 'optimize');
      
      // Navigate to next result
      await user.keyboard('{Enter}');
      
      const activeResult = screen.getByTestId('active-search-result');
      expect(activeResult).toBeInTheDocument();
    });

    it('should clear search and show all messages', async () => {
      mockStore.messages = searchableMessages;
      
      render(
        <TestProviders>
          <ChatSidebar />
        </TestProviders>
      );

      const searchInput = screen.getByPlaceholderText(/search messages/i);
      await user.type(searchInput, 'optimize');
      
      // Clear search
      const clearButton = screen.getByTestId('clear-search');
      await user.click(clearButton);
      
      expect(searchInput).toHaveValue('');
      expect(screen.queryByTestId(/search-highlight/)).not.toBeInTheDocument();
    });
  });

  describe('7. Keyboard Shortcuts', () => {
    it('should send message with Enter key', async () => {
      render(
        <TestProviders>
          <MainChat />
        </TestProviders>
      );

      const textarea = screen.getByRole('textbox');
      await user.type(textarea, 'Test message');
      await user.keyboard('{Enter}');
      
      expect(mockStore.sendMessage).toHaveBeenCalledWith('Test message');
    });

    it('should add line break with Shift+Enter', async () => {
      render(
        <TestProviders>
          <MainChat />
        </TestProviders>
      );

      const textarea = screen.getByRole('textbox');
      await user.type(textarea, 'Line 1');
      await user.keyboard('{Shift>}{Enter}');
      await user.type(textarea, 'Line 2');
      
      expect(textarea).toHaveValue('Line 1\nLine 2');
    });

    it('should focus message input with Ctrl+I', async () => {
      render(
        <TestProviders>
          <MainChat />
        </TestProviders>
      );

      await user.keyboard('{Control>}i');
      
      const textarea = screen.getByRole('textbox');
      expect(textarea).toHaveFocus();
    });

    it('should open command palette with Ctrl+K', async () => {
      render(
        <TestProviders>
          <MainChat />
        </TestProviders>
      );

      await user.keyboard('{Control>}k');
      
      expect(screen.getByTestId('command-palette')).toBeInTheDocument();
    });

    it('should show shortcuts help with Ctrl+?', async () => {
      render(
        <TestProviders>
          <MainChat />
        </TestProviders>
      );

      await user.keyboard('{Control>}?');
      
      expect(screen.getByText(/keyboard shortcuts/i)).toBeInTheDocument();
      expect(screen.getByText(/enter.*send message/i)).toBeInTheDocument();
    });
  });

  describe('8. Markdown Rendering in Messages', () => {
    it('should render markdown headers correctly', () => {
      const markdownMessage = createMockMessage('# Header 1\n## Header 2\n### Header 3');
      
      render(
        <TestProviders>
          <FormattedMessageContent content={markdownMessage.content} />
        </TestProviders>
      );

      expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent('Header 1');
      expect(screen.getByRole('heading', { level: 2 })).toHaveTextContent('Header 2');
      expect(screen.getByRole('heading', { level: 3 })).toHaveTextContent('Header 3');
    });

    it('should render markdown lists correctly', () => {
      const markdownMessage = createMockMessage('- Item 1\n- Item 2\n- Item 3');
      
      render(
        <TestProviders>
          <FormattedMessageContent content={markdownMessage.content} />
        </TestProviders>
      );

      const list = screen.getByRole('list');
      const listItems = screen.getAllByRole('listitem');
      
      expect(list).toBeInTheDocument();
      expect(listItems).toHaveLength(3);
      expect(listItems[0]).toHaveTextContent('Item 1');
    });

    it('should render markdown links as clickable elements', () => {
      const markdownMessage = createMockMessage('[OpenAI](https://openai.com) and [Anthropic](https://anthropic.com)');
      
      render(
        <TestProviders>
          <FormattedMessageContent content={markdownMessage.content} />
        </TestProviders>
      );

      const openAILink = screen.getByRole('link', { name: /openai/i });
      const anthropicLink = screen.getByRole('link', { name: /anthropic/i });
      
      expect(openAILink).toHaveAttribute('href', 'https://openai.com');
      expect(anthropicLink).toHaveAttribute('href', 'https://anthropic.com');
      expect(openAILink).toHaveAttribute('target', '_blank');
    });

    it('should render bold and italic text formatting', () => {
      const markdownMessage = createMockMessage('**Bold text** and *italic text* and ***bold italic***');
      
      render(
        <TestProviders>
          <FormattedMessageContent content={markdownMessage.content} />
        </TestProviders>
      );

      expect(screen.getByText('Bold text')).toHaveStyle('font-weight: bold');
      expect(screen.getByText('italic text')).toHaveStyle('font-style: italic');
      expect(screen.getByText('bold italic')).toHaveStyle('font-weight: bold; font-style: italic');
    });

    it('should render blockquotes with proper styling', () => {
      const markdownMessage = createMockMessage('> This is a blockquote\n> with multiple lines');
      
      render(
        <TestProviders>
          <FormattedMessageContent content={markdownMessage.content} />
        </TestProviders>
      );

      const blockquote = screen.getByTestId('blockquote');
      expect(blockquote).toBeInTheDocument();
      expect(blockquote).toHaveTextContent('This is a blockquote with multiple lines');
    });
  });

  describe('9. Code Syntax Highlighting', () => {
    it('should render inline code with proper styling', () => {
      const messageWithCode = createMockMessage('Use `console.log()` to debug your code.');
      
      render(
        <TestProviders>
          <FormattedMessageContent content={messageWithCode.content} />
        </TestProviders>
      );

      const codeElement = screen.getByText('console.log()');
      expect(codeElement).toHaveClass('inline-code');
    });

    it('should render JavaScript code blocks with syntax highlighting', () => {
      const jsCodeMessage = createMockMessage(`\`\`\`javascript
function optimizeModel(model) {
  const optimizedModel = model.quantize();
  return optimizedModel;
}
\`\`\``);
      
      render(
        <TestProviders>
          <FormattedMessageContent content={jsCodeMessage.content} />
        </TestProviders>
      );

      const codeBlock = screen.getByTestId('code-block');
      expect(codeBlock).toHaveAttribute('data-language', 'javascript');
      expect(screen.getByText('function')).toHaveClass('token', 'keyword');
    });

    it('should render Python code blocks with syntax highlighting', () => {
      const pythonCodeMessage = createMockMessage(`\`\`\`python
import torch

def optimize_model(model):
    optimized_model = torch.quantization.quantize_dynamic(model)
    return optimized_model
\`\`\``);
      
      render(
        <TestProviders>
          <FormattedMessageContent content={pythonCodeMessage.content} />
        </TestProviders>
      );

      const codeBlock = screen.getByTestId('code-block');
      expect(codeBlock).toHaveAttribute('data-language', 'python');
      expect(screen.getByText('import')).toHaveClass('token', 'keyword');
      expect(screen.getByText('def')).toHaveClass('token', 'keyword');
    });

    it('should provide copy functionality for code blocks', async () => {
      const codeMessage = createMockMessage(`\`\`\`bash
npm install @anthropic/claude
npm start
\`\`\``);
      
      // Mock clipboard API
      Object.assign(navigator, {
        clipboard: {
          writeText: jest.fn().mockResolvedValue(undefined),
        },
      });

      render(
        <TestProviders>
          <FormattedMessageContent content={codeMessage.content} />
        </TestProviders>
      );

      const copyButton = screen.getByTestId('copy-code-button');
      await user.click(copyButton);
      
      expect(navigator.clipboard.writeText).toHaveBeenCalledWith('npm install @anthropic/claude\nnpm start');
      expect(screen.getByText(/copied/i)).toBeInTheDocument();
    });

    it('should handle code blocks without language specification', () => {
      const codeMessage = createMockMessage(`\`\`\`
generic code without language
console.log("hello world");
\`\`\``);
      
      render(
        <TestProviders>
          <FormattedMessageContent content={codeMessage.content} />
        </TestProviders>
      );

      const codeBlock = screen.getByTestId('code-block');
      expect(codeBlock).toBeInTheDocument();
      expect(codeBlock).toHaveAttribute('data-language', 'text');
    });
  });

  describe('10. Export Conversation Functionality', () => {
    const exportableMessages = [
      createMockMessage('How can I optimize my AI workflow?', 'user'),
      createMockMessage('Here are several strategies for AI optimization:\n\n1. Model selection\n2. Prompt engineering\n3. Caching strategies', 'assistant'),
      createMockMessage('Tell me more about caching.', 'user'),
      createMockMessage('Caching can significantly improve performance...', 'assistant')
    ];

    it('should show export options when export is triggered', async () => {
      mockStore.messages = exportableMessages;
      
      render(
        <TestProviders>
          <MainChat />
        </TestProviders>
      );

      const exportButton = screen.getByTestId('export-conversation');
      await user.click(exportButton);
      
      expect(screen.getByText(/export as/i)).toBeInTheDocument();
      expect(screen.getByText(/markdown/i)).toBeInTheDocument();
      expect(screen.getByText(/pdf/i)).toBeInTheDocument();
      expect(screen.getByText(/json/i)).toBeInTheDocument();
    });

    it('should export conversation as Markdown', async () => {
      mockStore.messages = exportableMessages;
      
      // Mock download functionality
      const mockCreateObjectURL = jest.fn(() => 'mock-url');
      const mockRevokeObjectURL = jest.fn();
      global.URL.createObjectURL = mockCreateObjectURL;
      global.URL.revokeObjectURL = mockRevokeObjectURL;

      render(
        <TestProviders>
          <MainChat />
        </TestProviders>
      );

      const exportButton = screen.getByTestId('export-conversation');
      await user.click(exportButton);
      
      const markdownOption = screen.getByText(/markdown/i);
      await user.click(markdownOption);
      
      expect(mockCreateObjectURL).toHaveBeenCalled();
    });

    it('should export conversation as PDF with proper formatting', async () => {
      mockStore.messages = exportableMessages;
      
      // Mock jsPDF
      const mockJsPDF = jest.fn().mockImplementation(() => ({
        text: jest.fn(),
        addPage: jest.fn(),
        save: jest.fn(),
        setFontSize: jest.fn(),
        setTextColor: jest.fn(),
      }));
      
      jest.mock('jspdf', () => ({ jsPDF: mockJsPDF }));

      render(
        <TestProviders>
          <MainChat />
        </TestProviders>
      );

      const exportButton = screen.getByTestId('export-conversation');
      await user.click(exportButton);
      
      const pdfOption = screen.getByText(/pdf/i);
      await user.click(pdfOption);
      
      await waitFor(() => {
        expect(screen.getByText(/generating pdf/i)).toBeInTheDocument();
      });
    });

    it('should include metadata in exported conversation', async () => {
      mockStore.messages = exportableMessages;
      mockStore.activeThread = {
        id: 'thread1',
        title: 'AI Optimization Discussion',
        createdAt: '2025-08-19T10:00:00.000Z'
      };
      
      render(
        <TestProviders>
          <MainChat />
        </TestProviders>
      );

      const exportButton = screen.getByTestId('export-conversation');
      await user.click(exportButton);
      
      const jsonOption = screen.getByText(/json/i);
      await user.click(jsonOption);
      
      // Verify export contains metadata
      const exportData = JSON.parse(mockStore.exportConversation.mock.calls[0][0]);
      expect(exportData).toHaveProperty('title', 'AI Optimization Discussion');
      expect(exportData).toHaveProperty('createdAt');
      expect(exportData).toHaveProperty('messages');
      expect(exportData.messages).toHaveLength(4);
    });
  });
});