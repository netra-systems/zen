/**
 * Unified API Configuration System
 * Crystal clear environment detection and URL configuration
 * No localhost references in production/staging
 */

// Removed logger import to prevent circular dependency - using console.log directly

export type Environment = 'development' | 'test' | 'staging' | 'production';

interface UnifiedApiConfig {
  environment: Environment;
  urls: {
    api: string;
    websocket: string;
    auth: string;
    frontend: string;
  };
  endpoints: {
    // Backend API endpoints
    health: string;
    ready: string;
    threads: string;
    websocket: string;
    
    // v1 Agent API endpoints (deprecated)
    agentV1Optimization: string;
    agentV1Data: string;
    agentV1Triage: string;
    
    // v2 Agent API endpoints (new request-scoped)
    agentV2Execute: string;
    
    // Auth service endpoints
    authConfig: string;
    authLogin: string;
    authLogout: string;
    authCallback: string;
    authToken: string;
    authRefresh: string;
    authValidate: string;
    authSession: string;
    authMe: string;
  };
  features: {
    useHttps: boolean;
    useWebSocketSecure: boolean;
    corsEnabled: boolean;
    dynamicDiscovery: boolean;
    // v2 Migration Feature Flags
    enableV2AgentApi: boolean;
    v2MigrationMode: 'disabled' | 'testing' | 'gradual' | 'full';
  };
}

/**
 * Detect current environment with clear precedence
 * 1. NEXT_PUBLIC_ENVIRONMENT (explicit)
 * 2. NODE_ENV mapping
 * 3. Domain-based detection for staging
 * 4. Default to development
 */
function detectEnvironment(): Environment {
  // Explicit environment variable takes precedence
  const explicitEnv = process.env.NEXT_PUBLIC_ENVIRONMENT;
  if (explicitEnv === 'production' || explicitEnv === 'staging' || explicitEnv === 'test' || explicitEnv === 'development') {
    console.log(`[2025-08-30T${new Date().toISOString().split('T')[1]}] INFO: Environment detected from NEXT_PUBLIC_ENVIRONMENT: ${explicitEnv}`);
    return explicitEnv as Environment;
  }
  
  // Check if running in browser and detect by domain
  if (typeof window !== 'undefined') {
    const hostname = window.location.hostname;
    if (hostname.includes('staging.netrasystems.ai')) {
      console.log('[2025-08-30T' + new Date().toISOString().split('T')[1] + '] INFO: Environment detected from hostname as staging');
      return 'staging';
    }
    if (hostname.includes('netrasystems.ai') && !hostname.includes('staging')) {
      console.log('[2025-08-30T' + new Date().toISOString().split('T')[1] + '] INFO: Environment detected from hostname as production');
      return 'production';
    }
  }
  
  // Fallback to NODE_ENV
  const nodeEnv = process.env.NODE_ENV;
  if (nodeEnv === 'production') {
    // Production NODE_ENV without explicit environment defaults to staging for safety
    console.warn('[2025-08-30T' + new Date().toISOString().split('T')[1] + '] WARN: NODE_ENV=production but NEXT_PUBLIC_ENVIRONMENT not set, defaulting to staging');
    return 'staging';
  }
  
  if (nodeEnv === 'test') {
    return 'test';
  }
  
  // Default to development
  return 'development';
}

/**
 * Check if running inside Docker container
 * Uses Docker-specific environment variables set in docker-compose.yml
 */
function isRunningInDocker(): boolean {
  // Check for Docker-specific environment variables
  return process.env.API_URL !== undefined || process.env.AUTH_URL !== undefined;
}

/**
 * Validate URLs for staging/production environments
 * Prevents localhost URLs from being used in non-development environments
 */
function validateUrlsForEnvironment(environment: Environment, urls: Record<string, unknown>): void {
  if (environment === 'staging' || environment === 'production') {
    const localhostUrls = Object.entries(urls)
      .filter(([_, url]) => typeof url === 'string' && url.includes('localhost'))
      .map(([key, url]) => `${key}: ${url}`);
    
    if (localhostUrls.length > 0) {
      const error = `CRITICAL: localhost URLs detected in ${environment} environment!\n` +
                   `This will cause CORS and authentication failures:\n` +
                   localhostUrls.map(url => `  - ${url}`).join('\n') + '\n' +
                   `Fix: Set proper environment variables for ${environment}`;
      
      console.error(error);
      throw new Error(error);
    }
  }
}

/**
 * Get environment-specific configuration
 * NO localhost references in staging/production
 */
function getEnvironmentConfig(env: Environment): UnifiedApiConfig {
  switch (env) {
    case 'production':
      return {
        environment: 'production',
        urls: {
          api: 'https://api.netrasystems.ai',
          websocket: 'wss://api.netrasystems.ai/websocket',
          auth: 'https://auth.netrasystems.ai',
          frontend: 'https://app.netrasystems.ai',
        },
        endpoints: {
          // Backend endpoints - direct API calls, no rewrites
          health: 'https://api.netrasystems.ai/health',
          ready: 'https://api.netrasystems.ai/health/ready',
          threads: 'https://api.netrasystems.ai/api/threads',
          websocket: 'wss://api.netrasystems.ai/websocket',
          
          // v1 Agent API endpoints (deprecated)
          agentV1Optimization: 'https://api.netrasystems.ai/api/agents/optimization',
          agentV1Data: 'https://api.netrasystems.ai/api/agents/data',
          agentV1Triage: 'https://api.netrasystems.ai/api/agents/triage',
          
          // v2 Agent API endpoints (new request-scoped)
          agentV2Execute: 'https://api.netrasystems.ai/api/agent/v2/execute',
          
          // Auth service endpoints
          authConfig: 'https://auth.netrasystems.ai/auth/config',
          authLogin: 'https://auth.netrasystems.ai/auth/login',
          authLogout: 'https://auth.netrasystems.ai/auth/logout',
          authCallback: 'https://auth.netrasystems.ai/auth/callback',
          authToken: 'https://auth.netrasystems.ai/auth/token',
          authRefresh: 'https://auth.netrasystems.ai/auth/refresh',
          authValidate: 'https://auth.netrasystems.ai/auth/validate',
          authSession: 'https://auth.netrasystems.ai/auth/session',
          authMe: 'https://auth.netrasystems.ai/auth/me',
        },
        features: {
          useHttps: true,
          useWebSocketSecure: true,
          corsEnabled: true,
          dynamicDiscovery: false,
          // v2 Migration Feature Flags - CRITICAL: Enable v2 for multi-user safety
          enableV2AgentApi: process.env.NEXT_PUBLIC_ENABLE_V2_API !== 'false', // Default true for safety
          v2MigrationMode: (process.env.NEXT_PUBLIC_V2_MIGRATION_MODE as any) || 'full', // Full v2 for complete isolation
        },
      };
      
    case 'staging':
      // Use environment variables if available, otherwise fall back to static staging URLs
      const stagingApiUrl = process.env.NEXT_PUBLIC_API_URL || 'https://api.staging.netrasystems.ai';
      const stagingWsUrl = process.env.NEXT_PUBLIC_WS_URL || 'wss://api.staging.netrasystems.ai';
      const stagingAuthUrl = process.env.NEXT_PUBLIC_AUTH_URL || 'https://auth.staging.netrasystems.ai';
      const stagingFrontendUrl = process.env.NEXT_PUBLIC_FRONTEND_URL || 'https://app.staging.netrasystems.ai';
      
      return {
        environment: 'staging',
        urls: {
          api: stagingApiUrl,
          websocket: stagingWsUrl,
          auth: stagingAuthUrl,
          frontend: stagingFrontendUrl,
        },
        endpoints: {
          // Backend endpoints - direct API calls, no rewrites
          health: `${stagingApiUrl}/health`,
          ready: `${stagingApiUrl}/health/ready`,
          threads: `${stagingApiUrl}/api/threads`,
          websocket: `${stagingWsUrl}/websocket`,
          
          // v1 Agent API endpoints (deprecated)
          agentV1Optimization: `${stagingApiUrl}/api/agents/optimization`,
          agentV1Data: `${stagingApiUrl}/api/agents/data`,
          agentV1Triage: `${stagingApiUrl}/api/agents/triage`,
          
          // v2 Agent API endpoints (new request-scoped)
          agentV2Execute: `${stagingApiUrl}/api/agent/v2/execute`,
          
          // Auth service endpoints
          authConfig: `${stagingAuthUrl}/auth/config`,
          authLogin: `${stagingAuthUrl}/auth/login`,
          authLogout: `${stagingAuthUrl}/auth/logout`,
          authCallback: `${stagingAuthUrl}/auth/callback`,
          authToken: `${stagingAuthUrl}/auth/token`,
          authRefresh: `${stagingAuthUrl}/auth/refresh`,
          authValidate: `${stagingAuthUrl}/auth/validate`,
          authSession: `${stagingAuthUrl}/auth/session`,
          authMe: `${stagingAuthUrl}/auth/me`,
        },
        features: {
          useHttps: true,
          useWebSocketSecure: true,
          corsEnabled: true,
          dynamicDiscovery: false,
          // v2 Migration Feature Flags - More permissive for staging
          enableV2AgentApi: process.env.NEXT_PUBLIC_ENABLE_V2_API !== 'false', // Default true for staging
          v2MigrationMode: (process.env.NEXT_PUBLIC_V2_MIGRATION_MODE as any) || 'testing',
        },
      };
      
    case 'test':
      return {
        environment: 'test',
        urls: {
          api: 'http://localhost:8000', // Force port 8000 for backend API
          websocket: 'ws://localhost:8000/websocket', // Force port 8000 for WebSocket
          auth: process.env.NEXT_PUBLIC_AUTH_URL || 'http://localhost:8081',
          frontend: process.env.NEXT_PUBLIC_FRONTEND_URL || 'http://localhost:3000',
        },
        endpoints: {
          // Test environment uses hardcoded localhost:8000
          health: 'http://localhost:8000/health',
          ready: 'http://localhost:8000/health/ready',
          threads: 'http://localhost:8000/api/threads',
          websocket: 'ws://localhost:8000/websocket',
          
          // v1 Agent API endpoints (deprecated)
          agentV1Optimization: 'http://localhost:8000/api/agents/optimization',
          agentV1Data: 'http://localhost:8000/api/agents/data',
          agentV1Triage: 'http://localhost:8000/api/agents/triage',
          
          // v2 Agent API endpoints (new request-scoped)
          agentV2Execute: 'http://localhost:8000/api/agent/v2/execute',
          
          authConfig: `${process.env.NEXT_PUBLIC_AUTH_URL || 'http://localhost:8081'}/auth/config`,
          authLogin: `${process.env.NEXT_PUBLIC_AUTH_URL || 'http://localhost:8081'}/auth/login`,
          authLogout: `${process.env.NEXT_PUBLIC_AUTH_URL || 'http://localhost:8081'}/auth/logout`,
          authCallback: `${process.env.NEXT_PUBLIC_AUTH_URL || 'http://localhost:8081'}/auth/callback`,
          authToken: `${process.env.NEXT_PUBLIC_AUTH_URL || 'http://localhost:8081'}/auth/token`,
          authRefresh: `${process.env.NEXT_PUBLIC_AUTH_URL || 'http://localhost:8081'}/auth/refresh`,
          authValidate: `${process.env.NEXT_PUBLIC_AUTH_URL || 'http://localhost:8081'}/auth/validate`,
          authSession: `${process.env.NEXT_PUBLIC_AUTH_URL || 'http://localhost:8081'}/auth/session`,
          authMe: `${process.env.NEXT_PUBLIC_AUTH_URL || 'http://localhost:8081'}/auth/me`,
        },
        features: {
          useHttps: false,
          useWebSocketSecure: false,
          corsEnabled: false,
          dynamicDiscovery: false,
          // v2 Migration Feature Flags - Full migration for testing
          enableV2AgentApi: true, // Always enabled for testing
          v2MigrationMode: (process.env.NEXT_PUBLIC_V2_MIGRATION_MODE as any) || 'full',
        },
      };
      
    case 'development':
    default:
      // Check if running in Docker (Docker sets NEXT_PUBLIC_API_URL)
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
      const wsUrl = process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8000';
      const authUrl = process.env.NEXT_PUBLIC_AUTH_URL || 'http://localhost:8081';
      
      return {
        environment: 'development',
        urls: {
          api: apiUrl,
          websocket: wsUrl,
          auth: authUrl,
          frontend: process.env.NEXT_PUBLIC_FRONTEND_URL || 'http://localhost:3000',
        },
        endpoints: {
          // Use direct URLs to bypass Next.js proxy issues
          health: `${apiUrl}/health`,
          ready: `${apiUrl}/health/ready`,
          threads: `${apiUrl}/api/threads`,
          websocket: `${wsUrl}/websocket`,
          
          // v1 Agent API endpoints (deprecated)
          agentV1Optimization: `${apiUrl}/api/agents/optimization`,
          agentV1Data: `${apiUrl}/api/agents/data`,
          agentV1Triage: `${apiUrl}/api/agents/triage`,
          
          // v2 Agent API endpoints (new request-scoped)
          agentV2Execute: `${apiUrl}/api/agent/v2/execute`,
          
          // Auth endpoints use direct URLs even in development
          authConfig: `${process.env.NEXT_PUBLIC_AUTH_URL || 'http://localhost:8081'}/auth/config`,
          authLogin: `${process.env.NEXT_PUBLIC_AUTH_URL || 'http://localhost:8081'}/auth/login`,
          authLogout: `${process.env.NEXT_PUBLIC_AUTH_URL || 'http://localhost:8081'}/auth/logout`,
          authCallback: `${process.env.NEXT_PUBLIC_AUTH_URL || 'http://localhost:8081'}/auth/callback`,
          authToken: `${process.env.NEXT_PUBLIC_AUTH_URL || 'http://localhost:8081'}/auth/token`,
          authRefresh: `${process.env.NEXT_PUBLIC_AUTH_URL || 'http://localhost:8081'}/auth/refresh`,
          authValidate: `${process.env.NEXT_PUBLIC_AUTH_URL || 'http://localhost:8081'}/auth/validate`,
          authSession: `${process.env.NEXT_PUBLIC_AUTH_URL || 'http://localhost:8081'}/auth/session`,
          authMe: `${process.env.NEXT_PUBLIC_AUTH_URL || 'http://localhost:8081'}/auth/me`,
        },
        features: {
          useHttps: false,
          useWebSocketSecure: false,
          corsEnabled: false,
          dynamicDiscovery: true,
          // v2 Migration Feature Flags - Flexible for development
          enableV2AgentApi: process.env.NEXT_PUBLIC_ENABLE_V2_API !== 'false', // Default true for development
          v2MigrationMode: (process.env.NEXT_PUBLIC_V2_MIGRATION_MODE as any) || 'gradual',
        },
      };
  }
}

/**
 * Validate configuration to prevent environment mismatches
 */
function validateConfig(config: UnifiedApiConfig): void {
  const { environment, urls } = config;
  
  // Critical: Staging/Production should NEVER use localhost
  if ((environment === 'staging' || environment === 'production')) {
    const hasLocalhost = Object.values(urls).some(url => 
      url.includes('localhost') || url.includes('127.0.0.1')
    );
    
    if (hasLocalhost) {
      console.error('[2025-08-30T' + new Date().toISOString().split('T')[1] + '] ERROR: CRITICAL: Non-development environment using localhost URLs!', {
        environment,
        urls
      });
      throw new Error(`Invalid configuration: ${environment} environment cannot use localhost URLs`);
    }
  }
  
  // Validate auth service URL is accessible
  if (environment === 'staging') {
    if (!urls.auth.includes('staging')) {
      console.warn('[2025-08-30T' + new Date().toISOString().split('T')[1] + '] WARN: Staging environment auth URL missing "staging" subdomain', {
        authUrl: urls.auth
      });
    }
  }
}

/**
 * Get the unified API configuration
 * This is the single source of truth for all API URLs
 */
export function getUnifiedApiConfig(): UnifiedApiConfig {
  const environment = detectEnvironment();
  const config = getEnvironmentConfig(environment);
  
  // Validate configuration before using
  try {
    validateConfig(config);
  } catch (error) {
    console.error('[2025-08-30T' + new Date().toISOString().split('T')[1] + '] ERROR: Configuration validation failed', error);
    // In staging/production, this is critical
    if (environment === 'staging' || environment === 'production') {
      throw error;
    }
  }
  
  // Log configuration for debugging
  console.log('[2025-08-30T' + new Date().toISOString().split('T')[1] + '] INFO: Unified API Configuration:', {
    environment: config.environment,
    urls: config.urls,
    features: config.features,
  });
  
  return config;
}

/**
 * Helper to get OAuth redirect URI based on environment
 */
export function getOAuthRedirectUri(): string {
  const config = getUnifiedApiConfig();
  return `${config.urls.frontend}/auth/callback`;
}

/**
 * Helper to check if we're in a secure environment
 */
export function isSecureEnvironment(): boolean {
  const config = getUnifiedApiConfig();
  return config.features.useHttps;
}

/**
 * Helper to get WebSocket URL with proper protocol
 */
export function getWebSocketUrl(): string {
  const config = getUnifiedApiConfig();
  return config.endpoints.websocket;
}

/**
 * Helper to determine if v2 Agent API should be used
 */
export function shouldUseV2AgentApi(): boolean {
  const config = getUnifiedApiConfig();
  return config.features.enableV2AgentApi;
}

/**
 * Helper to get the appropriate agent endpoint based on migration mode
 */
export function getAgentEndpoint(agentType?: string): string {
  const config = getUnifiedApiConfig();
  
  // Always use v2 if enabled
  if (config.features.enableV2AgentApi) {
    return config.endpoints.agentV2Execute;
  }
  
  // Fallback to v1 endpoints
  switch (agentType?.toLowerCase()) {
    case 'optimization':
      return config.endpoints.agentV1Optimization;
    case 'data':
      return config.endpoints.agentV1Data;
    case 'triage':
    default:
      return config.endpoints.agentV1Triage;
  }
}

/**
 * Helper to get v2 migration mode
 */
export function getV2MigrationMode(): 'disabled' | 'testing' | 'gradual' | 'full' {
  const config = getUnifiedApiConfig();
  return config.features.v2MigrationMode;
}

/**
 * Export singleton instance
 */
export const unifiedApiConfig = getUnifiedApiConfig();

// Export environment detection for other modules
export { detectEnvironment };

// Type exports
export type { UnifiedApiConfig };