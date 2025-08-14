/**
 * MessageInput Voice Input Tests
 * Tests for voice input functionality
 */

import React from 'react';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MessageInput } from '@/components/chat/MessageInput';
import { useWebSocket } from '@/hooks/useWebSocket';
import { useChatStore } from '@/store/chat';
import { useThreadStore } from '@/store/threadStore';
import { useAuthStore } from '@/store/authStore';
import { generateUniqueId } from '@/lib/utils';

// Mock dependencies
jest.mock('@/hooks/useWebSocket', () => ({
  useWebSocket: jest.fn()
}));
jest.mock('@/store/chat');
jest.mock('@/store/threadStore');
jest.mock('@/store/authStore');
jest.mock('@/lib/utils');

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
    
    (useChatStore as jest.Mock).mockReturnValue({
      setProcessing: mockChatStore.setProcessing,
      isProcessing: false,
      addMessage: mockChatStore.addMessage,
    });
    
    (useThreadStore as jest.Mock).mockReturnValue({
      currentThreadId: 'thread-1',
      setCurrentThread: mockThreadStore.setCurrentThread,
      addThread: mockThreadStore.addThread,
    });
    
    (useAuthStore as jest.Mock).mockReturnValue({
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
      (useChatStore as jest.Mock).mockReturnValue({
        setProcessing: mockChatStore.setProcessing,
        isProcessing: true,
        addMessage: mockChatStore.addMessage,
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
      (useAuthStore as jest.Mock).mockReturnValue({
        isAuthenticated: false,
      });
      
      render(<MessageInput />);
      const voiceButton = screen.getByLabelText('Voice input');
      
      expect(voiceButton).toBeDisabled();
    });
  });
});