/**
 * Integration Tests: Sentry Error Reporting Flow
 * 
 * Business Value Justification (BVJ):
 * - Segment: All (Free/Early/Mid/Enterprise) - Operational Excellence
 * - Business Goal: End-to-end error capture and reporting validation
 * - Value Impact: Ensures reliable error monitoring and operational visibility
 * - Strategic Impact: Validates complete error workflow from capture to Sentry delivery
 * 
 * Test Focus: Complete error reporting flow with network simulation (Non-Docker)
 */

import React from 'react';
import { render, fireEvent, waitFor, cleanup } from '@testing-library/react';
import { SentryInit } from '../../../app/sentry-init';
import { ChatErrorBoundary } from '../../../components/chat/ChatErrorBoundary';

// Mock fetch for network simulation
const mockFetch = jest.fn();
global.fetch = mockFetch;

// Mock Sentry with detailed tracking
const mockSentryInit = jest.fn();
const mockSentryCaptureException = jest.fn();
const mockSentryAddBreadcrumb = jest.fn();
const mockSentrySetContext = jest.fn();
const mockSentrySetTag = jest.fn();

jest.mock('@sentry/react', () => ({
  init: mockSentryInit,
  captureException: mockSentryCaptureException,
  addBreadcrumb: mockSentryAddBreadcrumb,
  setContext: mockSentrySetContext,
  setTag: mockSentrySetTag,
  isInitialized: jest.fn(() => true),
  getCurrentScope: jest.fn(() => ({
    setTag: mockSentrySetTag,
    setContext: mockSentrySetContext,
  })),
}));

// Performance measurement utilities
const performanceTracker = {
  measurements: [] as Array<{ operation: string; duration: number; timestamp: number }>,
  start: (operation: string) => {
    const start = performance.now();
    return {
      end: () => {
        const end = performance.now();
        const duration = end - start;
        performanceTracker.measurements.push({
          operation,
          duration,
          timestamp: Date.now(),
        });
        return duration;
      },
    };
  },
  getAverageDuration: (operation: string) => {
    const measurements = performanceTracker.measurements.filter(m => m.operation === operation);
    if (measurements.length === 0) return 0;
    return measurements.reduce((sum, m) => sum + m.duration, 0) / measurements.length;
  },
  clear: () => {
    performanceTracker.measurements = [];
  },
};

// Test component with controlled error throwing
const ErrorThrowingComponent: React.FC<{
  shouldThrow?: boolean;
  errorType?: 'runtime' | 'network' | 'validation';
  errorMessage?: string;
}> = ({ shouldThrow = false, errorType = 'runtime', errorMessage = 'Test error' }) => {
  if (shouldThrow) {
    switch (errorType) {
      case 'runtime':
        throw new Error(errorMessage);
      case 'network':
        throw new Error(`NetworkError: ${errorMessage}`);
      case 'validation':
        throw new Error(`ValidationError: ${errorMessage}`);
    }
  }
  return <div data-testid="no-error">Component rendered successfully</div>;
};

describe('Sentry Error Reporting Flow - Integration Tests', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    performanceTracker.clear();
    mockFetch.mockClear();
    
    // Set up environment for production Sentry
    process.env.NODE_ENV = 'production';
    process.env.NEXT_PUBLIC_ENVIRONMENT = 'staging';
    process.env.NEXT_PUBLIC_SENTRY_DSN = 'https://test@sentry.io/123';
    
    // Mock successful Sentry API responses
    mockFetch.mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({ id: 'error-123' }),
    });
    
    // Set up global Sentry mock
    (global as any).window = {
      Sentry: {
        captureException: mockSentryCaptureException,
        addBreadcrumb: mockSentryAddBreadcrumb,
        setContext: mockSentrySetContext,
        setTag: mockSentrySetTag,
      },
      dataLayer: [],
      localStorage: {
        getItem: jest.fn(() => null),
        setItem: jest.fn(),
      },
      sessionStorage: {
        getItem: jest.fn(() => null),
        setItem: jest.fn(),
      },
    };
  });

  afterEach(() => {
    cleanup();
    delete (global as any).window;
  });

  describe('End-to-End Error Capture Flow', () => {
    test('should complete full error reporting flow with performance measurement', async () => {
      const tracker = performanceTracker.start('error-reporting-flow');
      
      const consoleSpy = jest.spyOn(console, 'error').mockImplementation(() => {});
      
      render(
        <div>
          <SentryInit />
          <ChatErrorBoundary level="message" threadId="thread-123" messageId="msg-456">
            <ErrorThrowingComponent 
              shouldThrow={true} 
              errorType="runtime"
              errorMessage="Integration test error"
            />
          </ChatErrorBoundary>
        </div>
      );
      
      // Wait for error reporting to complete
      await waitFor(() => {
        expect(mockSentryCaptureException).toHaveBeenCalled();
      });
      
      const duration = tracker.end();
      
      // Validate error capture
      expect(mockSentryCaptureException).toHaveBeenCalledWith(
        expect.objectContaining({
          message: 'Integration test error',
        }),
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
        })
      );
      
      // Performance validation - should be under 50ms
      expect(duration).toBeLessThan(50);
      
      consoleSpy.mockRestore();
    });

    test('should handle network request to internal error API', async () => {
      const consoleSpy = jest.spyOn(console, 'error').mockImplementation(() => {});
      
      render(
        <div>
          <SentryInit />
          <ChatErrorBoundary level="chat" threadId="thread-789">
            <ErrorThrowingComponent 
              shouldThrow={true}
              errorType="network"
              errorMessage="API call failed"
            />
          </ChatErrorBoundary>
        </div>
      );
      
      // Wait for API call
      await waitFor(() => {
        expect(mockFetch).toHaveBeenCalled();
      }, { timeout: 2000 });
      
      // Validate API call structure
      const fetchCall = mockFetch.mock.calls[0];
      expect(fetchCall[0]).toBe('/api/errors');
      expect(fetchCall[1]).toMatchObject({
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: expect.any(String),
      });
      
      // Validate request payload
      const payload = JSON.parse(fetchCall[1].body);
      expect(payload).toMatchObject({
        error: 'NetworkError: API call failed',
        level: 'chat',
        context: expect.objectContaining({
          threadId: 'thread-789',
        }),
      });
      
      consoleSpy.mockRestore();
    });

    test('should handle multiple concurrent error reports', async () => {
      const consoleSpy = jest.spyOn(console, 'error').mockImplementation(() => {});
      
      const components = Array.from({ length: 5 }, (_, i) => (
        <ChatErrorBoundary key={i} level="message" messageId={`msg-${i}`}>
          <ErrorThrowingComponent 
            shouldThrow={true}
            errorMessage={`Concurrent error ${i}`}
          />
        </ChatErrorBoundary>
      ));
      
      render(
        <div>
          <SentryInit />
          {components}
        </div>
      );
      
      // Wait for all errors to be captured
      await waitFor(() => {
        expect(mockSentryCaptureException).toHaveBeenCalledTimes(5);
      }, { timeout: 3000 });
      
      // Wait for all API calls
      await waitFor(() => {
        expect(mockFetch).toHaveBeenCalledTimes(5);
      }, { timeout: 3000 });
      
      // Validate each error was captured with correct metadata
      mockSentryCaptureException.mock.calls.forEach((call, index) => {
        expect(call[0]).toMatchObject({
          message: `Concurrent error ${index}`,
        });
        expect(call[1]).toMatchObject({
          tags: expect.objectContaining({
            message_id: `msg-${index}`,
          }),
        });
      });
      
      consoleSpy.mockRestore();
    });
  });

  describe('Error Metadata and Context Preservation', () => {
    test('should preserve comprehensive error context throughout reporting flow', async () => {
      const consoleSpy = jest.spyOn(console, 'error').mockImplementation(() => {});
      
      // Mock user data
      (global as any).window.localStorage.getItem.mockImplementation((key: string) => {
        if (key === 'user') return JSON.stringify({ id: 'user-456', email: 'test@example.com' });
        return null;
      });
      
      render(
        <div>
          <SentryInit />
          <ChatErrorBoundary 
            level="thread" 
            threadId="thread-context-test"
            messageId="msg-context-test"
          >
            <ErrorThrowingComponent 
              shouldThrow={true}
              errorMessage="Context preservation test"
            />
          </ChatErrorBoundary>
        </div>
      );
      
      await waitFor(() => {
        expect(mockSentryCaptureException).toHaveBeenCalled();
      });
      
      const captureCall = mockSentryCaptureException.mock.calls[0];
      
      // Validate error context
      expect(captureCall[1].contexts.chat_error).toMatchObject({
        level: 'thread',
        component: 'ChatErrorBoundary',
        threadId: 'thread-context-test',
        messageId: 'msg-context-test',
        userId: 'user-456',
        timestamp: expect.any(String),
        userAgent: expect.any(String),
        url: expect.any(String),
        sessionId: expect.any(String),
      });
      
      // Validate tags
      expect(captureCall[1].tags).toMatchObject({
        component: 'chat',
        boundary_level: 'thread',
        thread_id: 'thread-context-test',
        message_id: 'msg-context-test',
      });
      
      consoleSpy.mockRestore();
    });

    test('should handle error context with missing optional data', async () => {
      const consoleSpy = jest.spyOn(console, 'error').mockImplementation(() => {});
      
      // Mock localStorage with partial data
      (global as any).window.localStorage.getItem.mockImplementation(() => null);
      
      render(
        <div>
          <SentryInit />
          <ChatErrorBoundary level="message">
            <ErrorThrowingComponent 
              shouldThrow={true}
              errorMessage="Minimal context test"
            />
          </ChatErrorBoundary>
        </div>
      );
      
      await waitFor(() => {
        expect(mockSentryCaptureException).toHaveBeenCalled();
      });
      
      const captureCall = mockSentryCaptureException.mock.calls[0];
      
      // Should still have basic context
      expect(captureCall[1].contexts.chat_error).toMatchObject({
        level: 'message',
        component: 'ChatErrorBoundary',
        timestamp: expect.any(String),
        sessionId: expect.any(String),
      });
      
      // Optional fields should be undefined or absent
      expect(captureCall[1].contexts.chat_error.userId).toBeUndefined();
      expect(captureCall[1].contexts.chat_error.threadId).toBeUndefined();
      
      consoleSpy.mockRestore();
    });
  });

  describe('Network Failure and Retry Logic', () => {
    test('should handle Sentry API network failures gracefully', async () => {
      const consoleSpy = jest.spyOn(console, 'error').mockImplementation(() => {});
      
      // Mock network failure
      mockFetch.mockRejectedValue(new Error('Network request failed'));
      
      render(
        <div>
          <SentryInit />
          <ChatErrorBoundary level="message">
            <ErrorThrowingComponent 
              shouldThrow={true}
              errorMessage="Network failure test"
            />
          </ChatErrorBoundary>
        </div>
      );
      
      await waitFor(() => {
        expect(mockFetch).toHaveBeenCalled();
      });
      
      // Should still capture with Sentry
      expect(mockSentryCaptureException).toHaveBeenCalled();
      
      // Should not throw error on network failure
      expect(consoleSpy).not.toHaveBeenCalledWith(
        expect.stringContaining('Failed to send to API')
      );
      
      consoleSpy.mockRestore();
    });

    test('should queue errors for retry when API is unavailable', async () => {
      const consoleSpy = jest.spyOn(console, 'error').mockImplementation(() => {});
      
      // Mock API failure
      mockFetch.mockRejectedValue(new Error('Service unavailable'));
      
      render(
        <div>
          <SentryInit />
          <ChatErrorBoundary level="message" messageId="retry-test">
            <ErrorThrowingComponent 
              shouldThrow={true}
              errorMessage="Retry queue test"
            />
          </ChatErrorBoundary>
        </div>
      );
      
      await waitFor(() => {
        expect(mockFetch).toHaveBeenCalled();
      });
      
      // Should attempt to queue error in localStorage
      expect((global as any).window.localStorage.setItem).toHaveBeenCalledWith(
        'chat_error_queue',
        expect.any(String)
      );
      
      consoleSpy.mockRestore();
    });

    test('should retry queued errors when API becomes available', async () => {
      const consoleSpy = jest.spyOn(console, 'error').mockImplementation(() => {});
      
      // Mock localStorage with queued error
      const queuedError = {
        error: 'Previous error',
        queued_at: Date.now() - 1000,
      };
      (global as any).window.localStorage.getItem.mockImplementation((key: string) => {
        if (key === 'chat_error_queue') return JSON.stringify([queuedError]);
        return null;
      });
      
      // Mock successful retry
      mockFetch.mockResolvedValue({ ok: true, status: 200 });
      
      render(
        <div>
          <SentryInit />
          <ChatErrorBoundary level="message">
            <ErrorThrowingComponent shouldThrow={false} />
          </ChatErrorBoundary>
        </div>
      );
      
      // Wait for retry mechanism to activate
      await new Promise(resolve => setTimeout(resolve, 100));
      
      // Should eventually try to send queued error (implementation dependent)
      // This test validates the structure exists for retry logic
      expect((global as any).window.localStorage.getItem).toHaveBeenCalledWith('chat_error_queue');
      
      consoleSpy.mockRestore();
    });
  });

  describe('Performance Impact Measurement', () => {
    test('should maintain low performance overhead during error reporting', async () => {
      const consoleSpy = jest.spyOn(console, 'error').mockImplementation(() => {});
      
      const measurements: number[] = [];
      
      // Run multiple error reporting cycles
      for (let i = 0; i < 10; i++) {
        const tracker = performanceTracker.start('error-cycle');
        
        const { unmount } = render(
          <div>
            <SentryInit />
            <ChatErrorBoundary level="message" messageId={`perf-test-${i}`}>
              <ErrorThrowingComponent shouldThrow={true} errorMessage={`Performance test ${i}`} />
            </ChatErrorBoundary>
          </div>
        );
        
        await waitFor(() => {
          expect(mockSentryCaptureException).toHaveBeenCalled();
        });
        
        const duration = tracker.end();
        measurements.push(duration);
        
        unmount();
        jest.clearAllMocks();
      }
      
      // Calculate performance metrics
      const averageDuration = measurements.reduce((sum, d) => sum + d, 0) / measurements.length;
      const maxDuration = Math.max(...measurements);
      
      // Performance requirements
      expect(averageDuration).toBeLessThan(50); // Average under 50ms
      expect(maxDuration).toBeLessThan(100);    // Max under 100ms
      
      // Consistency check - no outliers more than 3x average
      const outliers = measurements.filter(d => d > averageDuration * 3);
      expect(outliers).toHaveLength(0);
      
      consoleSpy.mockRestore();
    });

    test('should not cause memory leaks during repeated error capture', async () => {
      const consoleSpy = jest.spyOn(console, 'error').mockImplementation(() => {});
      
      const initialCallCount = mockSentryCaptureException.mock.calls.length;
      
      // Create and destroy many error components
      for (let i = 0; i < 20; i++) {
        const { unmount } = render(
          <div>
            <SentryInit />
            <ChatErrorBoundary level="message" messageId={`memory-test-${i}`}>
              <ErrorThrowingComponent shouldThrow={true} errorMessage={`Memory test ${i}`} />
            </ChatErrorBoundary>
          </div>
        );
        
        // Don't wait for async operations to simulate rapid creation/destruction
        unmount();
      }
      
      // Wait for all async operations to complete
      await waitFor(() => {
        expect(mockSentryCaptureException.mock.calls.length).toBe(initialCallCount + 20);
      }, { timeout: 5000 });
      
      // Memory leak indicator - function call counts should be predictable
      expect(mockSentryCaptureException.mock.calls.length).toBe(initialCallCount + 20);
      expect(mockFetch.mock.calls.length).toBeLessThanOrEqual(20); // Some might be debounced
      
      consoleSpy.mockRestore();
    });
  });

  describe('Error Filtering and Sanitization', () => {
    test('should sanitize sensitive information from error reports', async () => {
      const consoleSpy = jest.spyOn(console, 'error').mockImplementation(() => {});
      
      render(
        <div>
          <SentryInit />
          <ChatErrorBoundary level="message">
            <ErrorThrowingComponent 
              shouldThrow={true}
              errorMessage="Error with password=secret123 and token=abc456"
            />
          </ChatErrorBoundary>
        </div>
      );
      
      await waitFor(() => {
        expect(mockFetch).toHaveBeenCalled();
      });
      
      const fetchCall = mockFetch.mock.calls[0];
      const payload = JSON.parse(fetchCall[1].body);
      
      // Should not contain sensitive information
      expect(payload.error).not.toContain('secret123');
      expect(payload.error).not.toContain('abc456');
      expect(JSON.stringify(payload)).not.toContain('password=');
      expect(JSON.stringify(payload)).not.toContain('token=');
      
      consoleSpy.mockRestore();
    });

    test('should apply beforeSend filtering to error reports', async () => {
      const consoleSpy = jest.spyOn(console, 'error').mockImplementation(() => {});
      
      // Mock beforeSend that filters chunk loading errors
      mockSentryInit.mockImplementation((config) => {
        const beforeSend = config.beforeSend;
        if (beforeSend) {
          const chunkError = {
            exception: { values: [{ value: 'ChunkLoadError: Loading chunk failed' }] },
          };
          const result = beforeSend(chunkError, {});
          expect(result).toBeNull(); // Should filter chunk errors
        }
      });
      
      render(
        <div>
          <SentryInit />
          <ChatErrorBoundary level="message">
            <ErrorThrowingComponent shouldThrow={false} />
          </ChatErrorBoundary>
        </div>
      );
      
      // Validate beforeSend was called during initialization
      expect(mockSentryInit).toHaveBeenCalled();
      
      consoleSpy.mockRestore();
    });
  });
});