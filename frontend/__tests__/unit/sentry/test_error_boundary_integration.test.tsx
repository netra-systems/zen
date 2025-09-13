/**
 * Unit Tests: Error Boundary Integration with Sentry
 * 
 * Business Value Justification (BVJ):
 * - Segment: All (Free/Early/Mid/Enterprise) - User Experience & Operational Excellence
 * - Business Goal: Seamless error capture and reporting from React error boundaries  
 * - Value Impact: Prevents error blindness and ensures comprehensive error collection
 * - Strategic Impact: Integrates existing error boundary infrastructure with Sentry monitoring
 * 
 * Test Focus: Error boundary + Sentry integration for comprehensive error capture
 */

import React from 'react';
import { render, cleanup } from '@testing-library/react';
import { ChatErrorBoundary } from '../../../components/chat/ChatErrorBoundary';
import { SentryInit } from '../../../app/sentry-init';

// Mock Sentry functions
const mockSentryCaptureException = jest.fn();
const mockSentryAddBreadcrumb = jest.fn();
const mockSentrySetTag = jest.fn();
const mockSentrySetContext = jest.fn();
const mockSentryInit = jest.fn();

jest.mock('@sentry/react', () => ({
  init: mockSentryInit,
  captureException: mockSentryCaptureException,
  addBreadcrumb: mockSentryAddBreadcrumb,
  setTag: mockSentrySetTag,
  setContext: mockSentrySetContext,
  isInitialized: jest.fn(() => true),
  getCurrentScope: jest.fn(() => ({
    setTag: mockSentrySetTag,
    setContext: mockSentrySetContext,
  })),
  withErrorBoundary: jest.fn((component) => component),
  ErrorBoundary: ({ children, fallback }: any) => {
    try {
      return children;
    } catch (error) {
      return fallback;
    }
  },
}));

// Test component that throws an error
const ErrorThrowingComponent: React.FC<{ shouldThrow?: boolean }> = ({ shouldThrow = false }) => {
  if (shouldThrow) {
    throw new Error('Test error for Sentry integration');
  }
  return <div>No error</div>;
};

describe('Error Boundary + Sentry Integration Tests', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    
    // Set up environment for Sentry initialization
    process.env.NODE_ENV = 'production';
    process.env.NEXT_PUBLIC_ENVIRONMENT = 'staging';
    process.env.NEXT_PUBLIC_SENTRY_DSN = 'https://test@sentry.io/123';
    
    // Mock window.Sentry for error boundary integration
    (global as any).window = {
      Sentry: {
        captureException: mockSentryCaptureException,
        addBreadcrumb: mockSentryAddBreadcrumb,
        setTag: mockSentrySetTag,
        setContext: mockSentrySetContext,
      },
    };
  });

  afterEach(() => {
    cleanup();
    delete (global as any).window;
  });

  describe('Sentry Initialization with Error Boundary', () => {
    test('should initialize Sentry before error boundary catches errors', () => {
      render(
        <div>
          <SentryInit />
          <ChatErrorBoundary level="chat">
            <ErrorThrowingComponent />
          </ChatErrorBoundary>
        </div>
      );
      
      expect(mockSentryInit).toHaveBeenCalled();
    });

    test('should work with error boundary when Sentry is not initialized', () => {
      delete (global as any).window.Sentry;
      
      expect(() => {
        render(
          <ChatErrorBoundary level="message">
            <ErrorThrowingComponent />
          </ChatErrorBoundary>
        );
      }).not.toThrow();
    });
  });

  describe('Error Capture Integration', () => {
    test('should capture React errors via Sentry when available', () => {
      // Spy on console.error to capture the error boundary call
      const consoleSpy = jest.spyOn(console, 'error').mockImplementation(() => {});
      
      render(
        <div>
          <SentryInit />
          <ChatErrorBoundary level="message" threadId="thread-123" messageId="msg-456">
            <ErrorThrowingComponent shouldThrow={true} />
          </ChatErrorBoundary>
        </div>
      );
      
      // Should capture exception with Sentry
      expect(mockSentryCaptureException).toHaveBeenCalledWith(
        expect.any(Error),
        expect.objectContaining({
          tags: expect.objectContaining({
            component: 'chat',
            boundary_level: 'message',
            thread_id: 'thread-123',
            message_id: 'msg-456',
          }),
          contexts: expect.objectContaining({
            chat_error: expect.any(Object),
          }),
          level: 'low', // message level = low severity
        })
      );
      
      consoleSpy.mockRestore();
    });

    test('should preserve error context and metadata for Sentry', () => {
      const consoleSpy = jest.spyOn(console, 'error').mockImplementation(() => {});
      
      render(
        <div>
          <SentryInit />
          <ChatErrorBoundary level="chat" threadId="thread-789">
            <ErrorThrowingComponent shouldThrow={true} />
          </ChatErrorBoundary>
        </div>
      );
      
      const captureCall = mockSentryCaptureException.mock.calls[0];
      expect(captureCall[0]).toBeInstanceOf(Error);
      expect(captureCall[1]).toMatchObject({
        tags: {
          component: 'chat',
          boundary_level: 'chat',
          thread_id: 'thread-789',
        },
        contexts: {
          chat_error: expect.objectContaining({
            level: 'chat',
            component: 'ChatErrorBoundary',
            threadId: 'thread-789',
            timestamp: expect.any(String),
            userAgent: expect.any(String),
          }),
        },
        level: 'high', // chat level = high severity
      });
      
      consoleSpy.mockRestore();
    });

    test('should handle different error boundary severity levels', () => {
      const consoleSpy = jest.spyOn(console, 'error').mockImplementation(() => {});
      
      const levels = [
        { level: 'message', expectedSeverity: 'low' },
        { level: 'thread', expectedSeverity: 'medium' },
        { level: 'chat', expectedSeverity: 'high' },
        { level: 'app', expectedSeverity: 'critical' },
      ] as const;
      
      levels.forEach(({ level, expectedSeverity }) => {
        jest.clearAllMocks();
        
        render(
          <div>
            <SentryInit />
            <ChatErrorBoundary level={level}>
              <ErrorThrowingComponent shouldThrow={true} />
            </ChatErrorBoundary>
          </div>
        );
        
        expect(mockSentryCaptureException).toHaveBeenCalledWith(
          expect.any(Error),
          expect.objectContaining({
            level: expectedSeverity,
          })
        );
      });
      
      consoleSpy.mockRestore();
    });
  });

  describe('Error Context Enrichment', () => {
    test('should include comprehensive error context for Sentry', () => {
      const consoleSpy = jest.spyOn(console, 'error').mockImplementation(() => {});
      
      // Mock user data in localStorage
      const mockUser = { id: 'user-123', name: 'Test User' };
      Object.defineProperty(window, 'localStorage', {
        value: {
          getItem: jest.fn((key) => {
            if (key === 'user') return JSON.stringify(mockUser);
            return null;
          }),
        },
        writable: true,
      });
      
      render(
        <div>
          <SentryInit />
          <ChatErrorBoundary level="thread" threadId="thread-456" messageId="msg-789">
            <ErrorThrowingComponent shouldThrow={true} />
          </ChatErrorBoundary>
        </div>
      );
      
      const captureCall = mockSentryCaptureException.mock.calls[0];
      expect(captureCall[1].contexts.chat_error).toMatchObject({
        level: 'thread',
        component: 'ChatErrorBoundary',
        threadId: 'thread-456',
        messageId: 'msg-789',
        userId: 'user-123',
        sessionId: expect.any(String),
        timestamp: expect.any(String),
        userAgent: expect.any(String),
        url: 'http://localhost/',
      });
      
      consoleSpy.mockRestore();
    });

    test('should handle missing user context gracefully', () => {
      const consoleSpy = jest.spyOn(console, 'error').mockImplementation(() => {});
      
      // Mock localStorage with no user data
      Object.defineProperty(window, 'localStorage', {
        value: {
          getItem: jest.fn(() => null),
        },
        writable: true,
      });
      
      render(
        <div>
          <SentryInit />
          <ChatErrorBoundary level="message">
            <ErrorThrowingComponent shouldThrow={true} />
          </ChatErrorBoundary>
        </div>
      );
      
      expect(mockSentryCaptureException).toHaveBeenCalled();
      const captureCall = mockSentryCaptureException.mock.calls[0];
      expect(captureCall[1].contexts.chat_error.userId).toBeUndefined();
      
      consoleSpy.mockRestore();
    });
  });

  describe('Component Tree Isolation', () => {
    test('should isolate errors to specific boundary levels', () => {
      const consoleSpy = jest.spyOn(console, 'error').mockImplementation(() => {});
      
      render(
        <div>
          <SentryInit />
          <ChatErrorBoundary level="chat" threadId="outer-thread">
            <div>Outer boundary</div>
            <ChatErrorBoundary level="message" messageId="inner-message">
              <ErrorThrowingComponent shouldThrow={true} />
            </ChatErrorBoundary>
            <div>This should still render</div>
          </ChatErrorBoundary>
        </div>
      );
      
      // Should capture at message level (inner boundary)
      expect(mockSentryCaptureException).toHaveBeenCalledWith(
        expect.any(Error),
        expect.objectContaining({
          tags: expect.objectContaining({
            boundary_level: 'message',
            message_id: 'inner-message',
          }),
        })
      );
      
      consoleSpy.mockRestore();
    });

    test('should provide fallback UI while maintaining Sentry integration', () => {
      const consoleSpy = jest.spyOn(console, 'error').mockImplementation(() => {});
      
      const { container } = render(
        <div>
          <SentryInit />
          <ChatErrorBoundary level="message">
            <ErrorThrowingComponent shouldThrow={true} />
          </ChatErrorBoundary>
        </div>
      );
      
      // Should show fallback UI
      expect(container).toHaveTextContent('Something went wrong');
      
      // Should still capture with Sentry
      expect(mockSentryCaptureException).toHaveBeenCalled();
      
      consoleSpy.mockRestore();
    });
  });

  describe('Performance and Memory Considerations', () => {
    test('should not create memory leaks with repeated error captures', () => {
      const consoleSpy = jest.spyOn(console, 'error').mockImplementation(() => {});
      
      // Simulate multiple error captures
      for (let i = 0; i < 10; i++) {
        const { unmount } = render(
          <div>
            <SentryInit />
            <ChatErrorBoundary level="message" messageId={`msg-${i}`}>
              <ErrorThrowingComponent shouldThrow={true} />
            </ChatErrorBoundary>
          </div>
        );
        unmount();
      }
      
      // Should capture each error
      expect(mockSentryCaptureException).toHaveBeenCalledTimes(10);
      
      // Should not accumulate memory (basic check - real memory testing would require more sophisticated tools)
      expect(mockSentryCaptureException.mock.calls).toHaveLength(10);
      
      consoleSpy.mockRestore();
    });

    test('should handle high-frequency error scenarios gracefully', () => {
      const consoleSpy = jest.spyOn(console, 'error').mockImplementation(() => {});
      
      // Simulate rapid error component mounting/unmounting
      const renderAndUnmount = () => {
        const { unmount } = render(
          <div>
            <SentryInit />
            <ChatErrorBoundary level="message">
              <ErrorThrowingComponent shouldThrow={true} />
            </ChatErrorBoundary>
          </div>
        );
        unmount();
      };
      
      // Should handle rapid operations without throwing
      expect(() => {
        for (let i = 0; i < 5; i++) {
          renderAndUnmount();
        }
      }).not.toThrow();
      
      consoleSpy.mockRestore();
    });
  });

  describe('Error Filtering Integration', () => {
    test('should respect Sentry beforeSend filtering in error boundary', () => {
      const consoleSpy = jest.spyOn(console, 'error').mockImplementation(() => {});
      
      // Mock beforeSend to filter specific errors
      mockSentryInit.mockImplementation((config) => {
        if (config.beforeSend) {
          // Simulate beforeSend filtering
          const mockError = { exception: { values: [{ value: 'ChunkLoadError' }] } };
          const result = config.beforeSend(mockError, {});
          expect(result).toBeNull(); // Should be filtered
        }
      });
      
      render(
        <div>
          <SentryInit />
          <ChatErrorBoundary level="message">
            <ErrorThrowingComponent shouldThrow={true} />
          </ChatErrorBoundary>
        </div>
      );
      
      expect(mockSentryInit).toHaveBeenCalled();
      
      consoleSpy.mockRestore();
    });
  });
});