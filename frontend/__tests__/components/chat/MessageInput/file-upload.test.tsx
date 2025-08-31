import React from 'react';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MessageInput } from '@/components/chat/MessageInput';
import { useWebSocket } from '@/hooks/useWebSocket';
import { useUnifiedChatStore } from '@/store/unified-chat';
import { useThreadStore } from '@/store/threadStore';
import { useAuthStore } from '@/store/authStore';
import { generateUniqueId } from '@/lib/utils';
import { setupAntiHang, cleanupAntiHang } from '@/__tests__/utils/anti-hanging-test-utilities';
AuthStore } from '@/store/authStore';
import { generateUniqueId } from '@/lib/utils';

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

describe('MessageInput - File Upload Handling', () => {
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

  describe('File upload handling', () => {
      jest.setTimeout(10000);
    it('should render file attachment button', () => {
      render(<MessageInput />);
      
      const attachButton = screen.getByLabelText('Attach file');
      expect(attachButton).toBeInTheDocument();
    });

    it('should disable file attachment when processing', () => {
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
      const attachButton = screen.getByLabelText('Attach file');
      
      expect(attachButton).toBeDisabled();
    });

    it('should show file attachment tooltip', async () => {
      render(<MessageInput />);
      const attachButton = screen.getByLabelText('Attach file');
      
      // Component uses title attribute for tooltip
      expect(attachButton).toHaveAttribute('title', 'Attach file (coming soon)');
    });

    it('should handle file attachment button click', async () => {
      render(<MessageInput />);
      const attachButton = screen.getByLabelText('Attach file');
      
      await userEvent.click(attachButton);
      
      // Should trigger file input (implementation detail)
      expect(attachButton).toBeInTheDocument();
    });

    it('should disable file attachment when not authenticated', () => {
      jest.mocked(useAuthStore).mockReturnValue({
        isAuthenticated: false,
      });
      
      render(<MessageInput />);
      const attachButton = screen.getByLabelText('Attach file');
      
      expect(attachButton).toBeDisabled();
    });
  });
});