/**
 * ChatHistorySection Basic Loading States Tests
 * Tests for loading states and error handling ≤300 lines, ≤8 line functions
 */

import React from 'react';
import { render, screen } from '@testing-library/react';
import { ChatHistorySection } from '@/components/ChatHistorySection';
import { createTestSetup, setupLoadingState, setupErrorState } from './shared-setup';
import {
  expectBasicStructure,
  expectLoadingState,
  findChatHistoryContainer,
  mockConsoleError
} from './test-utils';

describe('ChatHistorySection - Loading States', () => {
  const testSetup = createTestSetup();

  beforeEach(() => {
    testSetup.beforeEach();
  });

  afterEach(() => {
    testSetup.afterEach();
  });

  describe('Loading state display', () => {
    it('should show loading state when threads are being fetched', () => {
      setupLoadingState();
      
      render(<ChatHistorySection />);
      
      expectLoadingState();
    });

    it('should maintain header during loading', () => {
      setupLoadingState();
      
      render(<ChatHistorySection />);
      
      expectBasicStructure();
    });

    it('should provide proper loading container structure', () => {
      setupLoadingState();
      
      render(<ChatHistorySection />);
      
      const container = findChatHistoryContainer();
      expect(container).toBeInTheDocument();
    });

    it('should handle loading state transitions smoothly', () => {
      setupLoadingState();
      const { rerender } = render(<ChatHistorySection />);
      
      expectLoadingState();
      
      testSetup.configureStore({ isLoading: false });
      rerender(<ChatHistorySection />);
      
      expectBasicStructure();
    });
  });

  describe('Error state handling', () => {
    it('should handle error state gracefully', () => {
      setupErrorState('Failed to load threads');
      
      render(<ChatHistorySection />);
      
      expectBasicStructure();
    });

    it('should maintain structure during error state', () => {
      setupErrorState('Network error');
      
      render(<ChatHistorySection />);
      
      const container = findChatHistoryContainer();
      expect(container).toBeInTheDocument();
    });

    it('should recover from error state when data is available', () => {
      setupErrorState('Network error');
      const { rerender } = render(<ChatHistorySection />);
      
      expectBasicStructure();
      
      testSetup.configureStore({ error: undefined });
      rerender(<ChatHistorySection />);
      
      expect(screen.getByText('First Conversation')).toBeInTheDocument();
    });

    it('should handle multiple error scenarios', () => {
      const errorMessages = ['Network error', 'Authentication failed', 'Server timeout'];
      
      errorMessages.forEach(error => {
        setupErrorState(error);
        
        render(<ChatHistorySection />);
        expectBasicStructure();
      });
    });
  });

  describe('Loading state variations', () => {
    it('should handle initial loading state', () => {
      testSetup.configureStore({ 
        threads: [], 
        isLoading: true 
      });
      
      render(<ChatHistorySection />);
      
      expectLoadingState();
    });

    it('should handle thread refresh loading', () => {
      const { rerender } = render(<ChatHistorySection />);
      
      expect(screen.getByText('First Conversation')).toBeInTheDocument();
      
      setupLoadingState();
      rerender(<ChatHistorySection />);
      
      expectLoadingState();
    });

    it('should handle partial loading states', () => {
      testSetup.configureStore({ 
        isLoading: false,
        threads: []
      });
      
      render(<ChatHistorySection />);
      
      expectBasicStructure();
    });

    it('should maintain loading state consistency', () => {
      setupLoadingState();
      
      const { rerender } = render(<ChatHistorySection />);
      
      for (let i = 0; i < 3; i++) {
        rerender(<ChatHistorySection />);
        expectLoadingState();
      }
    });
  });

  describe('Error recovery scenarios', () => {
    it('should handle network error recovery', () => {
      setupErrorState('Network connection failed');
      const { rerender } = render(<ChatHistorySection />);
      
      expectBasicStructure();
      
      testSetup.configureStore({ error: undefined });
      rerender(<ChatHistorySection />);
      
      expect(screen.getByText('First Conversation')).toBeInTheDocument();
    });

    it('should handle authentication error recovery', () => {
      setupErrorState('Authentication expired');
      const { rerender } = render(<ChatHistorySection />);
      
      expectBasicStructure();
      
      testSetup.configureStore({ 
        error: undefined,
        isAuthenticated: true 
      });
      rerender(<ChatHistorySection />);
      
      expectBasicStructure();
    });

    it('should handle server error recovery', () => {
      setupErrorState('Internal server error');
      const { rerender } = render(<ChatHistorySection />);
      
      expectBasicStructure();
      
      testSetup.configureStore({ error: undefined });
      rerender(<ChatHistorySection />);
      
      expectBasicStructure();
    });

    it('should handle timeout error recovery', () => {
      setupErrorState('Request timeout');
      const { rerender } = render(<ChatHistorySection />);
      
      expectBasicStructure();
      
      testSetup.configureStore({ error: undefined });
      rerender(<ChatHistorySection />);
      
      expectBasicStructure();
    });
  });

  describe('Console error handling', () => {
    it('should not log errors during normal operation', () => {
      const restoreConsole = mockConsoleError();
      
      render(<ChatHistorySection />);
      
      expect(console.error).not.toHaveBeenCalled();
      restoreConsole();
    });

    it('should handle error logging appropriately', () => {
      const restoreConsole = mockConsoleError();
      setupErrorState('Test error');
      
      render(<ChatHistorySection />);
      
      expectBasicStructure();
      restoreConsole();
    });

    it('should maintain error boundaries', () => {
      const restoreConsole = mockConsoleError();
      
      expect(() => {
        setupErrorState('Critical error');
        render(<ChatHistorySection />);
      }).not.toThrow();
      
      restoreConsole();
    });

    it('should handle component error boundaries', () => {
      const restoreConsole = mockConsoleError();
      
      expect(() => {
        render(<ChatHistorySection />);
      }).not.toThrow();
      
      expectBasicStructure();
      restoreConsole();
    });
  });

  describe('State transition handling', () => {
    it('should handle loading to success transition', () => {
      setupLoadingState();
      const { rerender } = render(<ChatHistorySection />);
      
      expectLoadingState();
      
      testSetup.configureStore({ isLoading: false });
      rerender(<ChatHistorySection />);
      
      expect(screen.getByText('First Conversation')).toBeInTheDocument();
    });

    it('should handle loading to error transition', () => {
      setupLoadingState();
      const { rerender } = render(<ChatHistorySection />);
      
      expectLoadingState();
      
      setupErrorState('Failed to load');
      rerender(<ChatHistorySection />);
      
      expectBasicStructure();
    });

    it('should handle error to loading transition', () => {
      setupErrorState('Network error');
      const { rerender } = render(<ChatHistorySection />);
      
      expectBasicStructure();
      
      setupLoadingState();
      rerender(<ChatHistorySection />);
      
      expectLoadingState();
    });

    it('should handle rapid state transitions', () => {
      const { rerender } = render(<ChatHistorySection />);
      
      const states = [
        () => setupLoadingState(),
        () => setupErrorState('Error'),
        () => testSetup.configureStore({ isLoading: false, error: undefined }),
        () => setupLoadingState(),
        () => testSetup.configureStore({ isLoading: false })
      ];
      
      states.forEach(setState => {
        setState();
        expect(() => rerender(<ChatHistorySection />)).not.toThrow();
        expectBasicStructure();
      });
    });
  });

  describe('Component stability during state changes', () => {
    it('should maintain component integrity during loading', () => {
      setupLoadingState();
      
      const { unmount } = render(<ChatHistorySection />);
      
      expectLoadingState();
      expect(() => unmount()).not.toThrow();
    });

    it('should maintain component integrity during errors', () => {
      setupErrorState('Test error');
      
      const { unmount } = render(<ChatHistorySection />);
      
      expectBasicStructure();
      expect(() => unmount()).not.toThrow();
    });

    it('should handle multiple rerenders safely', () => {
      const { rerender } = render(<ChatHistorySection />);
      
      for (let i = 0; i < 10; i++) {
        expect(() => rerender(<ChatHistorySection />)).not.toThrow();
      }
      
      expectBasicStructure();
    });

    it('should clean up properly on unmount', () => {
      const { unmount } = render(<ChatHistorySection />);
      
      expectBasicStructure();
      expect(() => unmount()).not.toThrow();
    });
  });
});