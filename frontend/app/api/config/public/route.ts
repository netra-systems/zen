/**
 * Frontend API Proxy - Public Configuration
 * Provides robust, cached configuration with fallback mechanisms
 */
import { NextRequest, NextResponse } from 'next/server'
import { getUnifiedApiConfig } from '@/lib/unified-api-config'
import { corsJsonResponse, handleOptions, addCorsHeaders } from '@/lib/cors-utils'

// Simple in-memory cache for configuration data
const CONFIG_CACHE = {
  data: null as any,
  timestamp: 0,
  ttl: 60 * 1000, // 1 minute TTL
};

/**
 * Circuit breaker state management
 */
const CIRCUIT_BREAKER = {
  failures: 0,
  lastFailure: 0,
  state: 'closed' as 'closed' | 'open' | 'half-open',
  threshold: 5, // Open after 5 failures
  timeout: 30 * 1000, // 30 seconds before trying again
};

/**
 * Check if circuit breaker should allow requests
 */
function shouldAllowRequest(): boolean {
  const now = Date.now();
  
  switch (CIRCUIT_BREAKER.state) {
    case 'closed':
      return true;
    case 'open':
      if (now - CIRCUIT_BREAKER.lastFailure > CIRCUIT_BREAKER.timeout) {
        CIRCUIT_BREAKER.state = 'half-open';
        return true;
      }
      return false;
    case 'half-open':
      return true;
    default:
      return true;
  }
}

/**
 * Record circuit breaker success
 */
function recordSuccess(): void {
  CIRCUIT_BREAKER.failures = 0;
  CIRCUIT_BREAKER.state = 'closed';
}

/**
 * Record circuit breaker failure
 */
function recordFailure(): void {
  CIRCUIT_BREAKER.failures++;
  CIRCUIT_BREAKER.lastFailure = Date.now();
  
  if (CIRCUIT_BREAKER.failures >= CIRCUIT_BREAKER.threshold) {
    CIRCUIT_BREAKER.state = 'open';
  }
}

/**
 * Get fresh configuration from backend with retry logic
 */
async function fetchFreshConfig(config: any): Promise<any> {
  const maxRetries = 3;
  let attempt = 0;
  
  while (attempt < maxRetries) {
    try {
      const backendUrl = `${config.urls.auth}/auth/config`;
      
      const response = await fetch(backendUrl, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
          'User-Agent': 'Netra-Frontend-Config/1.0.0',
          'Cache-Control': 'no-cache',
        },
        // Short timeout for config requests
        signal: AbortSignal.timeout(10000), // 10 second timeout
        credentials: 'include',
      });

      if (response.ok) {
        const data = await response.json();
        recordSuccess();
        return {
          ...data,
          timestamp: Date.now(),
          cache_status: 'fresh',
          last_updated: new Date().toISOString(),
          source: 'backend',
        };
      } else {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }
    } catch (error) {
      attempt++;
      console.warn(`Config fetch attempt ${attempt} failed:`, error instanceof Error ? error.message : error);
      
      if (attempt < maxRetries) {
        // Exponential backoff: 500ms, 1s, 2s
        await new Promise(resolve => setTimeout(resolve, Math.pow(2, attempt - 1) * 500));
      } else {
        recordFailure();
        throw error;
      }
    }
  }
  
  throw new Error('Max retries exceeded');
}

/**
 * Get cached configuration if valid
 */
function getCachedConfig(): any | null {
  const now = Date.now();
  if (CONFIG_CACHE.data && (now - CONFIG_CACHE.timestamp) < CONFIG_CACHE.ttl) {
    return {
      ...CONFIG_CACHE.data,
      cache_status: 'cached',
      cached_at: new Date(CONFIG_CACHE.timestamp).toISOString(),
    };
  }
  return null;
}

/**
 * Generate fallback configuration
 */
function getFallbackConfig(config: any, error?: string): any {
  return {
    environment: config.environment || 'staging',
    timestamp: Date.now(),
    cache_status: 'fallback',
    last_updated: new Date().toISOString(),
    features: {
      chat: true,
      auth: true,
      mcp: true,
      useHttps: config.features?.useHttps || false,
      useWebSocketSecure: config.features?.useWebSocketSecure || false,
      corsEnabled: config.features?.corsEnabled || false,
    },
    urls: {
      api: config.urls.api,
      websocket: config.urls.websocket,
      auth: config.urls.auth,
      frontend: config.urls.frontend,
    },
    api_version: '1.0.0',
    deployment_status: 'active',
    circuit_breaker_state: CIRCUIT_BREAKER.state,
    fallback: true,
    source: 'frontend-fallback',
    ...(error && { error }),
  };
}

export async function GET(request: NextRequest) {
  try {
    const config = getUnifiedApiConfig();
    
    // Check cache first
    const cachedConfig = getCachedConfig();
    if (cachedConfig) {
      const response = NextResponse.json(cachedConfig, { 
        status: 200,
        headers: {
          'Cache-Control': 'public, max-age=30, s-maxage=60',
          'Vary': 'Accept-Encoding',
        }
      });
      return addCorsHeaders(response, request);
    }
    
    // Check circuit breaker
    if (!shouldAllowRequest()) {
      console.warn('Circuit breaker is open, returning fallback config');
      const fallbackConfig = getFallbackConfig(config, 'Circuit breaker open - using fallback');
      const response = NextResponse.json(fallbackConfig, { 
        status: 200,
        headers: {
          'Cache-Control': 'public, max-age=10, s-maxage=30', // Shorter cache for fallback
        }
      });
      return addCorsHeaders(response, request);
    }
    
    try {
      // Try to fetch fresh config
      const freshConfig = await fetchFreshConfig(config);
      
      // Update cache
      CONFIG_CACHE.data = freshConfig;
      CONFIG_CACHE.timestamp = Date.now();
      
      const response = NextResponse.json(freshConfig, { 
        status: 200,
        headers: {
          'Cache-Control': 'public, max-age=30, s-maxage=60',
          'Vary': 'Accept-Encoding',
        }
      });
      return addCorsHeaders(response, request);
      
    } catch (error) {
      console.warn('Failed to fetch fresh config, returning fallback:', error instanceof Error ? error.message : error);
      
      // Return fallback config with error details
      const fallbackConfig = getFallbackConfig(
        config, 
        error instanceof Error ? error.message : 'Unknown error'
      );
      
      const response = NextResponse.json(fallbackConfig, { 
        status: 200,
        headers: {
          'Cache-Control': 'public, max-age=10, s-maxage=30', // Shorter cache for fallback
        }
      });
      return addCorsHeaders(response, request);
    }
    
  } catch (error) {
    console.error('Config endpoint critical error:', error);
    
    // Last resort fallback
    try {
      const config = getUnifiedApiConfig();
      const emergencyConfig = getFallbackConfig(
        config, 
        `Critical error: ${error instanceof Error ? error.message : 'Unknown error'}`
      );
      
      const response = NextResponse.json(emergencyConfig, { 
        status: 200,
        headers: {
          'Cache-Control': 'no-cache',
        }
      });
      return addCorsHeaders(response, request);
      
    } catch (emergencyError) {
      // Even fallback failed - return minimal config
      return corsJsonResponse({
        environment: 'staging',
        features: { chat: false, auth: false, mcp: false },
        error: 'Critical system error',
        timestamp: Date.now(),
        cache_status: 'emergency_fallback',
        source: 'emergency',
      }, request, { status: 500 });
    }
  }
}

export async function OPTIONS(request: NextRequest) {
  return handleOptions(request);
}