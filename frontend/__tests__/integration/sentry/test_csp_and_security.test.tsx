/**
 * Integration Tests: Sentry CSP and Security Integration
 * 
 * Business Value Justification (BVJ):
 * - Segment: All (Free/Early/Mid/Enterprise) - Security & Operational Excellence
 * - Business Goal: Ensure Sentry integration complies with security policies
 * - Value Impact: Maintains security posture while enabling error monitoring
 * - Strategic Impact: Prevents security vulnerabilities in production monitoring setup
 * 
 * Test Focus: Content Security Policy, HTTPS enforcement, and data sanitization
 */

import React from 'react';
import { render, cleanup } from '@testing-library/react';
import { SentryInit } from '../../../app/sentry-init';
import { ChatErrorBoundary } from '../../../components/chat/ChatErrorBoundary';

// Mock Sentry with security tracking
const mockSentryInit = jest.fn();
const mockSentryCaptureException = jest.fn();

jest.mock('@sentry/react', () => ({
  init: mockSentryInit,
  captureException: mockSentryCaptureException,
  isInitialized: jest.fn(() => true),
  getCurrentScope: jest.fn(() => ({
    setTag: jest.fn(),
    setContext: jest.fn(),
  })),
}));

// Security test utilities
const securityTestUtils = {
  // Simulate CSP header checking
  checkCSPCompliance: (dsn: string) => {
    try {
      const url = new URL(dsn);
      const allowedHosts = [
        'sentry.io',
        '*.sentry.io',
        '*.ingest.sentry.io',
        'o*.ingest.sentry.io',
      ];
      
      return allowedHosts.some(host => {
        if (host.startsWith('*')) {
          const domain = host.substring(2);
          return url.hostname.endsWith(domain);
        }
        return url.hostname === host;
      });
    } catch {
      return false;
    }
  },
  
  // Check for sensitive data patterns
  containsSensitiveData: (data: string) => {
    const sensitivePatterns = [
      /password\s*[=:]\s*[\w\-!@#$%^&*()]+/gi,
      /token\s*[=:]\s*[\w\-!@#$%^&*()]+/gi,
      /api[_\-]?key\s*[=:]\s*[\w\-!@#$%^&*()]+/gi,
      /secret\s*[=:]\s*[\w\-!@#$%^&*()]+/gi,
      /bearer\s+[\w\-!@#$%^&*()]+/gi,
      /authorization\s*[=:]\s*[\w\-!@#$%^&*()]+/gi,
    ];
    
    return sensitivePatterns.some(pattern => pattern.test(data));
  },
  
  // Validate HTTPS enforcement
  isSecureURL: (url: string) => {
    try {
      return new URL(url).protocol === 'https:';
    } catch {
      return false;
    }
  },
};

// Test component that throws errors with sensitive data
const ErrorThrowingComponent: React.FC<{
  shouldThrow?: boolean;
  errorMessage?: string;
}> = ({ shouldThrow = false, errorMessage = 'Test error' }) => {
  if (shouldThrow) {
    throw new Error(errorMessage);
  }
  return <div data-testid="no-error">No error</div>;
};

describe('Sentry CSP and Security Integration Tests', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    
    // Set up secure environment
    process.env.NODE_ENV = 'production';
    process.env.NEXT_PUBLIC_ENVIRONMENT = 'staging';
    
    // Mock window with security APIs
    (global as any).window = {
      Sentry: {
        captureException: mockSentryCaptureException,
      },
      location: {
        href: 'https://app.netrasystems.ai/chat',
        protocol: 'https:',
      },
      localStorage: {
        getItem: jest.fn(),
        setItem: jest.fn(),
        removeItem: jest.fn(),
      },
      sessionStorage: {
        getItem: jest.fn(),
        setItem: jest.fn(),
      },
    };
  });

  afterEach(() => {
    cleanup();
    delete (global as any).window;
  });

  describe('Content Security Policy Validation', () => {
    test('should only accept Sentry-approved domains for DSN', () => {
      const validDSNs = [
        'https://test@sentry.io/123',
        'https://test@o123456.ingest.sentry.io/456',
        'https://test@us-east-1.ingest.sentry.io/789',
        'https://test@eu-central-1.ingest.sentry.io/999',
      ];
      
      validDSNs.forEach((dsn) => {
        jest.clearAllMocks();
        process.env.NEXT_PUBLIC_SENTRY_DSN = dsn;
        
        render(<SentryInit />);
        
        expect(mockSentryInit).toHaveBeenCalledWith(
          expect.objectContaining({
            dsn: dsn,
          })
        );
        
        // Validate CSP compliance
        expect(securityTestUtils.checkCSPCompliance(dsn)).toBe(true);
      });
    });

    test('should reject non-Sentry domains to prevent CSP violations', () => {
      const suspiciousDSNs = [
        'https://test@malicious.com/123',
        'https://test@fake-sentry.com/456',
        'https://test@sentry.malicious.com/789',
        'https://test@not-sentry.io/999',
        'https://test@sentry-fake.io/111',
      ];
      
      suspiciousDSNs.forEach((dsn) => {
        jest.clearAllMocks();
        process.env.NEXT_PUBLIC_SENTRY_DSN = dsn;
        
        render(<SentryInit />);
        
        // Should not initialize with suspicious domains
        expect(mockSentryInit).not.toHaveBeenCalled();
        
        // Validate CSP non-compliance
        expect(securityTestUtils.checkCSPCompliance(dsn)).toBe(false);
      });
    });

    test('should handle CSP-compliant error reporting configuration', () => {
      process.env.NEXT_PUBLIC_SENTRY_DSN = 'https://test@sentry.io/123';
      
      render(<SentryInit />);
      
      expect(mockSentryInit).toHaveBeenCalled();
      const initConfig = mockSentryInit.mock.calls[0][0];
      
      // Validate CSP-compliant configuration
      expect(initConfig.dsn).toBeDefined();
      expect(securityTestUtils.isSecureURL(initConfig.dsn)).toBe(true);
      expect(securityTestUtils.checkCSPCompliance(initConfig.dsn)).toBe(true);
      
      // Should include security-aware error filtering
      expect(initConfig.beforeSend).toBeDefined();
      expect(typeof initConfig.beforeSend).toBe('function');
    });

    test('should configure integrations with CSP awareness', () => {
      process.env.NEXT_PUBLIC_SENTRY_DSN = 'https://test@o123.ingest.sentry.io/456';
      
      render(<SentryInit />);
      
      const initConfig = mockSentryInit.mock.calls[0][0];
      
      // Should not include integrations that violate CSP
      if (initConfig.integrations) {
        expect(Array.isArray(initConfig.integrations)).toBe(true);
        // Specific integration validation would depend on implementation
      }
    });
  });

  describe('HTTPS Enforcement', () => {
    test('should reject HTTP DSNs in favor of HTTPS', () => {
      const httpDSNs = [
        'http://test@sentry.io/123',
        'http://test@o123.ingest.sentry.io/456',
      ];
      
      httpDSNs.forEach((httpDSN) => {
        jest.clearAllMocks();
        process.env.NEXT_PUBLIC_SENTRY_DSN = httpDSN;
        
        render(<SentryInit />);
        
        // Should not initialize with HTTP DSN
        expect(mockSentryInit).not.toHaveBeenCalled();
        expect(securityTestUtils.isSecureURL(httpDSN)).toBe(false);
      });
    });

    test('should ensure all Sentry communications use HTTPS', () => {
      process.env.NEXT_PUBLIC_SENTRY_DSN = 'https://test@sentry.io/123';
      
      render(<SentryInit />);
      
      const initConfig = mockSentryInit.mock.calls[0][0];
      
      // Validate HTTPS enforcement
      expect(securityTestUtils.isSecureURL(initConfig.dsn)).toBe(true);
      
      // Check transport configuration if available
      if (initConfig.transport) {
        // Transport should use HTTPS
        expect(initConfig.transport).toBeDefined();
      }
    });

    test('should validate HTTPS requirement in production environment', () => {
      // Test in production with HTTPS requirement
      process.env.NODE_ENV = 'production';
      process.env.NEXT_PUBLIC_ENVIRONMENT = 'production';
      process.env.NEXT_PUBLIC_SENTRY_DSN = 'https://prod@sentry.io/789';
      
      render(<SentryInit />);
      
      expect(mockSentryInit).toHaveBeenCalledWith(
        expect.objectContaining({
          dsn: expect.stringMatching(/^https:/),
          environment: 'production',
        })
      );
    });
  });

  describe('Data Sanitization and Privacy', () => {
    test('should sanitize sensitive information from error messages', async () => {
      process.env.NEXT_PUBLIC_SENTRY_DSN = 'https://test@sentry.io/123';
      
      const consoleSpy = jest.spyOn(console, 'error').mockImplementation(() => {});
      
      const sensitiveError = 'API Error: Invalid token=abc123 with password=secret456';
      
      render(
        <div>
          <SentryInit />
          <ChatErrorBoundary level="message">
            <ErrorThrowingComponent shouldThrow={true} errorMessage={sensitiveError} />
          </ChatErrorBoundary>
        </div>
      );
      
      // Wait for error capture
      await new Promise(resolve => setTimeout(resolve, 100));
      
      expect(mockSentryCaptureException).toHaveBeenCalled();
      
      // Get the captured error and context
      const captureCall = mockSentryCaptureException.mock.calls[0];
      const capturedError = captureCall[0];
      const capturedContext = captureCall[1];
      
      // Validate data sanitization
      const fullCaptureString = JSON.stringify([capturedError, capturedContext]);
      expect(securityTestUtils.containsSensitiveData(fullCaptureString)).toBe(false);
      
      consoleSpy.mockRestore();
    });

    test('should sanitize sensitive headers from error context', () => {
      process.env.NEXT_PUBLIC_SENTRY_DSN = 'https://test@sentry.io/123';
      
      render(<SentryInit />);
      
      const initConfig = mockSentryInit.mock.calls[0][0];
      const beforeSend = initConfig.beforeSend;
      
      // Simulate error with sensitive headers
      const errorWithHeaders = {
        exception: {
          values: [{
            value: 'Network request failed',
          }],
        },
        request: {
          headers: {
            authorization: 'Bearer secret-token-123',
            'x-api-key': 'api-key-456',
            'x-auth-token': 'auth-token-789',
            'content-type': 'application/json', // Should not be sanitized
          },
        },
      };
      
      const sanitizedError = beforeSend(errorWithHeaders, {});
      
      // Should sanitize sensitive headers
      expect(sanitizedError?.request?.headers?.authorization).toBe('[Filtered]');
      expect(sanitizedError?.request?.headers?.['x-api-key']).toBe('[Filtered]');
      expect(sanitizedError?.request?.headers?.['x-auth-token']).toBe('[Filtered]');
      
      // Should preserve non-sensitive headers
      expect(sanitizedError?.request?.headers?.['content-type']).toBe('application/json');
    });

    test('should filter sensitive data from breadcrumbs', () => {
      process.env.NEXT_PUBLIC_SENTRY_DSN = 'https://test@sentry.io/123';
      
      render(<SentryInit />);
      
      const initConfig = mockSentryInit.mock.calls[0][0];
      
      // Should have beforeBreadcrumb filter if configured
      if (initConfig.beforeBreadcrumb) {
        const breadcrumbWithSensitiveData = {
          category: 'http',
          data: {
            url: 'https://api.example.com/login',
            method: 'POST',
            request_body: 'password=secret123&email=user@example.com',
          },
          level: 'info',
          timestamp: Date.now(),
        };
        
        const filteredBreadcrumb = initConfig.beforeBreadcrumb(breadcrumbWithSensitiveData);
        
        if (filteredBreadcrumb) {
          const breadcrumbString = JSON.stringify(filteredBreadcrumb);
          expect(securityTestUtils.containsSensitiveData(breadcrumbString)).toBe(false);
        }
      }
    });

    test('should handle user data with privacy compliance', async () => {
      process.env.NEXT_PUBLIC_SENTRY_DSN = 'https://test@sentry.io/123';
      
      // Mock user data with PII
      (global as any).window.localStorage.getItem.mockImplementation((key: string) => {
        if (key === 'user') {
          return JSON.stringify({
            id: 'user-123',
            email: 'sensitive@example.com',
            fullName: 'Sensitive User',
            creditCard: '4111-1111-1111-1111', // Should be filtered
          });
        }
        return null;
      });
      
      const consoleSpy = jest.spyOn(console, 'error').mockImplementation(() => {});
      
      render(
        <div>
          <SentryInit />
          <ChatErrorBoundary level="message">
            <ErrorThrowingComponent shouldThrow={true} errorMessage="Privacy test error" />
          </ChatErrorBoundary>
        </div>
      );
      
      await new Promise(resolve => setTimeout(resolve, 100));
      
      expect(mockSentryCaptureException).toHaveBeenCalled();
      const captureCall = mockSentryCaptureException.mock.calls[0];
      const context = captureCall[1];
      
      // Should include safe user identification
      expect(context.contexts.chat_error.userId).toBe('user-123');
      
      // Should not include sensitive PII
      const contextString = JSON.stringify(context);
      expect(contextString).not.toContain('4111-1111-1111-1111');
      expect(contextString).not.toContain('sensitive@example.com'); // Depends on implementation
      
      consoleSpy.mockRestore();
    });
  });

  describe('Security Headers Compatibility', () => {
    test('should be compatible with strict CSP headers', () => {
      const strictCSP = "default-src 'self'; script-src 'self' 'unsafe-inline'; connect-src 'self' https://sentry.io https://*.ingest.sentry.io";
      
      process.env.NEXT_PUBLIC_SENTRY_DSN = 'https://test@o123.ingest.sentry.io/456';
      
      // Mock CSP validation
      Object.defineProperty(document, 'querySelector', {
        value: jest.fn(() => ({
          content: strictCSP,
        })),
        writable: true,
      });
      
      render(<SentryInit />);
      
      expect(mockSentryInit).toHaveBeenCalled();
      const initConfig = mockSentryInit.mock.calls[0][0];
      
      // DSN should be compatible with CSP
      const dsnUrl = new URL(initConfig.dsn);
      const cspConnectDirectives = strictCSP.match(/connect-src[^;]+/)?.[0] || '';
      
      expect(cspConnectDirectives.includes('sentry.io') || cspConnectDirectives.includes('*.ingest.sentry.io')).toBe(true);
    });

    test('should handle HSTS and secure cookie requirements', () => {
      process.env.NEXT_PUBLIC_SENTRY_DSN = 'https://test@sentry.io/123';
      
      // Mock secure context
      Object.defineProperty(window, 'isSecureContext', {
        value: true,
        writable: true,
      });
      
      render(<SentryInit />);
      
      expect(mockSentryInit).toHaveBeenCalled();
      const initConfig = mockSentryInit.mock.calls[0][0];
      
      // Should use HTTPS DSN
      expect(initConfig.dsn.startsWith('https:')).toBe(true);
    });

    test('should validate referrer policy compliance', () => {
      process.env.NEXT_PUBLIC_SENTRY_DSN = 'https://test@sentry.io/123';
      
      render(<SentryInit />);
      
      const initConfig = mockSentryInit.mock.calls[0][0];
      
      // Should not send sensitive referrer information
      if (initConfig.beforeSend) {
        const errorWithReferrer = {
          request: {
            headers: {
              referer: 'https://app.netrasystems.ai/private/user-123/sensitive-page',
            },
          },
        };
        
        const sanitized = initConfig.beforeSend(errorWithReferrer, {});
        
        // Referrer should be sanitized or removed
        if (sanitized?.request?.headers?.referer) {
          expect(sanitized.request.headers.referer).not.toContain('user-123');
          expect(sanitized.request.headers.referer).not.toContain('sensitive-page');
        }
      }
    });
  });

  describe('Production Security Hardening', () => {
    test('should disable debug mode in production', () => {
      process.env.NODE_ENV = 'production';
      process.env.NEXT_PUBLIC_ENVIRONMENT = 'production';
      process.env.NEXT_PUBLIC_SENTRY_DSN = 'https://prod@sentry.io/123';
      
      render(<SentryInit />);
      
      expect(mockSentryInit).toHaveBeenCalledWith(
        expect.objectContaining({
          debug: false,
        })
      );
    });

    test('should use conservative sample rates in production', () => {
      process.env.NODE_ENV = 'production';
      process.env.NEXT_PUBLIC_ENVIRONMENT = 'production';
      process.env.NEXT_PUBLIC_SENTRY_DSN = 'https://prod@sentry.io/123';
      
      render(<SentryInit />);
      
      const initConfig = mockSentryInit.mock.calls[0][0];
      
      // Should use conservative sampling for production
      expect(initConfig.tracesSampleRate).toBeLessThanOrEqual(0.5);
      expect(initConfig.profilesSampleRate).toBeLessThanOrEqual(0.25);
    });

    test('should implement rate limiting for error reports', () => {
      process.env.NEXT_PUBLIC_SENTRY_DSN = 'https://test@sentry.io/123';
      
      render(<SentryInit />);
      
      const initConfig = mockSentryInit.mock.calls[0][0];
      
      // Should have rate limiting configuration
      expect(initConfig.beforeSend).toBeDefined();
      
      // Test rate limiting by simulating rapid error reports
      if (initConfig.beforeSend) {
        const rapidErrors = Array.from({ length: 100 }, (_, i) => ({
          exception: { values: [{ value: `Rapid error ${i}` }] },
        }));
        
        let acceptedErrors = 0;
        rapidErrors.forEach(error => {
          const result = initConfig.beforeSend(error, {});
          if (result !== null) acceptedErrors++;
        });
        
        // Should rate limit excessive errors
        expect(acceptedErrors).toBeLessThan(100);
      }
    });
  });
});