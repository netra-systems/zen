/**
 * MessageInput Voice Input Tests
 * Tests for voice input functionality
 */

import React from 'react';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MessageInput } from '@/components/chat/MessageInput';
import { useWebSocket } from '@/hooks/useWebSocket';
import { useUnifiedChatStore } from '@/store/unified-chat';
import { useThreadStore } from '@/store/threadStore';
import { useAuthStore } from '@/store/authStore';
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

describe('MessageInput - Voice Input and Emoji Features', () => {
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

  describe('Voice input and emoji features', () => {
    it('should render voice input button', () => {
      render(<MessageInput />);
      
      const voiceButton = screen.getByLabelText('Voice input');
      expect(voiceButton).toBeInTheDocument();
    });

    it('should disable voice input when processing', () => {
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
      const voiceButton = screen.getByLabelText('Voice input');
      
      expect(voiceButton).toBeDisabled();
    });

    it('should show voice input tooltip', async () => {
      render(<MessageInput />);
      const voiceButton = screen.getByLabelText('Voice input');
      
      // Component uses title attribute for tooltip
      expect(voiceButton).toHaveAttribute('title', 'Voice input (coming soon)');
    });

    it('should handle voice button click', async () => {
      render(<MessageInput />);
      const voiceButton = screen.getByLabelText('Voice input');
      
      await userEvent.click(voiceButton);
      
      // Voice input not implemented yet
      expect(voiceButton).toBeInTheDocument();
    });

    it('should disable voice input when not authenticated', () => {
      jest.mocked(useAuthStore).mockReturnValue({
        isAuthenticated: false,
      });
      
      render(<MessageInput />);
      const voiceButton = screen.getByLabelText('Voice input');
      
      expect(voiceButton).toBeDisabled();
    });
  });
});