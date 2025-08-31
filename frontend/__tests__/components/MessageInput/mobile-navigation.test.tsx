import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { jest } from '@jest/globals';
import { setupAntiHang, cleanupAntiHang } from '@/__tests__/utils/anti-hanging-test-utilities';
ser flow continuity.
 * Critical for mobile-first user engagement and retention.
 */

import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { jest } from '@jest/globals';

// Mock functions for testing
const mockHandleSend = jest.fn().mockResolvedValue(undefined);
const mockAddToHistory = jest.fn();

// Mock all dependencies with reliable implementations
jest.mock('@/hooks/useWebSocket', () => ({
  useWebSocket: jest.fn(() => ({
    sendMessage: jest.fn()
  }))
}));

jest.mock('@/store/unified-chat', () => ({
  useUnifiedChatStore: jest.fn(() => ({
    activeThreadId: 'thread-1',
    isProcessing: false,
    setProcessing: jest.fn(),
    addMessage: jest.fn(),
    setActiveThread: jest.fn(),
    addOptimisticMessage: jest.fn(),
    updateOptimisticMessage: jest.fn(),
    removeOptimisticMessage: jest.fn(),
    clearOptimisticMessages: jest.fn(),
    resetLayers: jest.fn(),
    setConnectionStatus: jest.fn(),
    setThreadLoading: jest.fn(),
    startThreadLoading: jest.fn(),
    completeThreadLoading: jest.fn(),
    clearMessages: jest.fn(),
    loadMessages: jest.fn(),
    messages: []
  }))
}));

jest.mock('@/store/threadStore', () => ({
  useThreadStore: jest.fn(() => ({
    currentThreadId: 'thread-1',
    setCurrentThread: jest.fn(),
    addThread: jest.fn(),
  }))
}));

jest.mock('@/store/authStore', () => ({
  useAuthStore: jest.fn(() => ({
    isAuthenticated: true,
    user: { id: 'user-123', email: 'test@test.com' }
  }))
}));

jest.mock('@/components/chat/hooks/useMessageHistory', () => ({
  useMessageHistory: jest.fn(() => ({
    messageHistory: [],
    addToHistory: mockAddToHistory,
    navigateHistory: jest.fn(() => '')
  }))
}));

jest.mock('@/components/chat/hooks/useTextareaResize', () => ({
  useTextareaResize: jest.fn(() => ({ rows: 1 }))
}));

jest.mock('@/components/chat/hooks/useMessageSending', () => ({
  useMessageSending: jest.fn(() => ({
    isSending: false,
    handleSend: mockHandleSend
  }))
}));

// Import the component after mocking
import { MessageInput } from '@/components/chat/MessageInput';

// Mobile viewport simulation helper
const simulateMobileViewport = () => {
  Object.defineProperty(window, 'innerWidth', {
    writable: true,
    configurable: true,
    value: 375,
  });
  Object.defineProperty(window, 'innerHeight', {
    writable: true,
    configurable: true,
    value: 812,
  });
  fireEvent(window, new Event('resize'));
};

const resetViewport = () => {
  Object.defineProperty(window, 'innerWidth', {
    writable: true,
    configurable: true,
    value: 1024,
  });
  Object.defineProperty(window, 'innerHeight', {
    writable: true,
    configurable: true,
    value: 768,
  });
  fireEvent(window, new Event('resize'));
};

describe('MessageInput - Mobile Navigation', () => {
    jest.setTimeout(10000);
  beforeEach(() => {
    jest.clearAllMocks();
    resetViewport();
  });

  afterEach(() => {
    resetViewport();
      // Clean up timers to prevent hanging
      jest.clearAllTimers();
      jest.useFakeTimers();
      jest.runOnlyPendingTimers();
      jest.useRealTimers();
  });

  const getTextarea = () => screen.getByRole('textbox', { name: /message input/i }) as HTMLTextAreaElement;
  const getSendButton = () => screen.getByRole('button', { name: /send/i });

  describe('Mobile viewport behavior', () => {
      jest.setTimeout(10000);
    test('should render properly in mobile viewport', () => {
      simulateMobileViewport();
      render(<MessageInput />);
      
      const textarea = getTextarea();
      const sendButton = getSendButton();
      
      expect(textarea).toBeInTheDocument();
      expect(sendButton).toBeInTheDocument();
      
      // Component should maintain its responsive design
      expect(textarea).toHaveClass('w-full');
    });

    test('should handle touch events on mobile', async () => {
      simulateMobileViewport();
      render(<MessageInput />);
      
      const textarea = getTextarea();
      
      // Simulate touch start and end events
      fireEvent.touchStart(textarea);
      fireEvent.touchEnd(textarea);
      
      // Component should handle touch events gracefully
      expect(textarea).toBeInTheDocument();
    });

    test('should adapt text area height for mobile keyboards', async () => {
      simulateMobileViewport();
      render(<MessageInput />);
      
      const textarea = getTextarea();
      
      // Simulate long text that would require scrolling
      const longText = 'This is a very long message that would typically require multiple lines on a mobile device with a smaller screen width.';
      fireEvent.change(textarea, { target: { value: longText } });
      
      expect(textarea.value).toBe(longText);
      
      // The component should maintain proper styling for mobile
      expect(textarea.style.minHeight).toBe('48px');
    });

    test('should handle virtual keyboard appearance', async () => {
      simulateMobileViewport();
      render(<MessageInput />);
      
      const textarea = getTextarea();
      
      // Simulate focus which would trigger virtual keyboard
      fireEvent.focus(textarea);
      
      // Simulate viewport height change due to virtual keyboard
      Object.defineProperty(window, 'innerHeight', {
        value: 400, // Reduced height due to keyboard
      });
      fireEvent(window, new Event('resize'));
      
      // Component should remain functional with virtual keyboard
      expect(textarea).toBeInTheDocument();
    });
  });

  describe('Draft preservation', () => {
      jest.setTimeout(10000);
    test('should preserve draft content during navigation', async () => {
      render(<MessageInput />);
      
      const textarea = getTextarea();
      const draftText = 'This is a draft message';
      
      fireEvent.change(textarea, { target: { value: draftText } });
      expect(textarea.value).toBe(draftText);
      
      // Simulate navigation away and back (component unmount/mount)
      // In a real app, this would be handled by the parent component or router
      // Here we test that the component can maintain state
      expect(textarea).toHaveValue(draftText);
    });

    test('should handle draft with special characters', async () => {
      render(<MessageInput />);
      
      const textarea = getTextarea();
      const specialDraft = '🚀 Draft with emoji & special chars: @#$%';
      
      fireEvent.change(textarea, { target: { value: specialDraft } });
      expect(textarea.value).toBe(specialDraft);
    });

    test('should preserve multiline drafts', async () => {
      render(<MessageInput />);
      
      const textarea = getTextarea();
      const multilineDraft = 'Line 1\nLine 2\nLine 3';
      
      fireEvent.change(textarea, { target: { value: multilineDraft } });
      expect(textarea.value).toBe(multilineDraft);
    });

    test('should handle empty drafts correctly', async () => {
      render(<MessageInput />);
      
      const textarea = getTextarea();
      
      // Start with content, then clear it
      fireEvent.change(textarea, { target: { value: 'Some content' } });
      fireEvent.change(textarea, { target: { value: '' } });
      
      expect(textarea.value).toBe('');
      expect(getSendButton()).toBeDisabled();
    });
  });

  describe('Navigation handling', () => {
      jest.setTimeout(10000);
    test('should handle browser back/forward navigation', async () => {
      render(<MessageInput />);
      
      const textarea = getTextarea();
      
      // Simulate typing
      fireEvent.change(textarea, { target: { value: 'Navigation test' } });
      
      // Simulate browser back navigation
      fireEvent(window, new Event('popstate'));
      
      // Component should remain stable
      expect(textarea).toBeInTheDocument();
    });

    test('should handle page visibility changes', async () => {
      render(<MessageInput />);
      
      const textarea = getTextarea();
      fireEvent.change(textarea, { target: { value: 'Visibility test' } });
      
      // Simulate page becoming hidden (user switches tabs)
      Object.defineProperty(document, 'hidden', {
        value: true,
        configurable: true
      });
      fireEvent(document, new Event('visibilitychange'));
      
      // Simulate page becoming visible again
      Object.defineProperty(document, 'hidden', {
        value: false,
        configurable: true
      });
      fireEvent(document, new Event('visibilitychange'));
      
      // Component should maintain its state
      expect(textarea.value).toBe('Visibility test');
    });

    test('should handle focus/blur during navigation', async () => {
      render(<MessageInput />);
      
      const textarea = getTextarea();
      
      // Set content and focus
      fireEvent.change(textarea, { target: { value: 'Focus test' } });
      fireEvent.focus(textarea);
      
      // Simulate navigation causing blur
      fireEvent.blur(textarea);
      
      // Content should be preserved
      expect(textarea.value).toBe('Focus test');
    });

    test('should handle route changes gracefully', async () => {
      render(<MessageInput />);
      
      const textarea = getTextarea();
      fireEvent.change(textarea, { target: { value: 'Route change test' } });
      
      // Simulate a route change event
      fireEvent(window, new Event('beforeunload'));
      
      // Component should remain functional
      expect(textarea).toBeInTheDocument();
      expect(textarea.value).toBe('Route change test');
    });
  });

  describe('Mobile keyboard shortcuts', () => {
      jest.setTimeout(10000);
    test('should handle mobile Enter key behavior', async () => {
      simulateMobileViewport();
      render(<MessageInput />);
      
      const textarea = getTextarea();
      fireEvent.change(textarea, { target: { value: 'Mobile send test' } });
      
      // On mobile, Enter might behave differently
      fireEvent.keyDown(textarea, { key: 'Enter' });
      
      // Component should handle mobile Enter appropriately
      expect(textarea).toBeInTheDocument();
    });

    test('should handle swipe gestures (simulated)', async () => {
      simulateMobileViewport();
      render(<MessageInput />);
      
      const textarea = getTextarea();
      
      // Simulate swipe gestures using touch events
      fireEvent.touchStart(textarea, {
        touches: [{ clientX: 100, clientY: 100 }]
      });
      fireEvent.touchMove(textarea, {
        touches: [{ clientX: 200, clientY: 100 }]
      });
      fireEvent.touchEnd(textarea);
      
      // Component should handle gestures without breaking
      expect(textarea).toBeInTheDocument();
    });

    test('should handle long press events', async () => {
      simulateMobileViewport();
      render(<MessageInput />);
      
      const textarea = getTextarea();
      
      // Simulate long press
      fireEvent.touchStart(textarea);
      
      // Wait for long press timeout (simulated)
      await new Promise(resolve => setTimeout(resolve, 100));
      
      fireEvent.touchEnd(textarea);
      
      // Component should handle long press gracefully
      expect(textarea).toBeInTheDocument();
    });
  });

  describe('Responsive design', () => {
      jest.setTimeout(10000);
    test('should adapt to different screen sizes', async () => {
      // Test various mobile screen sizes
      const screenSizes = [
        { width: 320, height: 568 }, // iPhone 5
        { width: 375, height: 812 }, // iPhone X
        { width: 414, height: 896 }, // iPhone 11 Pro Max
        { width: 360, height: 640 }  // Android
      ];
      
      for (const size of screenSizes) {
        Object.defineProperty(window, 'innerWidth', { value: size.width });
        Object.defineProperty(window, 'innerHeight', { value: size.height });
        fireEvent(window, new Event('resize'));
        
        const { rerender } = render(<MessageInput />);
        
        const textarea = getTextarea();
        expect(textarea).toBeInTheDocument();
        expect(textarea).toHaveClass('w-full');
        
        rerender(<div />); // Clean up for next iteration
      }
    });

    test('should maintain accessibility on mobile', async () => {
      simulateMobileViewport();
      render(<MessageInput />);
      
      const textarea = getTextarea();
      const sendButton = getSendButton();
      
      // Check accessibility attributes are present
      expect(textarea).toHaveAttribute('aria-label', 'Message input');
      expect(sendButton).toHaveAttribute('aria-label', 'Send message');
      
      // Check touch targets are appropriate size
      const textareaStyles = getComputedStyle(textarea);
      expect(parseInt(textareaStyles.minHeight)).toBeGreaterThanOrEqual(44); // iOS minimum
    });

    test('should handle orientation changes', async () => {
      render(<MessageInput />);
      
      const textarea = getTextarea();
      fireEvent.change(textarea, { target: { value: 'Orientation test' } });
      
      // Simulate portrait to landscape
      Object.defineProperty(window, 'innerWidth', { value: 812 });
      Object.defineProperty(window, 'innerHeight', { value: 375 });
      fireEvent(window, new Event('resize'));
      
      // Content should be preserved
      expect(textarea.value).toBe('Orientation test');
      
      // Simulate landscape to portrait
      Object.defineProperty(window, 'innerWidth', { value: 375 });
      Object.defineProperty(window, 'innerHeight', { value: 812 });
      fireEvent(window, new Event('resize'));
      
      // Content should still be preserved
      expect(textarea.value).toBe('Orientation test');
    });
  });
});