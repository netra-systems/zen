import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MessageInput } from '@/components/chat/MessageInput';
import { useWebSocket } from '@/hooks/useWebSocket';
import { useUnifiedChatStore } from '@/store/unified-chat';
import { useThreadStore } from '@/store/threadStore';
import { useAuthStore } from '@/store/authStore';
import { generateUniqueId } from '@/lib/utils';
import { setupAntiHang, cleanupAntiHang } from '@/__tests__/utils/anti-hanging-test-utilities';

// Mock dependencies
jest.mock('@/hooks/useWebSocket', () => ({
  useWebSocket: jest.fn()
}));
jest.mock('@/store/unified-chat');
jest.mock('@/store/threadStore');
jest.mock('@/store/authStore');
jest.mock('@/lib/utils');
jest.mock('@/services/threadService');
jest.mock('@/services/threadRenameService');

describe('MessageInput - Focus Management and UI', () => {
    jest.setTimeout(10000);
  const mockSendMessage = jest.fn();
  const mockChatStore = {
    setProcessing: jest.fn(),
    addMessage: jest.fn()
  };
  const mockThreadStore = {
    setCurrentThread: jest.fn(),
    addThread: jest.fn()
  };

  beforeEach(() => {
    jest.clearAllMocks();
    
    // Setup default mocks
    (useWebSocket as jest.Mock).mockReturnValue({
      sendMessage: mockSendMessage,
    });
    
    jest.mocked(useUnifiedChatStore).mockReturnValue({
      setProcessing: mockChatStore.setProcessing,
      isProcessing: false,
      addMessage: mockChatStore.addMessage,
      activeThreadId: 'thread-1',
      setActiveThread: jest.fn(),
      addOptimisticMessage: jest.fn(),
      updateOptimisticMessage: jest.fn(),
    });
    
    jest.mocked(useThreadStore).mockReturnValue({
      currentThreadId: 'thread-1',
      setCurrentThread: mockThreadStore.setCurrentThread,
      addThread: mockThreadStore.addThread,
    });
    
    jest.mocked(useAuthStore).mockReturnValue({
      isAuthenticated: true,
    });
    
    (generateUniqueId as jest.Mock).mockImplementation((prefix) => `${prefix}-${Date.now()}`);
  });

  describe('Focus management', () => {
      jest.setTimeout(10000);
    it('should auto-focus on mount when authenticated', () => {
      render(<MessageInput />);
      const textarea = screen.getByPlaceholderText(/Type a message/i);
      
      expect(textarea).toHaveFocus();
    });

    it('should not auto-focus when not authenticated', () => {
      jest.mocked(useAuthStore).mockReturnValue({
        isAuthenticated: false,
      });
      
      render(<MessageInput />);
      const textarea = screen.getByPlaceholderText(/Please sign in/i);
      
      expect(textarea).not.toHaveFocus();
    });

    it('should maintain focus after sending message', async () => {
      render(<MessageInput />);
      const textarea = screen.getByPlaceholderText(/Type a message/i);
      
      await userEvent.type(textarea, 'Test message');
      await userEvent.type(textarea, '{enter}');
      
      await waitFor(() => {
        expect(textarea).toHaveFocus();
      });
    });
  });

  describe('UI state indicators', () => {
      jest.setTimeout(10000);
    it('should show appropriate placeholder when authenticated', () => {
      render(<MessageInput />);
      const textarea = screen.getByPlaceholderText(/Type a message/i);
      
      expect(textarea).toHaveAttribute('placeholder', expect.stringContaining('Type a message'));
    });

    it('should show sign-in prompt when not authenticated', () => {
      jest.mocked(useAuthStore).mockReturnValue({
        isAuthenticated: false,
      });
      
      render(<MessageInput />);
      const textarea = screen.getByPlaceholderText(/Please sign in/i);
      
      expect(textarea).toHaveAttribute('placeholder', 'Please sign in to send messages');
    });

    it('should show processing indicator when agent is thinking', () => {
      jest.mocked(useUnifiedChatStore).mockReturnValue({
        setProcessing: mockChatStore.setProcessing,
        isProcessing: true,
        addMessage: mockChatStore.addMessage,
        activeThreadId: 'thread-1',
        setActiveThread: jest.fn(),
        addOptimisticMessage: jest.fn(),
        updateOptimisticMessage: jest.fn(),
      });
      
      render(<MessageInput />);
      const textarea = screen.getByPlaceholderText(/Agent is thinking/i);
      
      expect(textarea).toHaveAttribute('placeholder', 'Agent is thinking...');
    });

    it('should show character limit warning in placeholder', async () => {
      render(<MessageInput />);
      const textarea = screen.getByPlaceholderText(/Type a message/i) as HTMLTextAreaElement;
      
      // Type over 90% of the limit
      const nearLimitMessage = 'a'.repeat(9100);
      fireEvent.change(textarea, { target: { value: nearLimitMessage } });
      
      // The placeholder changes dynamically when > 90% of limit
      await waitFor(() => {
        const currentPlaceholder = textarea.getAttribute('placeholder');
        expect(currentPlaceholder).toContain('characters remaining');
      });
    });
  });

  describe('Accessibility', () => {
      jest.setTimeout(10000);
    it('should have proper ARIA labels', () => {
      render(<MessageInput />);
      
      const textarea = screen.getByLabelText('Message input');
      const sendButton = screen.getByLabelText('Send message');
      const attachButton = screen.getByLabelText('Attach file');
      const voiceButton = screen.getByLabelText('Voice input');
      
      expect(textarea).toBeInTheDocument();
      expect(sendButton).toBeInTheDocument();
      expect(attachButton).toBeInTheDocument();
      expect(voiceButton).toBeInTheDocument();
    });

    it('should have ARIA describedby for character count', async () => {
      render(<MessageInput />);
      const textarea = screen.getByPlaceholderText(/Type a message/i) as HTMLTextAreaElement;
      
      // Type to trigger character count
      const longMessage = 'a'.repeat(8001);
      fireEvent.change(textarea, { target: { value: longMessage } });
      
      await waitFor(() => {
        expect(textarea).toHaveAttribute('aria-describedby', 'char-count');
        expect(screen.getByText(/8001\/10000/)).toHaveAttribute('id', 'char-count');
      });
    });

    it('should handle keyboard navigation properly', async () => {
      render(<MessageInput />);
      const textarea = screen.getByPlaceholderText(/Type a message/i);
      
      // Focus the textarea
      await userEvent.click(textarea);
      expect(textarea).toHaveFocus();
      
      // Tab should move focus away
      await userEvent.tab();
      expect(textarea).not.toHaveFocus();
      
      // Shift+Tab should bring focus back
      await userEvent.tab({ shift: true });
      expect(textarea).toHaveFocus();
    });
  });
});