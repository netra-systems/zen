/**
 * Regression Test: API URL Configuration
 * 
 * CRITICAL: This test prevents the frontend from making API calls to the wrong domain.
 * 
 * Background: Frontend was making calls to /api/agents/* which resolved to the frontend
 * domain (app.staging.netrasystems.ai) instead of the backend API domain 
 * (api.staging.netrasystems.ai), causing 404 errors.
 * 
 * This test ensures all API calls use absolute URLs with the correct backend domain.
 */

import { renderHook } from '@testing-library/react';
import { getUnifiedApiConfig } from '@/lib/unified-api-config';
import { API_BASE_URL } from '@/lib/secure-api-config';

// Mock fetch to track URL calls
const mockFetch = jest.fn();
global.fetch = mockFetch;

describe('API URL Configuration Regression Test', () => {
  beforeEach(() => {
    mockFetch.mockClear();
    // Set staging environment
    process.env.NEXT_PUBLIC_ENVIRONMENT = 'staging';
    process.env.NODE_ENV = 'production';
  });

  afterEach(() => {
    jest.clearAllMocks();
  });

  describe('Configuration Validation', () => {
    it('should use backend API domain in staging environment', () => {
      const config = getUnifiedApiConfig();
      
      // In staging, API URL must be the backend domain
      expect(config.urls.api).toBe('https://api.staging.netrasystems.ai');
      expect(config.urls.api).not.toContain('app.staging');
      expect(config.urls.api).toContain('api.staging');
    });

    it('should use backend API domain in production environment', () => {
      process.env.NEXT_PUBLIC_ENVIRONMENT = 'production';
      const config = getUnifiedApiConfig();
      
      // In production, API URL must be the backend domain
      expect(config.urls.api).toBe('https://api.netrasystems.ai');
      expect(config.urls.api).not.toContain('app.');
      expect(config.urls.api).toContain('api.');
    });

    it('should export correct API_BASE_URL for backward compatibility', () => {
      const config = getUnifiedApiConfig();
      
      // API_BASE_URL should match config.urls.api
      expect(API_BASE_URL).toBe(config.urls.api);
      expect(API_BASE_URL).toContain('api.staging');
    });
  });

  describe('Agent Endpoint URLs', () => {
    it('should NEVER use relative URLs for agent endpoints', () => {
      // This test checks that we're not using relative URLs
      const badPatterns = [
        '/api/agents/triage',
        '/api/agents/data', 
        '/api/agents/optimization',
        '/api/agents/execute'
      ];
      
      // Import the hook source to check for relative URLs
      // This is a static analysis test
      const hookSource = require('!!raw-loader!@/components/chat/hooks/useMessageSending').default;
      
      badPatterns.forEach(pattern => {
        // Check that fetch is never called with just the relative path
        const hasRelativeUrl = hookSource.includes(`fetch('${pattern}'`) || 
                              hookSource.includes(`fetch("${pattern}"`) ||
                              hookSource.includes(`fetch(\`${pattern}\``);
        
        expect(hasRelativeUrl).toBe(false);
      });
    });

    it('should construct agent URLs with backend API domain', () => {
      const config = getUnifiedApiConfig();
      const agentTypes = ['triage', 'data', 'optimization'];
      
      agentTypes.forEach(agentType => {
        const url = `${config.urls.api}/api/agents/${agentType}`;
        
        // URL must be absolute
        expect(url).toMatch(/^https?:\/\//);
        
        // URL must use backend domain
        expect(url).toContain('api.staging.netrasystems.ai');
        expect(url).not.toContain('app.staging');
        
        // URL must have correct path
        expect(url).toContain(`/api/agents/${agentType}`);
      });
    });
  });

  describe('useMessageSending Hook Integration', () => {
    it('should import getUnifiedApiConfig', () => {
      // Check that the hook imports the config function
      const hookSource = require('!!raw-loader!@/components/chat/hooks/useMessageSending').default;
      
      expect(hookSource).toContain("import { getUnifiedApiConfig }");
      expect(hookSource).toContain("from '@/lib/unified-api-config'");
    });

    it('should use config.urls.api for agent endpoints', () => {
      // Check that the hook uses the API URL from config
      const hookSource = require('!!raw-loader!@/components/chat/hooks/useMessageSending').default;
      
      expect(hookSource).toContain("getUnifiedApiConfig()");
      expect(hookSource).toContain("config.urls.api");
      expect(hookSource).toContain("${apiUrl}/api/agents/");
    });
  });

  describe('Environment-Specific Validation', () => {
    const environments = [
      { name: 'development', expectedApi: 'http://localhost:8000' },
      { name: 'staging', expectedApi: 'https://api.staging.netrasystems.ai' },
      { name: 'production', expectedApi: 'https://api.netrasystems.ai' }
    ];

    environments.forEach(({ name, expectedApi }) => {
      it(`should use correct API URL in ${name} environment`, () => {
        process.env.NEXT_PUBLIC_ENVIRONMENT = name;
        process.env.NODE_ENV = name === 'development' ? 'development' : 'production';
        
        const config = getUnifiedApiConfig();
        
        expect(config.urls.api).toBe(expectedApi);
        
        // Construct agent URL
        const agentUrl = `${config.urls.api}/api/agents/triage`;
        
        // Validate URL structure
        if (name !== 'development') {
          expect(agentUrl).toMatch(/^https:\/\//);
          expect(agentUrl).toContain('api.');
          expect(agentUrl).not.toContain('app.');
        }
      });
    });
  });

  describe('Common Mistakes Prevention', () => {
    it('should not allow fetch calls without domain prefix', () => {
      // Mock a fetch call with relative URL (wrong way)
      const wrongFetch = () => fetch('/api/agents/triage');
      
      // This would go to the frontend domain in production
      // We need to ensure this pattern is not used
      const hookSource = require('!!raw-loader!@/components/chat/hooks/useMessageSending').default;
      
      // Check that fetch is always called with a variable containing the domain
      const fetchCalls = hookSource.match(/fetch\([^)]+\)/g) || [];
      
      fetchCalls.forEach(call => {
        // Skip WebSocket or other non-agent calls
        if (call.includes('agents')) {
          // Must use template literal or variable with apiUrl
          expect(call).toMatch(/\$\{apiUrl\}|apiUrl \+/);
        }
      });
    });

    it('should validate all API endpoint constructions use absolute URLs', () => {
      const config = getUnifiedApiConfig();
      
      // All endpoints should be absolute URLs
      Object.entries(config.endpoints).forEach(([key, value]) => {
        if (typeof value === 'string' && value.startsWith('/')) {
          // This is a relative URL - should not happen for external API calls
          if (key !== 'websocket') { // WebSocket might be relative for upgrade
            fail(`Endpoint ${key} uses relative URL: ${value}`);
          }
        }
      });
    });
  });

  describe('Error Scenarios', () => {
    it('should handle missing environment configuration gracefully', () => {
      delete process.env.NEXT_PUBLIC_ENVIRONMENT;
      
      const config = getUnifiedApiConfig();
      
      // Should fall back to development
      expect(config.urls.api).toBe('http://localhost:8000');
      expect(config.environment).toBe('development');
    });

    it('should construct valid URLs even with trailing slashes', () => {
      const config = getUnifiedApiConfig();
      const apiUrl = config.urls.api;
      
      // Test with and without trailing slash
      const url1 = `${apiUrl}/api/agents/triage`;
      const url2 = `${apiUrl.replace(/\/$/, '')}/api/agents/triage`;
      
      expect(url1).toBe(url2);
      expect(url1).not.toContain('//api');
    });
  });
});

/**
 * Manual Testing Checklist:
 * 
 * 1. Deploy to staging
 * 2. Open browser DevTools Network tab
 * 3. Send a message in chat that triggers agent (e.g., "test", "analyze")
 * 4. Verify the request goes to api.staging.netrasystems.ai, NOT app.staging.netrasystems.ai
 * 5. Verify no 404 errors for agent endpoints
 * 
 * Expected network request:
 * ✅ https://api.staging.netrasystems.ai/api/agents/triage
 * ❌ https://app.staging.netrasystems.ai/api/agents/triage
 */