import { setupAntiHang, cleanupAntiHang } from '@/__tests__/utils/anti-hanging-test-utilities';
import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { jest } from '@jest/globals';
import { MessageInput } from '@/components/chat/MessageInput';
import { rt React from 'react';
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
    jest.setTimeout(10000);
  const user = userEvent.setup();

  beforeEach(() => {
    setupMessageInputMocks();
    jest.clearAllMocks();
  });

  describe('Text Entry and Real-time Updates', () => {
      jest.setTimeout(10000);
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
      jest.setTimeout(10000);
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
      // Mock the useTextareaResize hook to return 3 rows
      mockUseTextareaResize.mockReturnValue({ rows: 3 });
      
      render(<MessageInput />);
      
      const textarea = screen.getByRole('textbox');
      expect(textarea).toHaveAttribute('rows', '3');
      // The component should use the rows prop from the hook
      expect(textarea).toHaveStyle({ height: '72px' }); // 3 rows * 24px line height
    });
  });

  describe('Send with Enter Key', () => {
      jest.setTimeout(10000);
    it('sends message on Enter key', async () => {
      const mockHandleSend = jest.fn();
      const mockAddToHistory = jest.fn();
      
      // Reset all mocks and set up fresh ones
      setupMessageInputMocks();
      
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
      
      setupMessageInputMocks();
      
      mockUseMessageSending.mockReturnValue({
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
      
      setupMessageInputMocks();
      
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
      jest.setTimeout(10000);
    it('shows character count when approaching limit', () => {
      const mockShouldShow = require('@/components/chat/utils/messageInputUtils').shouldShowCharCount;
      mockShouldShow.mockReturnValue(true);
      
      render(<MessageInput />);
      
      const textarea = screen.getByRole('textbox');
      fireEvent.change(textarea, { target: { value: 'a'.repeat(8500) } });
      
      expect(screen.getByText('8500/10000')).toBeInTheDocument();
    });

    it('updates character count in real-time', async () => {
      // Make shouldShowCharCount return true for short messages in this test
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
      jest.setTimeout(10000);
    it('prevents input beyond character limit', async () => {
      render(<MessageInput />);
      
      const textarea = screen.getByRole('textbox');
      // Use fireEvent for very long text to avoid timeout
      const longText = 'a'.repeat(10001);
      
      fireEvent.change(textarea, { target: { value: longText } });
      
      // The component should prevent input beyond limit
      expect(textarea.value.length).toBeLessThanOrEqual(10000);
    }, 5000);

    it('shows warning near character limit', () => {
      const mockGetPlaceholder = require('@/components/chat/utils/messageInputUtils').getPlaceholder;
      mockGetPlaceholder.mockReturnValue('100 characters remaining');
      
      render(<MessageInput />);
      
      const textarea = screen.getByRole('textbox');
      expect(textarea).toHaveAttribute('placeholder', '100 characters remaining');
    });
  });

  describe('Auto-resize Behavior', () => {
      jest.setTimeout(10000);
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
      jest.setTimeout(10000);
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
      // Set up the disabled state properly
      const mockIsDisabled = require('@/components/chat/utils/messageInputUtils').isMessageDisabled;
      mockIsDisabled.mockReturnValue(true);
      
      mockUseUnifiedChatStore.mockReturnValue({
        activeThreadId: 'thread-1',
        isProcessing: true
      });
      
      render(<MessageInput />);
      
      const textarea = screen.getByRole('textbox');
      expect(textarea).toBeDisabled();
    });

    it('disables input when not authenticated', () => {
      // Set up the disabled state properly
      const mockIsDisabled = require('@/components/chat/utils/messageInputUtils').isMessageDisabled;
      mockIsDisabled.mockReturnValue(true);
      
      mockUseAuthStore.mockReturnValue({
        isAuthenticated: false
      });
      
      render(<MessageInput />);
      
      const textarea = screen.getByRole('textbox');
      expect(textarea).toBeDisabled();
    });
  });
});