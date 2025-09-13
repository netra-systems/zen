/**
 * Unit Tests: Sentry Initialization Component
 * 
 * Business Value Justification (BVJ):
 * - Segment: All (Free/Early/Mid/Enterprise) - Operational Excellence
 * - Business Goal: Production-grade error monitoring for $500K+ ARR platform
 * - Value Impact: Prevents operational blindness and enables proactive issue resolution
 * - Strategic Impact: Foundation for reliable error collection and environment isolation
 * 
 * Test Focus: Environment-aware initialization to prevent "multiple instance" conflicts
 */

import React from 'react';
import { render, cleanup } from '@testing-library/react';
import { SentryInit } from '../../../app/sentry-init';

// Mock Sentry to control initialization behavior
const mockSentryInit = jest.fn();
const mockSentryClose = jest.fn();

jest.mock('@sentry/react', () => ({
  init: mockSentryInit,
  close: mockSentryClose,
  isInitialized: jest.fn(() => false),
  getCurrentScope: jest.fn(() => ({
    setTag: jest.fn(),
    setContext: jest.fn(),
  })),
}));

describe('SentryInit Component - Initialization Tests', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    delete process.env.NEXT_PUBLIC_SENTRY_DSN;
    delete process.env.NODE_ENV;
    delete process.env.NEXT_PUBLIC_ENVIRONMENT;
  });

  afterEach(() => {
    cleanup();
  });

  describe('Environment Detection', () => {
    test('should not initialize Sentry in development environment', () => {
      process.env.NODE_ENV = 'development';
      process.env.NEXT_PUBLIC_SENTRY_DSN = 'https://test@example.ingest.sentry.io/123';
      
      render(<SentryInit />);
      
      expect(mockSentryInit).not.toHaveBeenCalled();
    });

    test('should not initialize Sentry in test environment', () => {
      process.env.NODE_ENV = 'test';
      process.env.NEXT_PUBLIC_SENTRY_DSN = 'https://test@example.ingest.sentry.io/123';
      
      render(<SentryInit />);
      
      expect(mockSentryInit).not.toHaveBeenCalled();
    });

    test('should not initialize Sentry without valid DSN in production', () => {
      process.env.NODE_ENV = 'production';
      delete process.env.NEXT_PUBLIC_SENTRY_DSN;
      
      render(<SentryInit />);
      
      expect(mockSentryInit).not.toHaveBeenCalled();
    });

    test('should initialize Sentry with valid configuration in staging', () => {
      process.env.NODE_ENV = 'production';
      process.env.NEXT_PUBLIC_ENVIRONMENT = 'staging';
      process.env.NEXT_PUBLIC_SENTRY_DSN = 'https://valid@sentry.io/123';
      
      render(<SentryInit />);
      
      expect(mockSentryInit).toHaveBeenCalledWith(
        expect.objectContaining({
          dsn: 'https://valid@sentry.io/123',
          environment: 'staging',
        })
      );
    });

    test('should initialize Sentry with valid configuration in production', () => {
      process.env.NODE_ENV = 'production';
      process.env.NEXT_PUBLIC_ENVIRONMENT = 'production';
      process.env.NEXT_PUBLIC_SENTRY_DSN = 'https://valid@sentry.io/123';
      
      render(<SentryInit />);
      
      expect(mockSentryInit).toHaveBeenCalledWith(
        expect.objectContaining({
          dsn: 'https://valid@sentry.io/123',
          environment: 'production',
        })
      );
    });
  });

  describe('DSN Validation', () => {
    beforeEach(() => {
      process.env.NODE_ENV = 'production';
      process.env.NEXT_PUBLIC_ENVIRONMENT = 'staging';
    });

    test('should reject invalid DSN format', () => {
      process.env.NEXT_PUBLIC_SENTRY_DSN = 'invalid-dsn';
      
      render(<SentryInit />);
      
      expect(mockSentryInit).not.toHaveBeenCalled();
    });

    test('should reject HTTP DSN (require HTTPS)', () => {
      process.env.NEXT_PUBLIC_SENTRY_DSN = 'http://test@sentry.io/123';
      
      render(<SentryInit />);
      
      expect(mockSentryInit).not.toHaveBeenCalled();
    });

    test('should accept valid HTTPS Sentry DSN', () => {
      process.env.NEXT_PUBLIC_SENTRY_DSN = 'https://test@sentry.io/123';
      
      render(<SentryInit />);
      
      expect(mockSentryInit).toHaveBeenCalledWith(
        expect.objectContaining({
          dsn: 'https://test@sentry.io/123',
        })
      );
    });

    test('should reject empty or whitespace DSN', () => {
      process.env.NEXT_PUBLIC_SENTRY_DSN = '   ';
      
      render(<SentryInit />);
      
      expect(mockSentryInit).not.toHaveBeenCalled();
    });
  });

  describe('Multiple Instance Prevention', () => {
    const mockIsInitialized = require('@sentry/react').isInitialized;

    test('should not initialize if Sentry is already initialized', () => {
      process.env.NODE_ENV = 'production';
      process.env.NEXT_PUBLIC_ENVIRONMENT = 'staging';
      process.env.NEXT_PUBLIC_SENTRY_DSN = 'https://test@sentry.io/123';
      
      mockIsInitialized.mockReturnValue(true);
      
      render(<SentryInit />);
      
      expect(mockSentryInit).not.toHaveBeenCalled();
    });

    test('should handle rapid component mount/unmount cycles', () => {
      process.env.NODE_ENV = 'production';
      process.env.NEXT_PUBLIC_ENVIRONMENT = 'staging';
      process.env.NEXT_PUBLIC_SENTRY_DSN = 'https://test@sentry.io/123';
      
      mockIsInitialized.mockReturnValue(false);
      
      // Mount and unmount rapidly multiple times
      for (let i = 0; i < 3; i++) {
        const { unmount } = render(<SentryInit />);
        unmount();
      }
      
      // Should only initialize once
      expect(mockSentryInit).toHaveBeenCalledTimes(1);
    });
  });

  describe('Initialization Configuration', () => {
    beforeEach(() => {
      process.env.NODE_ENV = 'production';
      process.env.NEXT_PUBLIC_SENTRY_DSN = 'https://test@sentry.io/123';
    });

    test('should configure appropriate settings for staging environment', () => {
      process.env.NEXT_PUBLIC_ENVIRONMENT = 'staging';
      
      render(<SentryInit />);
      
      expect(mockSentryInit).toHaveBeenCalledWith(
        expect.objectContaining({
          environment: 'staging',
          tracesSampleRate: expect.any(Number),
          profilesSampleRate: expect.any(Number),
          beforeSend: expect.any(Function),
        })
      );
    });

    test('should configure appropriate settings for production environment', () => {
      process.env.NEXT_PUBLIC_ENVIRONMENT = 'production';
      
      render(<SentryInit />);
      
      expect(mockSentryInit).toHaveBeenCalledWith(
        expect.objectContaining({
          environment: 'production',
          tracesSampleRate: expect.any(Number),
          profilesSampleRate: expect.any(Number),
          beforeSend: expect.any(Function),
        })
      );
    });

    test('should include error filtering configuration', () => {
      process.env.NEXT_PUBLIC_ENVIRONMENT = 'staging';
      
      render(<SentryInit />);
      
      const initCall = mockSentryInit.mock.calls[0][0];
      expect(initCall.beforeSend).toBeDefined();
      expect(typeof initCall.beforeSend).toBe('function');
    });

    test('should set appropriate sample rates for different environments', () => {
      process.env.NEXT_PUBLIC_ENVIRONMENT = 'staging';
      
      render(<SentryInit />);
      
      const initCall = mockSentryInit.mock.calls[0][0];
      expect(initCall.tracesSampleRate).toBeGreaterThan(0);
      expect(initCall.tracesSampleRate).toBeLessThanOrEqual(1);
      expect(initCall.profilesSampleRate).toBeGreaterThan(0);
      expect(initCall.profilesSampleRate).toBeLessThanOrEqual(1);
    });
  });

  describe('Error Handling', () => {
    test('should handle Sentry initialization errors gracefully', () => {
      process.env.NODE_ENV = 'production';
      process.env.NEXT_PUBLIC_ENVIRONMENT = 'staging';
      process.env.NEXT_PUBLIC_SENTRY_DSN = 'https://test@sentry.io/123';
      
      mockSentryInit.mockImplementation(() => {
        throw new Error('Sentry initialization failed');
      });
      
      // Should not throw error
      expect(() => render(<SentryInit />)).not.toThrow();
    });

    test('should log initialization errors to console', () => {
      const consoleSpy = jest.spyOn(console, 'error').mockImplementation(() => {});
      
      process.env.NODE_ENV = 'production';
      process.env.NEXT_PUBLIC_ENVIRONMENT = 'staging';
      process.env.NEXT_PUBLIC_SENTRY_DSN = 'https://test@sentry.io/123';
      
      mockSentryInit.mockImplementation(() => {
        throw new Error('Sentry initialization failed');
      });
      
      render(<SentryInit />);
      
      expect(consoleSpy).toHaveBeenCalledWith(
        expect.stringContaining('Sentry initialization failed'),
        expect.any(Error)
      );
      
      consoleSpy.mockRestore();
    });
  });

  describe('Component Lifecycle', () => {
    test('should return null (render nothing)', () => {
      process.env.NODE_ENV = 'production';
      process.env.NEXT_PUBLIC_ENVIRONMENT = 'staging';
      process.env.NEXT_PUBLIC_SENTRY_DSN = 'https://test@sentry.io/123';
      
      const { container } = render(<SentryInit />);
      
      expect(container.firstChild).toBeNull();
    });

    test('should handle component unmounting without errors', () => {
      process.env.NODE_ENV = 'production';
      process.env.NEXT_PUBLIC_ENVIRONMENT = 'staging';
      process.env.NEXT_PUBLIC_SENTRY_DSN = 'https://test@sentry.io/123';
      
      const { unmount } = render(<SentryInit />);
      
      expect(() => unmount()).not.toThrow();
    });
  });
});