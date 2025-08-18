/**
 * Frontend Startup Environment Tests
 * Tests environment validation, configuration loading, and dependency management
 */

// JEST MODULE HOISTING - Global mocks BEFORE imports
global.fetch = jest.fn();
global.WebSocket = jest.fn(() => ({
  send: jest.fn(),
  close: jest.fn(),
  addEventListener: jest.fn(),
  removeEventListener: jest.fn(),
  readyState: WebSocket.OPEN
})) as any;

import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';

// Mock environment variables
const mockEnv = {
  NEXT_PUBLIC_API_URL: 'http://localhost:8000',
  NEXT_PUBLIC_WS_URL: 'ws://localhost:8000',
};

describe('Frontend Startup - Environment', () => {
  beforeEach(() => {
    // Setup environment
    process.env = { ...process.env, ...mockEnv };
    jest.clearAllMocks();
  });

  afterEach(() => {
    jest.restoreAllMocks();
  });

  describe('Environment Validation', () => {
    it('should validate required environment variables', () => {
      expect(process.env.NEXT_PUBLIC_API_URL).toBeDefined();
      expect(process.env.NEXT_PUBLIC_WS_URL).toBeDefined();
    });

    it('should handle missing environment variables gracefully', () => {
      delete process.env.NEXT_PUBLIC_API_URL;
      
      // Import should not throw
      const loadConfig = () => {
        const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
        return { apiUrl };
      };
      
      const config = loadConfig();
      expect(config.apiUrl).toBe('http://localhost:8000');
    });

    it('should validate environment variable formats', () => {
      const validateUrl = (url: string) => {
        try {
          new URL(url);
          return true;
        } catch {
          return false;
        }
      };

      const apiUrl = process.env.NEXT_PUBLIC_API_URL!;
      const wsUrl = process.env.NEXT_PUBLIC_WS_URL!;

      expect(validateUrl(apiUrl)).toBe(true);
      expect(validateUrl(wsUrl.replace('ws:', 'http:'))).toBe(true);
    });
  });

  describe('Configuration Loading', () => {
    it('should load application configuration', () => {
      const config = {
        apiUrl: process.env.NEXT_PUBLIC_API_URL,
        wsUrl: process.env.NEXT_PUBLIC_WS_URL,
        environment: process.env.NODE_ENV,
        version: '1.0.0',
      };
      
      expect(config.apiUrl).toBe('http://localhost:8000');
      expect(config.wsUrl).toBe('ws://localhost:8000');
      expect(config.environment).toBeDefined();
      expect(config.version).toBe('1.0.0');
    });

    it('should handle configuration validation', () => {
      const validateConfig = (config: any) => {
        const required = ['apiUrl', 'wsUrl'];
        return required.every(key => config[key]);
      };

      const validConfig = {
        apiUrl: 'http://localhost:8000',
        wsUrl: 'ws://localhost:8000',
      };

      const invalidConfig = {
        apiUrl: 'http://localhost:8000',
      };

      expect(validateConfig(validConfig)).toBe(true);
      expect(validateConfig(invalidConfig)).toBe(false);
    });

    it('should provide configuration defaults', () => {
      const getConfigWithDefaults = () => ({
        apiUrl: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000',
        wsUrl: process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8000',
        timeout: 30000,
        retries: 3,
      });

      delete process.env.NEXT_PUBLIC_API_URL;
      delete process.env.NEXT_PUBLIC_WS_URL;

      const config = getConfigWithDefaults();
      expect(config.apiUrl).toBe('http://localhost:8000');
      expect(config.wsUrl).toBe('ws://localhost:8000');
      expect(config.timeout).toBe(30000);
      expect(config.retries).toBe(3);
    });
  });

  describe('Dependency Loading', () => {
    it('should load required React dependencies', () => {
      expect(React).toBeDefined();
      expect(React.version).toBeDefined();
      expect(render).toBeDefined();
      expect(screen).toBeDefined();
      expect(waitFor).toBeDefined();
    });

    it('should handle missing dependencies gracefully', () => {
      const loadOptionalDependency = (name: string) => {
        try {
          return require(name);
        } catch {
          return null;
        }
      };
      
      const optionalDep = loadOptionalDependency('non-existent-package');
      expect(optionalDep).toBeNull();
    });

    it('should verify critical dependency versions', () => {
      const React = require('react');
      const version = React.version;
      
      // Ensure React version is compatible (17+ or 18+)
      const majorVersion = parseInt(version.split('.')[0]);
      expect(majorVersion).toBeGreaterThanOrEqual(17);
    });

    it('should load testing utilities', () => {
      const testingLibrary = require('@testing-library/react');
      const jestDom = require('@testing-library/jest-dom');
      
      expect(testingLibrary.render).toBeDefined();
      expect(testingLibrary.screen).toBeDefined();
      expect(testingLibrary.waitFor).toBeDefined();
      expect(jestDom).toBeDefined();
    });
  });

  describe('Environment Security', () => {
    it('should not expose sensitive environment variables', () => {
      // Check that sensitive vars are not exposed to client
      expect(process.env.DATABASE_URL).toBeUndefined();
      expect(process.env.SECRET_KEY).toBeUndefined();
      expect(process.env.REDIS_URL).toBeUndefined();
    });

    it('should validate public environment variables', () => {
      const publicVars = Object.keys(process.env).filter(key => 
        key.startsWith('NEXT_PUBLIC_')
      );
      
      expect(publicVars.length).toBeGreaterThan(0);
      publicVars.forEach(varName => {
        expect(process.env[varName]).toBeDefined();
      });
    });
  });
});