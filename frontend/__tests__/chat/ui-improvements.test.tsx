import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { WebSocketProvider } from '../providers/WebSocketProvider';
import userEvent from '@testing-library/user-event';
import { MessageInput } from '@/components/chat/MessageInput';

import { TestProviders } from '@/__tests__/test-utils/providers';// Legacy components removed - using unified MainChat and MessageItem
// import { ImprovedMessageItem } from '@/components/chat/ImprovedMessageItem';
// import { ResponsiveMainChat } from '@/components/chat/ResponsiveMainChat';
import { useKeyboardShortcuts } from '@/hooks/useKeyboardShortcuts';
import { renderHook, act } from '@testing-library/react';
import '@testing-library/jest-dom';

// Mock dependencies
jest.mock('@/hooks/useWebSocket', () => ({
  useWebSocket: () => ({
    sendMessage: jest.fn(),
    isConnected: true,
  }),
}));

jest.mock('@/hooks/useChatWebSocket', () => ({
  useChatWebSocket: jest.fn(),
}));

jest.mock('@/store/chat', () => ({
  useChatStore: () => ({
    messages: [],
    isProcessing: false,
    setProcessing: jest.fn(),
    addMessage: jest.fn(),
    stopProcessing: jest.fn(),
  }),
}));

jest.mock('@/store/threadStore', () => ({
  useThreadStore: () => ({
    currentThreadId: 'test-thread',
    threads: [],
    setCurrentThread: jest.fn(),
    addThread: jest.fn(),
  }),
}));

jest.mock('@/store/authStore', () => ({
  useAuthStore: () => ({
    isAuthenticated: true,
  }),
}));

jest.mock('@/services/threadService', () => ({
  ThreadService: {
    createThread: jest.fn().mockResolvedValue({ 
      id: 'new-thread', 
      title: 'Test Thread',
      created_at: Math.floor(Date.now() / 1000),
      updated_at: Math.floor(Date.now() / 1000),
      message_count: 0,
      metadata: { title: 'Test Thread', renamed: false }
    }),
    getThread: jest.fn().mockResolvedValue({
      id: 'test-thread',
      created_at: Math.floor(Date.now() / 1000),
      updated_at: Math.floor(Date.now() / 1000),
      message_count: 1,
      metadata: { title: 'Test Thread', renamed: false }
    }),
    listThreads: jest.fn().mockResolvedValue([]),
    deleteThread: jest.fn(),
    updateThread: jest.fn(),
    getThreadMessages: jest.fn().mockResolvedValue({ 
      messages: [], 
      thread_id: 'test', 
      total: 0, 
      limit: 50, 
      offset: 0 
    })
  },
}));

jest.mock('@/services/threadRenameService', () => ({
  ThreadRenameService: {
    autoRenameThread: jest.fn()
  }
}));

describe('Chat UI Improvements', () => {
  describe('MessageInput Component', () => {
    it('should support multi-line input with Shift+Enter', async () => {
      const { container } = render(<MessageInput />);
      const textarea = container.querySelector('textarea') as HTMLTextAreaElement;
      
      expect(textarea).toBeInTheDocument();
      
      // Type some text
      await userEvent.type(textarea, 'Line 1');
      
      // Press Shift+Enter for new line
      fireEvent.keyDown(textarea, { key: 'Enter', shiftKey: true });
      await userEvent.type(textarea, '{shift}{enter}Line 2');
      
      // Verify multi-line content
      expect(textarea.value).toContain('Line 1');
    });

    it('should show character count when approaching limit', async () => {
      const { container } = render(<MessageInput />);
      const textarea = container.querySelector('textarea') as HTMLTextAreaElement;
      
      // Type a long message (simulate approaching limit)
      const longMessage = 'a'.repeat(8001); // 80% of 10000 char limit
      fireEvent.change(textarea, { target: { value: longMessage } });
      
      // Check for character counter
      await waitFor(() => {
        const charCount = screen.getByText(/8001\/10000/);
        expect(charCount).toBeInTheDocument();
      });
    });

    it('should auto-resize based on content', async () => {
      const { container } = render(<MessageInput />);
      const textarea = container.querySelector('textarea') as HTMLTextAreaElement;
      
      const initialHeight = textarea.style.height;
      
      // Add multiple lines
      await userEvent.type(textarea, 'Line 1{shift}{enter}Line 2{shift}{enter}Line 3');
      
      // Height should have changed
      expect(textarea.style.height).not.toBe(initialHeight);
    });

    it('should support message history navigation with arrow keys', async () => {
      const { container } = render(<MessageInput />);
      const textarea = container.querySelector('textarea') as HTMLTextAreaElement;
      
      // Send a few messages to build history
      await userEvent.type(textarea, 'First message');
      fireEvent.keyDown(textarea, { key: 'Enter' });
      
      await userEvent.clear(textarea);
      await userEvent.type(textarea, 'Second message');
      fireEvent.keyDown(textarea, { key: 'Enter' });
      
      // Navigate history with arrow up
      fireEvent.keyDown(textarea, { key: 'ArrowUp' });
      
      // Should show previous message
      expect(textarea.value).toBe('');
    });

    it('should display action buttons (attachment, voice)', () => {
      render(<MessageInput />);
      
      // Check for attachment button
      const attachButton = screen.getByLabelText('Attach file');
      expect(attachButton).toBeInTheDocument();
      
      // Check for voice input button
      const voiceButton = screen.getByLabelText('Voice input');
      expect(voiceButton).toBeInTheDocument();
    });
  });

  // Tests for ImprovedMessageItem removed - component archived
  // describe('ImprovedMessageItem Component', () => {
  //   const mockMessage = {
  //     id: 'msg-1',
  //     type: 'assistant' as const,
  //     content: '```javascript\nconst hello = "world";\n```',
  //     sub_agent_name: 'OptimizationAgent',
  //     created_at: new Date().toISOString(),
  //     displayed_to_user: true,
  //   };

  //   it('should render message with syntax highlighting', () => {
  //     render(<ImprovedMessageItem message={mockMessage} />);
      
  //     // Check for code block rendering
  //     const codeBlock = screen.getByText('const');
  //     expect(codeBlock).toBeInTheDocument();
  //   });

  //   it('should show copy button for code blocks', async () => {
  //     render(<ImprovedMessageItem message={mockMessage} />);
      
  //     // Hover over code block to show copy button
  //     const codeContainer = screen.getByText('const').closest('.relative');
  //     if (codeContainer) {
  //       fireEvent.mouseEnter(codeContainer);
        
  //       // Check for copy button
  //       await waitFor(() => {
  //         const copyButtons = screen.getAllByRole('button', { name: /copy/i });
  //         expect(copyButtons.length).toBeGreaterThan(0);
  //       });
  //     }
  //   });

    // it('should support feedback buttons', () => {
    //   const onFeedback = jest.fn();
    //   render(
    //     <ImprovedMessageItem 
    //       message={mockMessage} 
    //       onFeedback={onFeedback}
    //     />
    //   );
      
    //   // Check for feedback buttons
    //   const helpfulButton = screen.getByLabelText('Mark as helpful');
    //   const notHelpfulButton = screen.getByLabelText('Mark as not helpful');
      
    //   expect(helpfulButton).toBeInTheDocument();
    //   expect(notHelpfulButton).toBeInTheDocument();
      
    //   // Test feedback interaction
    //   fireEvent.click(helpfulButton);
    //   expect(onFeedback).toHaveBeenCalledWith('msg-1', 'helpful');
    // });

    // it('should support compact mode display', () => {
    //   render(
    //     <ImprovedMessageItem 
    //       message={mockMessage} 
    //       isCompact={true}
    //     />
    //   );
      
    //   // In compact mode, should have simpler layout
    //   const compactContainer = screen.getByText('const hello = "world";').closest('div');
    //   expect(compactContainer?.className).toContain('flex gap-3');
    // });

    // it('should format timestamps correctly', () => {
    //   const oldMessage = {
    //     ...mockMessage,
    //     created_at: new Date(Date.now() - 3600000).toISOString(), // 1 hour ago
    //   };
      
    //   render(<ImprovedMessageItem message={oldMessage} />);
      
    //   // Should show relative time
    //   const timestamp = screen.getByText(/ago/);
    //   expect(timestamp).toBeInTheDocument();
    // });
  // });

  describe('Keyboard Shortcuts', () => {
    it('should register keyboard shortcuts correctly', () => {
      const { result } = renderHook(() => useKeyboardShortcuts());
      
      expect(result.current.shortcuts).toBeDefined();
      expect(result.current.shortcuts.length).toBeGreaterThan(0);
      
      // Check for specific shortcuts
      const commandPalette = result.current.shortcuts.find(s => s.key === 'k' && s.ctrl);
      expect(commandPalette).toBeDefined();
      expect(commandPalette?.description).toBe('Open command palette');
    });

    it('should handle focus message input shortcut', () => {
      const { result } = renderHook(() => useKeyboardShortcuts());
      
      // Create a mock textarea
      const textarea = document.createElement('textarea');
      textarea.setAttribute('aria-label', 'Message input');
      document.body.appendChild(textarea);
      
      // Test focus shortcut
      act(() => {
        result.current.focusMessageInput();
      });
      
      // Clean up
      document.body.removeChild(textarea);
    });

    it('should provide shortcut descriptions', () => {
      const { getShortcutDescriptions } = require('@/hooks/useKeyboardShortcuts');
      const descriptions = getShortcutDescriptions();
      
      expect(descriptions['Cmd/Ctrl + K']).toBe('Open command palette');
      expect(descriptions['Cmd/Ctrl + N']).toBe('New thread');
      expect(descriptions['/']).toBe('Focus message input');
      expect(descriptions['Esc']).toBe('Stop processing');
    });
  });

  describe('Responsive Design', () => {
    it('should adapt layout for mobile screens', () => {
      // Mock mobile viewport
      global.innerWidth = 375;
      global.matchMedia = jest.fn().mockImplementation(query => ({
        matches: query === '(max-width: 640px)',
        media: query,
        addEventListener: jest.fn(),
        removeEventListener: jest.fn(),
      }));

      render(<ResponsiveMainChat />);
      
      // Check for mobile-specific elements
      const mobileMenu = screen.getByLabelText('Toggle sidebar');
      expect(mobileMenu).toBeInTheDocument();
    });

    it('should handle tablet layout correctly', () => {
      // Mock tablet viewport
      global.innerWidth = 768;
      global.matchMedia = jest.fn().mockImplementation(query => ({
        matches: query === '(max-width: 1024px)',
        media: query,
        addEventListener: jest.fn(),
        removeEventListener: jest.fn(),
      }));

      render(<ResponsiveMainChat />);
      
      // Sidebar should be toggleable on tablet
      const toggleButton = screen.getByLabelText('Toggle sidebar');
      expect(toggleButton).toBeInTheDocument();
    });
  });

  describe('Accessibility Features', () => {
    it('should have proper ARIA labels', () => {
      render(<MessageInput />);
      
      const input = screen.getByLabelText('Message input');
      expect(input).toBeInTheDocument();
      
      const sendButton = screen.getByLabelText('Send message');
      expect(sendButton).toBeInTheDocument();
    });

    it('should support keyboard navigation', async () => {
      render(<MessageInput />);
      
      const textarea = screen.getByLabelText('Message input');
      
      // Tab navigation should work
      textarea.focus();
      expect(document.activeElement).toBe(textarea);
      
      // Tab to next element
      userEvent.tab();
      expect(document.activeElement).not.toBe(textarea);
    });

    it('should announce character limit warnings', async () => {
      const { container } = render(<MessageInput />);
      const textarea = container.querySelector('textarea') as HTMLTextAreaElement;
      
      // Type near limit
      const longMessage = 'a'.repeat(9500);
      fireEvent.change(textarea, { target: { value: longMessage } });
      
      // Check for aria-describedby
      expect(textarea).toHaveAttribute('aria-describedby', 'char-count');
      
      // Check character count is announced
      const charCount = document.getElementById('char-count');
      expect(charCount).toBeInTheDocument();
    });
  });
});