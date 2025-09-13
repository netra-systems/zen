/**
 * Integration Tests: Sentry Environment Isolation
 * 
 * Business Value Justification (BVJ):
 * - Segment: All (Free/Early/Mid/Enterprise) - Operational Excellence & Security
 * - Business Goal: Prevent configuration conflicts and ensure environment isolation
 * - Value Impact: Eliminates original "multiple instance" errors and prevents env contamination
 * - Strategic Impact: Enables safe multi-environment deployment without configuration leakage
 * 
 * Test Focus: Environment-specific isolation and configuration conflict prevention
 */

import React from 'react';
import { render, cleanup } from '@testing-library/react';
import { SentryInit } from '../../../app/sentry-init';

// Mock Sentry with environment tracking
const mockSentryInit = jest.fn();
const mockSentryClose = jest.fn();
const mockSentryIsInitialized = jest.fn();
const mockSentryGetCurrentScope = jest.fn();

// Track Sentry instances globally
const sentryInstanceTracker = {
  instances: [] as Array<{
    environment: string;
    dsn: string;
    timestamp: number;
    config: any;
  }>,
  reset: () => {
    sentryInstanceTracker.instances = [];
  },
  addInstance: (config: any) => {
    sentryInstanceTracker.instances.push({
      environment: config.environment || 'unknown',
      dsn: config.dsn || 'unknown',
      timestamp: Date.now(),
      config: { ...config },
    });
  },
  getInstanceCount: () => sentryInstanceTracker.instances.length,
  getEnvironments: () => [...new Set(sentryInstanceTracker.instances.map(i => i.environment))],
};

jest.mock('@sentry/react', () => ({
  init: jest.fn((config) => {
    mockSentryInit(config);
    sentryInstanceTracker.addInstance(config);
  }),
  close: mockSentryClose,
  isInitialized: mockSentryIsInitialized,
  getCurrentScope: mockSentryGetCurrentScope,
}));

describe('Sentry Environment Isolation - Integration Tests', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    sentryInstanceTracker.reset();
    mockSentryIsInitialized.mockReturnValue(false);
    
    // Clear all environment variables
    delete process.env.NODE_ENV;
    delete process.env.NEXT_PUBLIC_ENVIRONMENT;
    delete process.env.NEXT_PUBLIC_SENTRY_DSN;
    delete process.env.NEXT_PUBLIC_SENTRY_DEBUG;
  });

  afterEach(() => {
    cleanup();
  });

  describe('Multi-Environment Configuration Isolation', () => {
    test('should isolate staging environment configuration', () => {
      process.env.NODE_ENV = 'production';
      process.env.NEXT_PUBLIC_ENVIRONMENT = 'staging';
      process.env.NEXT_PUBLIC_SENTRY_DSN = 'https://staging@sentry.io/123';
      
      render(<SentryInit />);
      
      expect(mockSentryInit).toHaveBeenCalledWith(
        expect.objectContaining({
          environment: 'staging',
          dsn: 'https://staging@sentry.io/123',
          tracesSampleRate: expect.any(Number),
          debug: false,
        })
      );
      
      expect(sentryInstanceTracker.getEnvironments()).toEqual(['staging']);
    });

    test('should isolate production environment configuration', () => {
      process.env.NODE_ENV = 'production';
      process.env.NEXT_PUBLIC_ENVIRONMENT = 'production';
      process.env.NEXT_PUBLIC_SENTRY_DSN = 'https://production@sentry.io/456';
      
      render(<SentryInit />);
      
      expect(mockSentryInit).toHaveBeenCalledWith(
        expect.objectContaining({
          environment: 'production',
          dsn: 'https://production@sentry.io/456',
          tracesSampleRate: expect.any(Number),
          debug: false,
        })
      );
      
      expect(sentryInstanceTracker.getEnvironments()).toEqual(['production']);
    });

    test('should never initialize in development environment', () => {
      process.env.NODE_ENV = 'development';
      process.env.NEXT_PUBLIC_ENVIRONMENT = 'development';
      process.env.NEXT_PUBLIC_SENTRY_DSN = 'https://dev@sentry.io/789';
      
      render(<SentryInit />);
      
      expect(mockSentryInit).not.toHaveBeenCalled();
      expect(sentryInstanceTracker.getInstanceCount()).toBe(0);
    });

    test('should never initialize in test environment', () => {
      process.env.NODE_ENV = 'test';
      process.env.NEXT_PUBLIC_ENVIRONMENT = 'test';
      process.env.NEXT_PUBLIC_SENTRY_DSN = 'https://test@sentry.io/999';
      
      render(<SentryInit />);
      
      expect(mockSentryInit).not.toHaveBeenCalled();
      expect(sentryInstanceTracker.getInstanceCount()).toBe(0);
    });
  });

  describe('Environment Variable Isolation', () => {
    test('should use environment-specific DSN values', () => {
      const environments = [
        {
          NODE_ENV: 'production',
          NEXT_PUBLIC_ENVIRONMENT: 'staging',
          NEXT_PUBLIC_SENTRY_DSN: 'https://staging-specific@sentry.io/123',
        },
        {
          NODE_ENV: 'production',
          NEXT_PUBLIC_ENVIRONMENT: 'production',
          NEXT_PUBLIC_SENTRY_DSN: 'https://production-specific@sentry.io/456',
        },
      ];
      
      environments.forEach((env, index) => {
        // Reset environment
        delete process.env.NODE_ENV;
        delete process.env.NEXT_PUBLIC_ENVIRONMENT;
        delete process.env.NEXT_PUBLIC_SENTRY_DSN;
        
        Object.assign(process.env, env);
        jest.clearAllMocks();
        
        const { unmount } = render(<SentryInit />);
        
        expect(mockSentryInit).toHaveBeenCalledWith(
          expect.objectContaining({
            environment: env.NEXT_PUBLIC_ENVIRONMENT,
            dsn: env.NEXT_PUBLIC_SENTRY_DSN,
          })
        );
        
        unmount();
      });
      
      // Should have separate configurations for each environment
      expect(sentryInstanceTracker.getEnvironments()).toEqual(['staging', 'production']);
    });

    test('should handle missing environment variables gracefully', () => {
      process.env.NODE_ENV = 'production';
      delete process.env.NEXT_PUBLIC_ENVIRONMENT;
      delete process.env.NEXT_PUBLIC_SENTRY_DSN;
      
      render(<SentryInit />);
      
      // Should not initialize without DSN
      expect(mockSentryInit).not.toHaveBeenCalled();
      expect(sentryInstanceTracker.getInstanceCount()).toBe(0);
    });

    test('should validate environment variable format and security', () => {
      process.env.NODE_ENV = 'production';
      process.env.NEXT_PUBLIC_ENVIRONMENT = 'staging';
      
      const invalidEnvVars = [
        'http://insecure@sentry.io/123',  // HTTP not allowed
        'https://malicious@evil.com/123', // Non-Sentry domain
        '',                               // Empty string
        'not-a-url',                     // Invalid URL format
        'javascript:alert(1)',           // Security risk
      ];
      
      invalidEnvVars.forEach((invalidDSN, index) => {
        jest.clearAllMocks();
        process.env.NEXT_PUBLIC_SENTRY_DSN = invalidDSN;
        
        render(<SentryInit />);
        
        expect(mockSentryInit).not.toHaveBeenCalled();
      });
      
      expect(sentryInstanceTracker.getInstanceCount()).toBe(0);
    });
  });

  describe('Configuration Conflict Prevention', () => {
    test('should prevent multiple instances in same environment', () => {
      process.env.NODE_ENV = 'production';
      process.env.NEXT_PUBLIC_ENVIRONMENT = 'staging';
      process.env.NEXT_PUBLIC_SENTRY_DSN = 'https://staging@sentry.io/123';
      
      // First instance
      const { unmount: unmount1 } = render(<SentryInit />);
      expect(mockSentryInit).toHaveBeenCalledTimes(1);
      
      // Mock Sentry as initialized
      mockSentryIsInitialized.mockReturnValue(true);
      
      // Second instance - should not initialize
      const { unmount: unmount2 } = render(<SentryInit />);
      expect(mockSentryInit).toHaveBeenCalledTimes(1); // Still only 1
      
      unmount1();
      unmount2();
      
      expect(sentryInstanceTracker.getInstanceCount()).toBe(1);
    });

    test('should handle rapid component mount/unmount without conflicts', () => {
      process.env.NODE_ENV = 'production';
      process.env.NEXT_PUBLIC_ENVIRONMENT = 'staging';
      process.env.NEXT_PUBLIC_SENTRY_DSN = 'https://staging@sentry.io/123';
      
      // Rapid mount/unmount cycles
      const components = [];
      for (let i = 0; i < 10; i++) {
        const { unmount } = render(<SentryInit />);
        components.push(unmount);
        
        if (i === 0) {
          // After first initialization, mock as initialized
          mockSentryIsInitialized.mockReturnValue(true);
        }
      }
      
      // Clean up
      components.forEach(unmount => unmount());
      
      // Should only initialize once despite multiple mount attempts
      expect(mockSentryInit).toHaveBeenCalledTimes(1);
      expect(sentryInstanceTracker.getInstanceCount()).toBe(1);
    });

    test('should prevent environment configuration contamination', () => {
      // Simulate environment change during runtime (should not happen, but test robustness)
      process.env.NODE_ENV = 'production';
      process.env.NEXT_PUBLIC_ENVIRONMENT = 'staging';
      process.env.NEXT_PUBLIC_SENTRY_DSN = 'https://staging@sentry.io/123';
      
      render(<SentryInit />);
      expect(sentryInstanceTracker.getInstanceCount()).toBe(1);
      
      const firstInstance = sentryInstanceTracker.instances[0];
      expect(firstInstance.environment).toBe('staging');
      
      // Change environment variables (simulating contamination attempt)
      process.env.NEXT_PUBLIC_ENVIRONMENT = 'production';
      process.env.NEXT_PUBLIC_SENTRY_DSN = 'https://production@sentry.io/456';
      
      mockSentryIsInitialized.mockReturnValue(true);
      
      // Try to render again - should not create new instance
      render(<SentryInit />);
      
      expect(sentryInstanceTracker.getInstanceCount()).toBe(1);
      expect(sentryInstanceTracker.instances[0]).toEqual(firstInstance);
    });
  });

  describe('Cross-Environment Conflict Detection', () => {
    test('should detect and prevent configuration conflicts between environments', () => {
      // Test sequence: staging -> production (should not override)
      const environments = [
        {
          env: 'staging',
          dsn: 'https://staging@sentry.io/123',
        },
        {
          env: 'production',
          dsn: 'https://production@sentry.io/456',
        },
      ];
      
      process.env.NODE_ENV = 'production';
      
      // Initialize staging first
      process.env.NEXT_PUBLIC_ENVIRONMENT = environments[0].env;
      process.env.NEXT_PUBLIC_SENTRY_DSN = environments[0].dsn;
      
      render(<SentryInit />);
      expect(mockSentryInit).toHaveBeenCalledTimes(1);
      
      const stagingConfig = mockSentryInit.mock.calls[0][0];
      expect(stagingConfig.environment).toBe('staging');
      
      // Mock as initialized
      mockSentryIsInitialized.mockReturnValue(true);
      
      // Try to switch to production (should be prevented)
      process.env.NEXT_PUBLIC_ENVIRONMENT = environments[1].env;
      process.env.NEXT_PUBLIC_SENTRY_DSN = environments[1].dsn;
      
      render(<SentryInit />);
      
      // Should still only have one initialization (staging)
      expect(mockSentryInit).toHaveBeenCalledTimes(1);
      expect(sentryInstanceTracker.getInstanceCount()).toBe(1);
      expect(sentryInstanceTracker.getEnvironments()).toEqual(['staging']);
    });

    test('should maintain environment boundaries across component lifecycles', () => {
      process.env.NODE_ENV = 'production';
      process.env.NEXT_PUBLIC_ENVIRONMENT = 'staging';
      process.env.NEXT_PUBLIC_SENTRY_DSN = 'https://staging@sentry.io/123';
      
      // Component lifecycle simulation
      const lifecycles = [];
      
      for (let cycle = 0; cycle < 5; cycle++) {
        const { unmount } = render(<SentryInit />);
        lifecycles.push(unmount);
        
        if (cycle === 0) {
          mockSentryIsInitialized.mockReturnValue(true);
        }
        
        // Verify configuration remains consistent
        if (mockSentryInit.mock.calls.length > 0) {
          const config = mockSentryInit.mock.calls[0][0];
          expect(config.environment).toBe('staging');
          expect(config.dsn).toBe('https://staging@sentry.io/123');
        }
      }
      
      // Cleanup
      lifecycles.forEach(unmount => unmount());
      
      // Should maintain single environment throughout all lifecycles
      expect(sentryInstanceTracker.getInstanceCount()).toBe(1);
      expect(sentryInstanceTracker.getEnvironments()).toEqual(['staging']);
    });
  });

  describe('Environment-Specific Sample Rate Isolation', () => {
    test('should use different sample rates per environment', () => {
      const testCases = [
        {
          environment: 'staging',
          expectedTracesSampleRate: expect.any(Number),
          minTracesRate: 0.1, // Higher for staging
        },
        {
          environment: 'production',
          expectedTracesSampleRate: expect.any(Number),
          maxTracesRate: 0.5, // Conservative for production
        },
      ];
      
      testCases.forEach(({ environment, expectedTracesSampleRate, minTracesRate, maxTracesRate }) => {
        jest.clearAllMocks();
        sentryInstanceTracker.reset();
        mockSentryIsInitialized.mockReturnValue(false);
        
        process.env.NODE_ENV = 'production';
        process.env.NEXT_PUBLIC_ENVIRONMENT = environment;
        process.env.NEXT_PUBLIC_SENTRY_DSN = `https://${environment}@sentry.io/123`;
        
        render(<SentryInit />);
        
        expect(mockSentryInit).toHaveBeenCalledWith(
          expect.objectContaining({
            environment,
            tracesSampleRate: expectedTracesSampleRate,
          })
        );
        
        const config = mockSentryInit.mock.calls[0][0];
        if (minTracesRate) {
          expect(config.tracesSampleRate).toBeGreaterThanOrEqual(minTracesRate);
        }
        if (maxTracesRate) {
          expect(config.tracesSampleRate).toBeLessThanOrEqual(maxTracesRate);
        }
      });
    });

    test('should isolate custom sample rates per environment', () => {
      const stagingRate = '0.75';
      const productionRate = '0.25';
      
      // Test staging with custom rate
      process.env.NODE_ENV = 'production';
      process.env.NEXT_PUBLIC_ENVIRONMENT = 'staging';
      process.env.NEXT_PUBLIC_SENTRY_DSN = 'https://staging@sentry.io/123';
      process.env.NEXT_PUBLIC_SENTRY_TRACES_SAMPLE_RATE = stagingRate;
      
      render(<SentryInit />);
      
      expect(mockSentryInit).toHaveBeenCalledWith(
        expect.objectContaining({
          environment: 'staging',
          tracesSampleRate: 0.75,
        })
      );
      
      // Clear and test production
      jest.clearAllMocks();
      sentryInstanceTracker.reset();
      mockSentryIsInitialized.mockReturnValue(false);
      
      process.env.NEXT_PUBLIC_ENVIRONMENT = 'production';
      process.env.NEXT_PUBLIC_SENTRY_DSN = 'https://production@sentry.io/456';
      process.env.NEXT_PUBLIC_SENTRY_TRACES_SAMPLE_RATE = productionRate;
      
      render(<SentryInit />);
      
      expect(mockSentryInit).toHaveBeenCalledWith(
        expect.objectContaining({
          environment: 'production',
          tracesSampleRate: 0.25,
        })
      );
    });
  });

  describe('Environment Isolation Security', () => {
    test('should prevent sensitive environment leakage', () => {
      process.env.NODE_ENV = 'production';
      process.env.NEXT_PUBLIC_ENVIRONMENT = 'staging';
      process.env.NEXT_PUBLIC_SENTRY_DSN = 'https://staging@sentry.io/123';
      
      // Add sensitive test environment variables
      process.env.SECRET_KEY = 'super-secret';
      process.env.API_KEY = 'api-secret-123';
      process.env.DATABASE_URL = 'postgres://user:pass@db/name';
      
      render(<SentryInit />);
      
      expect(mockSentryInit).toHaveBeenCalled();
      const config = mockSentryInit.mock.calls[0][0];
      
      // Verify sensitive data is not included in Sentry config
      const configString = JSON.stringify(config);
      expect(configString).not.toContain('super-secret');
      expect(configString).not.toContain('api-secret-123');
      expect(configString).not.toContain('postgres://user:pass');
      
      // Should only contain expected Sentry configuration
      expect(config).toMatchObject({
        dsn: 'https://staging@sentry.io/123',
        environment: 'staging',
        tracesSampleRate: expect.any(Number),
        profilesSampleRate: expect.any(Number),
        beforeSend: expect.any(Function),
      });
    });

    test('should validate environment authenticity', () => {
      process.env.NODE_ENV = 'production';
      
      // Test with suspicious environment names
      const suspiciousEnvironments = [
        'production-dev',
        'staging-prod',
        'development-staging',
        'test-production',
      ];
      
      suspiciousEnvironments.forEach((suspiciousEnv) => {
        jest.clearAllMocks();
        
        process.env.NEXT_PUBLIC_ENVIRONMENT = suspiciousEnv;
        process.env.NEXT_PUBLIC_SENTRY_DSN = 'https://test@sentry.io/123';
        
        render(<SentryInit />);
        
        // Should still initialize (these are valid environment names)
        // but should use the exact environment name provided
        expect(mockSentryInit).toHaveBeenCalledWith(
          expect.objectContaining({
            environment: suspiciousEnv,
          })
        );
      });
    });
  });
});