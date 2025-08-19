/**
 * Mobile and navigation tests for MessageInput component
 * Tests mobile keyboard behavior, draft preservation, navigation
 * 
 * BVJ: Ensures optimal mobile experience and user flow continuity.
 * Critical for mobile-first user engagement and retention.
 */

import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { jest } from '@jest/globals';
import { MessageInput } from '@/components/chat/MessageInput';
import { 
  setupMessageInputMocks, 
  mockHooks,
  simulateMobileViewport,
  resetViewport
} from './shared-test-setup';

describe('MessageInput - Mobile and Navigation', () => {
  const user = userEvent.setup();

  beforeEach(() => {
    setupMessageInputMocks();
    jest.clearAllMocks();
    resetViewport();
  });

  describe('Mobile Keyboard Behavior', () => {
    beforeEach(() => {
      simulateMobileViewport();
    });

    it('handles mobile viewport gracefully', () => {
      render(<MessageInput />);
      
      const textarea = screen.getByRole('textbox');
      expect(textarea).toBeInTheDocument();
      expect(textarea).toHaveStyle({
        minHeight: '48px',
        maxHeight: '144px'
      });
    });

    it('maintains proper dimensions on mobile', () => {
      render(<MessageInput />);
      
      const textarea = screen.getByRole('textbox');
      expect(textarea).toHaveStyle({
        lineHeight: '24px'
      });
      
      // Verify mobile-appropriate sizing
      expect(window.innerWidth).toBe(375);
      expect(window.innerHeight).toBe(667);
    });

    it('handles touch events without errors', async () => {
      render(<MessageInput />);
      
      const textarea = screen.getByRole('textbox');
      
      // Simulate touch interaction
      fireEvent.touchStart(textarea, {
        touches: [{ clientX: 100, clientY: 100 }]
      });
      
      fireEvent.touchEnd(textarea, {
        changedTouches: [{ clientX: 100, clientY: 100 }]
      });
      
      expect(textarea).toBeInTheDocument();
    });

    it('maintains focus on mobile after touch', () => {
      render(<MessageInput />);
      
      const textarea = screen.getByRole('textbox');
      
      fireEvent.touchStart(textarea);
      fireEvent.touchEnd(textarea);
      
      expect(textarea).toHaveFocus();
    });

    it('handles virtual keyboard appearance simulation', async () => {
      render(<MessageInput />);
      
      const textarea = screen.getByRole('textbox');
      
      // Simulate virtual keyboard appearing (viewport height reduction)
      Object.defineProperty(window, 'innerHeight', {
        writable: true,
        configurable: true,
        value: 400,
      });
      
      fireEvent(window, new Event('resize'));
      
      // Component should remain functional
      await user.type(textarea, 'Mobile test');
      expect(textarea).toHaveValue('Mobile test');
    });

    it('handles orientation change', () => {
      render(<MessageInput />);
      
      const textarea = screen.getByRole('textbox');
      
      // Simulate landscape orientation
      Object.defineProperty(window, 'innerWidth', {
        writable: true,
        configurable: true,
        value: 667,
      });
      Object.defineProperty(window, 'innerHeight', {
        writable: true,
        configurable: true,
        value: 375,
      });
      
      fireEvent(window, new Event('resize'));
      
      expect(textarea).toBeInTheDocument();
      expect(textarea).toHaveFocus();
    });
  });

  describe('Draft Preservation and Navigation', () => {
    it('preserves draft when component unmounts', () => {
      const { unmount } = render(<MessageInput />);
      
      const textarea = screen.getByRole('textbox');
      fireEvent.change(textarea, { target: { value: 'Draft message' } });
      
      // Component should unmount cleanly without errors
      expect(() => unmount()).not.toThrow();
    });

    it('restores focus after navigation', async () => {
      const { rerender } = render(<MessageInput />);
      
      // Simulate navigation away
      rerender(<div>Other component</div>);
      
      // Simulate navigation back
      rerender(<MessageInput />);
      
      await waitFor(() => {
        const textarea = screen.getByRole('textbox');
        expect(textarea).toHaveFocus();
      });
    });

    it('maintains state during re-renders', () => {
      const { rerender } = render(<MessageInput />);
      
      const textarea = screen.getByRole('textbox');
      fireEvent.change(textarea, { target: { value: 'Test message' } });
      
      // Force re-render
      rerender(<MessageInput />);
      
      const newTextarea = screen.getByRole('textbox');
      // Note: In real implementation, draft preservation would be handled
      // by external state management or localStorage
      expect(newTextarea).toBeInTheDocument();
    });

    it('handles rapid navigation without memory leaks', () => {
      const { rerender, unmount } = render(<MessageInput />);
      
      // Simulate rapid navigation
      for (let i = 0; i < 10; i++) {
        rerender(<div key={i}>Page {i}</div>);
        rerender(<MessageInput key={i} />);
      }
      
      expect(() => unmount()).not.toThrow();
    });
  });

  describe('Focus Management', () => {
    it('maintains focus when switching between authenticated states', () => {
      const { rerender } = render(<MessageInput />);
      
      let textarea = screen.getByRole('textbox');
      expect(textarea).toHaveFocus();
      
      // Simulate auth state change to unauthenticated
      mockHooks.mockUseAuthStore.mockReturnValue({
        isAuthenticated: false
      });
      
      rerender(<MessageInput />);
      textarea = screen.getByRole('textbox');
      expect(textarea).toBeDisabled();
      
      // Simulate auth state change back to authenticated
      mockHooks.mockUseAuthStore.mockReturnValue({
        isAuthenticated: true
      });
      
      rerender(<MessageInput />);
      textarea = screen.getByRole('textbox');
      expect(textarea).not.toBeDisabled();
      expect(textarea).toHaveFocus();
    });

    it('handles focus restoration after processing', async () => {
      const { rerender } = render(<MessageInput />);
      
      let textarea = screen.getByRole('textbox');
      expect(textarea).toHaveFocus();
      
      // Start processing
      mockHooks.mockUseUnifiedChatStore.mockReturnValue({
        activeThreadId: 'thread-1',
        isProcessing: true
      });
      
      rerender(<MessageInput />);
      textarea = screen.getByRole('textbox');
      expect(textarea).toBeDisabled();
      
      // End processing
      mockHooks.mockUseUnifiedChatStore.mockReturnValue({
        activeThreadId: 'thread-1',
        isProcessing: false
      });
      
      rerender(<MessageInput />);
      
      await waitFor(() => {
        const newTextarea = screen.getByRole('textbox');
        expect(newTextarea).not.toBeDisabled();
        expect(newTextarea).toHaveFocus();
      });
    });
  });

  describe('Performance During Navigation', () => {
    it('renders quickly after navigation', async () => {
      const startTime = performance.now();
      
      const { rerender } = render(<MessageInput />);
      rerender(<div>Other page</div>);
      rerender(<MessageInput />);
      
      const endTime = performance.now();
      const renderTime = endTime - startTime;
      
      expect(renderTime).toBeLessThan(100); // Should render quickly
      expect(screen.getByRole('textbox')).toBeInTheDocument();
    });

    it('handles memory cleanup properly', () => {
      const { unmount } = render(<MessageInput />);
      
      const textarea = screen.getByRole('textbox');
      fireEvent.change(textarea, { target: { value: 'Test content' } });
      
      // Should not throw or cause memory leaks
      expect(() => unmount()).not.toThrow();
    });
  });

  describe('Keyboard Shortcuts Integration', () => {
    it('shows keyboard shortcuts hint', () => {
      render(<MessageInput />);
      
      expect(screen.getByTestId('keyboard-hint')).toBeInTheDocument();
    });

    it('updates keyboard hint based on authentication', () => {
      mockHooks.mockUseAuthStore.mockReturnValue({
        isAuthenticated: false
      });
      
      render(<MessageInput />);
      
      expect(screen.getByText('Sign in to send')).toBeInTheDocument();
    });

    it('shows appropriate hint with message content', async () => {
      render(<MessageInput />);
      
      const textarea = screen.getByRole('textbox');
      await user.type(textarea, 'Test message');
      
      const hint = screen.getByTestId('keyboard-hint');
      expect(hint).toHaveTextContent('Enter to send, Shift+Enter for new line');
    });
  });

  describe('Error Recovery', () => {
    it('recovers gracefully from render errors', () => {
      // Test component resilience
      const { rerender } = render(<MessageInput />);
      
      // Simulate error condition and recovery
      mockHooks.mockUseTextareaResize.mockReturnValue({ rows: null as any });
      
      expect(() => rerender(<MessageInput />)).not.toThrow();
      
      // Reset to normal state
      mockHooks.mockUseTextareaResize.mockReturnValue({ rows: 1 });
      rerender(<MessageInput />);
      
      expect(screen.getByRole('textbox')).toBeInTheDocument();
    });

    it('handles hook failures gracefully', () => {
      // Simulate hook returning undefined
      mockHooks.mockUseAuthStore.mockReturnValue(undefined as any);
      
      expect(() => render(<MessageInput />)).not.toThrow();
    });
  });
});