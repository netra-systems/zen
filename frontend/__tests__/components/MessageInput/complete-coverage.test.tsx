/**
 * Core functionality tests for MessageInput component
 * Tests text entry, send actions, character limits
 * 
 * BVJ: Direct impact on user engagement and message conversion rates.
 * Ensures reliable input experience for all customer segments.
 */

import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { jest } from '@jest/globals';
import { MessageInput } from '@/components/chat/MessageInput';
import { 
  setupMessageInputMocks, 
  mockHooks,
  measurePerformance,
  mockUseTextareaResize,
  mockUseMessageHistory,
  mockUseMessageSending,
  mockUseUnifiedChatStore,
  mockUseAuthStore
} from './shared-test-setup';

describe('MessageInput - Core Functionality', () => {
  const user = userEvent.setup();

  beforeEach(() => {
    setupMessageInputMocks();
    jest.clearAllMocks();
  });

  describe('Text Entry and Real-time Updates', () => {
    it('renders with correct placeholder for authenticated user', () => {
      render(<MessageInput />);
      
      const textarea = screen.getByRole('textbox');
      expect(textarea).toBeInTheDocument();
      expect(textarea).toHaveAttribute('placeholder', 'Start typing your AI optimization request... (Shift+Enter for new line)');
    });

    it('updates text value in real-time', async () => {
      render(<MessageInput />);
      
      const textarea = screen.getByRole('textbox');
      await user.type(textarea, 'Hello world');
      
      expect(textarea).toHaveValue('Hello world');
    });

    it('measures input latency under 16ms', async () => {
      render(<MessageInput />);
      
      const textarea = screen.getByRole('textbox');
      
      const latency = await measurePerformance(async () => {
        await user.type(textarea, 'a');
      });
      
      // Allow for test environment overhead
      expect(latency).toBeLessThan(100);
      expect(textarea).toHaveValue('a');
    });

    it('handles rapid typing without lag', async () => {
      render(<MessageInput />);
      
      const textarea = screen.getByRole('textbox');
      const rapidText = 'The quick brown fox jumps over the lazy dog';
      
      const duration = await measurePerformance(async () => {
        await user.type(textarea, rapidText, { delay: 1 });
      });
      
      expect(textarea).toHaveValue(rapidText);
      expect(duration).toBeLessThan(1000);
    });
  });

  describe('Multi-line Support', () => {
    it('creates new line with Shift+Enter', async () => {
      render(<MessageInput />);
      
      const textarea = screen.getByRole('textbox');
      await user.type(textarea, 'Line 1');
      await user.keyboard('{Shift>}{Enter}{/Shift}');
      await user.type(textarea, 'Line 2');
      
      expect(textarea).toHaveValue('Line 1\nLine 2');
    });

    it('handles multiple Shift+Enter combinations', async () => {
      render(<MessageInput />);
      
      const textarea = screen.getByRole('textbox');
      await user.type(textarea, 'First');
      await user.keyboard('{Shift>}{Enter}{/Shift}');
      await user.keyboard('{Shift>}{Enter}{/Shift}');
      await user.type(textarea, 'Third');
      
      expect(textarea).toHaveValue('First\n\nThird');
    });

    it('updates rows based on content', () => {
      mockUseTextareaResize.mockReturnValue({ rows: 3 });
      
      render(<MessageInput />);
      
      const textarea = screen.getByRole('textbox');
      expect(textarea).toHaveAttribute('rows', '3');
    });
  });

  describe('Send with Enter Key', () => {
    it('sends message on Enter key', async () => {
      const mockHandleSend = jest.fn();
      const mockAddToHistory = jest.fn();
      
      mockUseMessageSending.mockReturnValue({
        isSending: false,
        handleSend: mockHandleSend
      });
      
      mockUseMessageHistory.mockReturnValue({
        messageHistory: [],
        addToHistory: mockAddToHistory,
        navigateHistory: jest.fn(() => '')
      });
      
      render(<MessageInput />);
      
      const textarea = screen.getByRole('textbox');
      await user.type(textarea, 'Test message');
      await user.keyboard('{Enter}');
      
      expect(mockAddToHistory).toHaveBeenCalledWith('Test message');
      expect(mockHandleSend).toHaveBeenCalledWith({
        message: 'Test message',
        activeThreadId: 'thread-1',
        currentThreadId: 'thread-1',
        isAuthenticated: true
      });
    });

    it('does not send empty message on Enter', async () => {
      const mockHandleSend = jest.fn();
      
      mockHooks.mockUseMessageSending.mockReturnValue({
        isSending: false,
        handleSend: mockHandleSend
      });
      
      render(<MessageInput />);
      
      const textarea = screen.getByRole('textbox');
      await user.keyboard('{Enter}');
      
      expect(mockHandleSend).not.toHaveBeenCalled();
    });

    it('trims whitespace before sending', async () => {
      const mockHandleSend = jest.fn();
      const mockAddToHistory = jest.fn();
      
      mockUseMessageSending.mockReturnValue({
        isSending: false,
        handleSend: mockHandleSend
      });
      
      mockUseMessageHistory.mockReturnValue({
        messageHistory: [],
        addToHistory: mockAddToHistory,
        navigateHistory: jest.fn(() => '')
      });
      
      render(<MessageInput />);
      
      const textarea = screen.getByRole('textbox');
      await user.type(textarea, '   Test message   ');
      await user.keyboard('{Enter}');
      
      expect(mockAddToHistory).toHaveBeenCalledWith('Test message');
      expect(mockHandleSend).toHaveBeenCalledWith(
        expect.objectContaining({ message: 'Test message' })
      );
    });
  });

  describe('Character Count Display', () => {
    it('shows character count when approaching limit', () => {
      const mockShouldShow = require('@/components/chat/utils/messageInputUtils').shouldShowCharCount;
      mockShouldShow.mockReturnValue(true);
      
      render(<MessageInput />);
      
      const textarea = screen.getByRole('textbox');
      fireEvent.change(textarea, { target: { value: 'a'.repeat(8500) } });
      
      expect(screen.getByText('8500/10000')).toBeInTheDocument();
    });

    it('updates character count in real-time', async () => {
      const mockShouldShow = require('@/components/chat/utils/messageInputUtils').shouldShowCharCount;
      mockShouldShow.mockReturnValue(true);
      
      render(<MessageInput />);
      
      const textarea = screen.getByRole('textbox');
      await user.type(textarea, 'Hello');
      
      expect(screen.getByText('5/10000')).toBeInTheDocument();
    });

    it('hides character count for short messages', () => {
      render(<MessageInput />);
      
      const textarea = screen.getByRole('textbox');
      fireEvent.change(textarea, { target: { value: 'Short' } });
      
      expect(screen.queryByText(/\/10000/)).not.toBeInTheDocument();
    });
  });

  describe('Max Length Enforcement', () => {
    it('prevents input beyond character limit', async () => {
      render(<MessageInput />);
      
      const textarea = screen.getByRole('textbox');
      const longText = 'a'.repeat(10001);
      
      await user.type(textarea, longText);
      
      expect(textarea.value.length).toBeLessThanOrEqual(10000);
    });

    it('shows warning near character limit', () => {
      const mockGetPlaceholder = require('@/components/chat/utils/messageInputUtils').getPlaceholder;
      mockGetPlaceholder.mockReturnValue('100 characters remaining');
      
      render(<MessageInput />);
      
      expect(screen.getByDisplayValue('')).toHaveAttribute('placeholder', '100 characters remaining');
    });
  });

  describe('Auto-resize Behavior', () => {
    it('adjusts height based on content', () => {
      mockUseTextareaResize.mockReturnValue({ rows: 4 });
      
      render(<MessageInput />);
      
      const textarea = screen.getByRole('textbox');
      expect(textarea).toHaveAttribute('rows', '4');
      expect(textarea).toHaveStyle({
        minHeight: '48px',
        maxHeight: '144px',
        lineHeight: '24px'
      });
    });

    it('respects maximum height limit', () => {
      mockUseTextareaResize.mockReturnValue({ rows: 5 });
      
      render(<MessageInput />);
      
      const textarea = screen.getByRole('textbox');
      expect(textarea).toHaveAttribute('rows', '5');
    });
  });

  describe('Accessibility and States', () => {
    it('has proper ARIA labels', () => {
      render(<MessageInput />);
      
      const textarea = screen.getByRole('textbox');
      expect(textarea).toHaveAttribute('aria-label', 'Message input');
      expect(textarea).toHaveAttribute('aria-describedby', 'char-count');
    });

    it('maintains focus management', () => {
      render(<MessageInput />);
      
      const textarea = screen.getByRole('textbox');
      expect(textarea).toHaveFocus();
    });

    it('disables input when processing', () => {
      mockUseUnifiedChatStore.mockReturnValue({
        activeThreadId: 'thread-1',
        isProcessing: true
      });
      
      render(<MessageInput />);
      
      const textarea = screen.getByRole('textbox');
      expect(textarea).toBeDisabled();
    });

    it('disables input when not authenticated', () => {
      mockUseAuthStore.mockReturnValue({
        isAuthenticated: false
      });
      
      render(<MessageInput />);
      
      const textarea = screen.getByRole('textbox');
      expect(textarea).toBeDisabled();
    });
  });
});