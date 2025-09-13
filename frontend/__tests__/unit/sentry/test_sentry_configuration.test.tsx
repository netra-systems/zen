/**
 * Unit Tests: Sentry Configuration Management
 * 
 * Business Value Justification (BVJ):
 * - Segment: All (Free/Early/Mid/Enterprise) - Operational Excellence  
 * - Business Goal: Environment-specific error monitoring configuration
 * - Value Impact: Prevents configuration conflicts and ensures proper error isolation
 * - Strategic Impact: Enables reliable multi-environment deployment with proper error boundaries
 * 
 * Test Focus: Environment-specific configuration validation and multiple instance prevention
 */

import React from 'react';
import { render, cleanup } from '@testing-library/react';
import { SentryInit } from '../../../app/sentry-init';

// Mock Sentry to control configuration behavior
const mockSentryInit = jest.fn();
const mockSentryIsInitialized = jest.fn();
const mockSentryGetCurrentScope = jest.fn(() => ({
  setTag: jest.fn(),
  setContext: jest.fn(),
}));

jest.mock('@sentry/react', () => ({
  init: mockSentryInit,
  isInitialized: mockSentryIsInitialized,
  getCurrentScope: mockSentryGetCurrentScope,
}));

describe('SentryInit Component - Configuration Tests', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockSentryIsInitialized.mockReturnValue(false);
    
    // Clear all environment variables
    delete process.env.NEXT_PUBLIC_SENTRY_DSN;
    delete process.env.NODE_ENV;
    delete process.env.NEXT_PUBLIC_ENVIRONMENT;
    delete process.env.NEXT_PUBLIC_SENTRY_DEBUG;
    delete process.env.NEXT_PUBLIC_SENTRY_TRACES_SAMPLE_RATE;
    delete process.env.NEXT_PUBLIC_SENTRY_PROFILES_SAMPLE_RATE;
  });

  afterEach(() => {
    cleanup();
  });

  describe('Environment-Specific Configuration', () => {
    test('should load staging configuration correctly', () => {
      process.env.NODE_ENV = 'production';
      process.env.NEXT_PUBLIC_ENVIRONMENT = 'staging';
      process.env.NEXT_PUBLIC_SENTRY_DSN = 'https://staging@sentry.io/123';
      
      render(<SentryInit />);
      
      expect(mockSentryInit).toHaveBeenCalledWith(
        expect.objectContaining({
          dsn: 'https://staging@sentry.io/123',
          environment: 'staging',
          debug: false,
          tracesSampleRate: expect.any(Number),
          profilesSampleRate: expect.any(Number),
        })
      );
    });

    test('should load production configuration correctly', () => {
      process.env.NODE_ENV = 'production';
      process.env.NEXT_PUBLIC_ENVIRONMENT = 'production';
      process.env.NEXT_PUBLIC_SENTRY_DSN = 'https://production@sentry.io/456';
      
      render(<SentryInit />);
      
      expect(mockSentryInit).toHaveBeenCalledWith(
        expect.objectContaining({
          dsn: 'https://production@sentry.io/456',
          environment: 'production',
          debug: false,
          tracesSampleRate: expect.any(Number),
          profilesSampleRate: expect.any(Number),
        })
      );
    });

    test('should use development environment settings when NODE_ENV is development', () => {
      process.env.NODE_ENV = 'development';
      process.env.NEXT_PUBLIC_ENVIRONMENT = 'development';
      process.env.NEXT_PUBLIC_SENTRY_DSN = 'https://dev@sentry.io/789';
      
      render(<SentryInit />);
      
      // Should not initialize in development
      expect(mockSentryInit).not.toHaveBeenCalled();
    });

    test('should handle missing NEXT_PUBLIC_ENVIRONMENT gracefully', () => {
      process.env.NODE_ENV = 'production';
      delete process.env.NEXT_PUBLIC_ENVIRONMENT;
      process.env.NEXT_PUBLIC_SENTRY_DSN = 'https://default@sentry.io/123';
      
      render(<SentryInit />);
      
      expect(mockSentryInit).toHaveBeenCalledWith(
        expect.objectContaining({
          environment: 'production', // Should default to NODE_ENV
        })
      );
    });
  });

  describe('Sample Rate Configuration', () => {
    beforeEach(() => {
      process.env.NODE_ENV = 'production';
      process.env.NEXT_PUBLIC_ENVIRONMENT = 'staging';
      process.env.NEXT_PUBLIC_SENTRY_DSN = 'https://test@sentry.io/123';
    });

    test('should use default sample rates when not specified', () => {
      render(<SentryInit />);
      
      const initCall = mockSentryInit.mock.calls[0][0];
      expect(initCall.tracesSampleRate).toBeGreaterThan(0);
      expect(initCall.tracesSampleRate).toBeLessThanOrEqual(1);
      expect(initCall.profilesSampleRate).toBeGreaterThan(0);
      expect(initCall.profilesSampleRate).toBeLessThanOrEqual(1);
    });

    test('should use custom traces sample rate from environment', () => {
      process.env.NEXT_PUBLIC_SENTRY_TRACES_SAMPLE_RATE = '0.5';
      
      render(<SentryInit />);
      
      expect(mockSentryInit).toHaveBeenCalledWith(
        expect.objectContaining({
          tracesSampleRate: 0.5,
        })
      );
    });

    test('should use custom profiles sample rate from environment', () => {
      process.env.NEXT_PUBLIC_SENTRY_PROFILES_SAMPLE_RATE = '0.25';
      
      render(<SentryInit />);
      
      expect(mockSentryInit).toHaveBeenCalledWith(
        expect.objectContaining({
          profilesSampleRate: 0.25,
        })
      );
    });

    test('should handle invalid sample rate values gracefully', () => {
      process.env.NEXT_PUBLIC_SENTRY_TRACES_SAMPLE_RATE = 'invalid';
      process.env.NEXT_PUBLIC_SENTRY_PROFILES_SAMPLE_RATE = '2.5'; // > 1.0
      
      render(<SentryInit />);
      
      const initCall = mockSentryInit.mock.calls[0][0];
      expect(initCall.tracesSampleRate).toBeGreaterThan(0);
      expect(initCall.tracesSampleRate).toBeLessThanOrEqual(1);
      expect(initCall.profilesSampleRate).toBeGreaterThan(0);
      expect(initCall.profilesSampleRate).toBeLessThanOrEqual(1);
    });

    test('should use higher sample rates for staging environment', () => {
      process.env.NEXT_PUBLIC_ENVIRONMENT = 'staging';
      
      render(<SentryInit />);
      
      const initCall = mockSentryInit.mock.calls[0][0];
      expect(initCall.tracesSampleRate).toBeGreaterThanOrEqual(0.1); // At least 10%
    });

    test('should use conservative sample rates for production environment', () => {
      process.env.NEXT_PUBLIC_ENVIRONMENT = 'production';
      
      render(<SentryInit />);
      
      const initCall = mockSentryInit.mock.calls[0][0];
      expect(initCall.tracesSampleRate).toBeLessThanOrEqual(0.5); // Max 50%
    });
  });

  describe('Debug Configuration', () => {
    beforeEach(() => {
      process.env.NODE_ENV = 'production';
      process.env.NEXT_PUBLIC_SENTRY_DSN = 'https://test@sentry.io/123';
    });

    test('should disable debug by default', () => {
      render(<SentryInit />);
      
      expect(mockSentryInit).toHaveBeenCalledWith(
        expect.objectContaining({
          debug: false,
        })
      );
    });

    test('should enable debug when explicitly set', () => {
      process.env.NEXT_PUBLIC_SENTRY_DEBUG = 'true';
      
      render(<SentryInit />);
      
      expect(mockSentryInit).toHaveBeenCalledWith(
        expect.objectContaining({
          debug: true,
        })
      );
    });

    test('should handle various debug flag formats', () => {
      const testCases = ['1', 'yes', 'on', 'enabled'];
      
      testCases.forEach((debugValue) => {
        jest.clearAllMocks();
        process.env.NEXT_PUBLIC_SENTRY_DEBUG = debugValue;
        
        render(<SentryInit />);
        
        expect(mockSentryInit).toHaveBeenCalledWith(
          expect.objectContaining({
            debug: true,
          })
        );
      });
    });
  });

  describe('Invalid Configuration Handling', () => {
    test('should not initialize with invalid DSN format', () => {
      process.env.NODE_ENV = 'production';
      process.env.NEXT_PUBLIC_ENVIRONMENT = 'staging';
      
      const invalidDSNs = [
        'not-a-url',
        'http://insecure@sentry.io/123',
        'ftp://wrong-protocol@sentry.io/123',
        '',
        '   ',
        'javascript:alert(1)',
      ];
      
      invalidDSNs.forEach((invalidDSN) => {
        jest.clearAllMocks();
        process.env.NEXT_PUBLIC_SENTRY_DSN = invalidDSN;
        
        render(<SentryInit />);
        
        expect(mockSentryInit).not.toHaveBeenCalled();
      });
    });

    test('should validate DSN belongs to sentry.io domain', () => {
      process.env.NODE_ENV = 'production';
      process.env.NEXT_PUBLIC_ENVIRONMENT = 'staging';
      
      const suspiciousDSNs = [
        'https://test@malicious.com/123',
        'https://test@fake-sentry.com/123',
        'https://test@sentry.malicious.com/123',
      ];
      
      suspiciousDSNs.forEach((suspiciousDSN) => {
        jest.clearAllMocks();
        process.env.NEXT_PUBLIC_SENTRY_DSN = suspiciousDSN;
        
        render(<SentryInit />);
        
        expect(mockSentryInit).not.toHaveBeenCalled();
      });
    });

    test('should accept valid sentry.io and sentry-like domains', () => {
      process.env.NODE_ENV = 'production';
      process.env.NEXT_PUBLIC_ENVIRONMENT = 'staging';
      
      const validDSNs = [
        'https://test@sentry.io/123',
        'https://test@o123.ingest.sentry.io/456',
        'https://test@us-east-1.ingest.sentry.io/789',
      ];
      
      validDSNs.forEach((validDSN) => {
        jest.clearAllMocks();
        process.env.NEXT_PUBLIC_SENTRY_DSN = validDSN;
        
        render(<SentryInit />);
        
        expect(mockSentryInit).toHaveBeenCalledWith(
          expect.objectContaining({
            dsn: validDSN,
          })
        );
      });
    });
  });

  describe('Multiple Instance Prevention Logic', () => {
    test('should detect already initialized Sentry instances', () => {
      process.env.NODE_ENV = 'production';
      process.env.NEXT_PUBLIC_ENVIRONMENT = 'staging';
      process.env.NEXT_PUBLIC_SENTRY_DSN = 'https://test@sentry.io/123';
      
      mockSentryIsInitialized.mockReturnValue(true);
      
      render(<SentryInit />);
      
      expect(mockSentryInit).not.toHaveBeenCalled();
    });

    test('should prevent configuration conflicts between environments', () => {
      process.env.NODE_ENV = 'production';
      process.env.NEXT_PUBLIC_ENVIRONMENT = 'staging';
      process.env.NEXT_PUBLIC_SENTRY_DSN = 'https://staging@sentry.io/123';
      
      // First render - should initialize
      const { unmount } = render(<SentryInit />);
      expect(mockSentryInit).toHaveBeenCalledTimes(1);
      
      unmount();
      jest.clearAllMocks();
      
      // Change environment and try to reinitialize
      process.env.NEXT_PUBLIC_ENVIRONMENT = 'production';
      process.env.NEXT_PUBLIC_SENTRY_DSN = 'https://production@sentry.io/456';
      mockSentryIsInitialized.mockReturnValue(true);
      
      render(<SentryInit />);
      
      // Should not reinitialize
      expect(mockSentryInit).not.toHaveBeenCalled();
    });
  });

  describe('Error Filtering Configuration', () => {
    beforeEach(() => {
      process.env.NODE_ENV = 'production';
      process.env.NEXT_PUBLIC_ENVIRONMENT = 'staging';
      process.env.NEXT_PUBLIC_SENTRY_DSN = 'https://test@sentry.io/123';
    });

    test('should include beforeSend filter function', () => {
      render(<SentryInit />);
      
      const initCall = mockSentryInit.mock.calls[0][0];
      expect(initCall.beforeSend).toBeDefined();
      expect(typeof initCall.beforeSend).toBe('function');
    });

    test('should filter out development-related errors', () => {
      render(<SentryInit />);
      
      const initCall = mockSentryInit.mock.calls[0][0];
      const beforeSend = initCall.beforeSend;
      
      const devError = {
        exception: {
          values: [{
            value: 'ChunkLoadError: Loading chunk 123 failed',
          }],
        },
      };
      
      const result = beforeSend(devError, {});
      expect(result).toBeNull(); // Should filter out
    });

    test('should allow production errors to pass through', () => {
      render(<SentryInit />);
      
      const initCall = mockSentryInit.mock.calls[0][0];
      const beforeSend = initCall.beforeSend;
      
      const prodError = {
        exception: {
          values: [{
            value: 'TypeError: Cannot read property of undefined',
          }],
        },
      };
      
      const result = beforeSend(prodError, {});
      expect(result).toEqual(prodError); // Should pass through
    });

    test('should sanitize sensitive information from error reports', () => {
      render(<SentryInit />);
      
      const initCall = mockSentryInit.mock.calls[0][0];
      const beforeSend = initCall.beforeSend;
      
      const errorWithSensitiveData = {
        exception: {
          values: [{
            value: 'Error with password=secret123 and token=abc',
          }],
        },
        request: {
          headers: {
            authorization: 'Bearer secret-token',
          },
        },
      };
      
      const result = beforeSend(errorWithSensitiveData, {});
      expect(result?.exception?.values[0]?.value).not.toContain('secret123');
      expect(result?.request?.headers?.authorization).toBe('[Filtered]');
    });
  });

  describe('Performance Monitoring Configuration', () => {
    beforeEach(() => {
      process.env.NODE_ENV = 'production';
      process.env.NEXT_PUBLIC_ENVIRONMENT = 'staging';
      process.env.NEXT_PUBLIC_SENTRY_DSN = 'https://test@sentry.io/123';
    });

    test('should include performance monitoring integrations', () => {
      render(<SentryInit />);
      
      const initCall = mockSentryInit.mock.calls[0][0];
      expect(initCall.integrations).toBeDefined();
      expect(Array.isArray(initCall.integrations)).toBe(true);
    });

    test('should configure transaction names appropriately', () => {
      render(<SentryInit />);
      
      const initCall = mockSentryInit.mock.calls[0][0];
      expect(initCall.beforeTransaction).toBeDefined();
      expect(typeof initCall.beforeTransaction).toBe('function');
    });
  });
});