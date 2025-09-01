/**
 * Root Level Health Check API Endpoint
 * Provides comprehensive health status for the frontend service
 * This endpoint is designed for load balancer health checks and monitoring systems
 */
import { NextRequest, NextResponse } from 'next/server'
import { getUnifiedApiConfig } from '@/lib/unified-api-config'

// Health check result interface
interface HealthCheckResult {
  status: string;
  details?: {
    error?: string;
    response_time?: number;
    url?: string;
    [key: string]: unknown;
  };
}

/**
 * Check backend service health with environment-aware timeout
 */
async function checkBackendHealth(): Promise<HealthCheckResult> {
  try {
    const config = getUnifiedApiConfig();
    
    // Environment-aware timeout configuration
    const timeout = config.environment === 'staging' ? 2000 : 
                   config.environment === 'development' ? 3000 : 5000;
    
    const response = await fetch(`${config.urls.api}/health`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
        'User-Agent': 'Netra-Frontend-HealthCheck/1.0.0',
      },
      signal: AbortSignal.timeout(timeout),
    });

    if (response.ok) {
      const data = await response.json();
      return { status: 'healthy', details: data };
    } else {
      return { status: 'unhealthy', details: { status: response.status, statusText: response.statusText } };
    }
  } catch (error) {
    // In staging, treat timeouts as degraded rather than unhealthy
    const config = getUnifiedApiConfig();
    const isDegraded = config.environment === 'staging' && 
                      (error instanceof Error && error.name === 'TimeoutError');
    
    return { 
      status: isDegraded ? 'degraded' : 'unhealthy', 
      details: { error: error instanceof Error ? error.message : 'Unknown error' }
    };
  }
}

/**
 * Check auth service health with environment-aware timeout
 */
async function checkAuthHealth(): Promise<HealthCheckResult> {
  try {
    const config = getUnifiedApiConfig();
    
    // Environment-aware timeout configuration
    const timeout = config.environment === 'staging' ? 1500 : 
                   config.environment === 'development' ? 2000 : 3000;
    
    const response = await fetch(`${config.urls.auth}/health`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
        'User-Agent': 'Netra-Frontend-HealthCheck/1.0.0',
      },
      signal: AbortSignal.timeout(timeout),
    });

    if (response.ok) {
      const data = await response.json();
      return { status: 'healthy', details: data };
    } else {
      return { status: 'unhealthy', details: { status: response.status, statusText: response.statusText } };
    }
  } catch (error) {
    // In staging, treat auth service issues as degraded if backend is healthy
    const config = getUnifiedApiConfig();
    const isDegraded = config.environment === 'staging' && 
                      (error instanceof Error && error.name === 'TimeoutError');
    
    return { 
      status: isDegraded ? 'degraded' : 'unhealthy', 
      details: { error: error instanceof Error ? error.message : 'Unknown error' }
    };
  }
}

export async function GET(_request: NextRequest) {
  try {
    const config = getUnifiedApiConfig();
    const startTime = Date.now();
    
    // Check dependencies in parallel with timeout
    const [backendHealth, authHealth] = await Promise.allSettled([
      checkBackendHealth(),
      checkAuthHealth(),
    ]);
    
    const healthCheckDuration = Date.now() - startTime;
    
    // Process dependency check results
    const dependencies = {
      backend: backendHealth.status === 'fulfilled' ? backendHealth.value : { status: 'error', details: backendHealth.reason },
      auth: authHealth.status === 'fulfilled' ? authHealth.value : { status: 'error', details: authHealth.reason },
    };

    // Determine overall health status with graceful degradation
    const healthyCount = Object.values(dependencies).filter(dep => dep.status === 'healthy').length;
    const degradedCount = Object.values(dependencies).filter(dep => dep.status === 'degraded').length;
    const errorCount = Object.values(dependencies).filter(dep => dep.status === 'unhealthy' || dep.status === 'error').length;
    
    let overallStatus: string;
    if (healthyCount === Object.keys(dependencies).length) {
      overallStatus = 'healthy';
    } else if (healthyCount > 0 || degradedCount > 0) {
      // At least one service is working
      overallStatus = 'degraded';
    } else {
      overallStatus = 'unhealthy';
    }
    
    // Standard health check format expected by monitoring systems
    const healthData = {
      status: overallStatus,
      service: 'frontend',
      version: '1.0.0',
      environment: config.environment,
      timestamp: new Date().toISOString(),
      uptime: process.uptime(),
      memory: {
        used: Math.round(process.memoryUsage().heapUsed / 1024 / 1024),
        total: Math.round(process.memoryUsage().heapTotal / 1024 / 1024),
        rss: Math.round(process.memoryUsage().rss / 1024 / 1024),
      },
      dependencies,
      checks: {
        response_time_ms: healthCheckDuration,
        environment_config: config.environment ? 'ok' : 'error',
        memory_usage: process.memoryUsage().heapUsed < 500 * 1024 * 1024 ? 'ok' : 'warning', // 500MB threshold
      },
      urls: {
        api: config.urls.api,
        websocket: config.urls.websocket,
        auth: config.urls.auth,
        frontend: config.urls.frontend,
      }
    };

    // Return appropriate status code based on health
    const statusCode = overallStatus === 'healthy' ? 200 : 
                      overallStatus === 'degraded' ? 200 : 503; // 200 for degraded allows traffic
    
    return NextResponse.json(healthData, { 
      status: statusCode,
      headers: {
        'Cache-Control': 'no-cache, no-store, must-revalidate',
        'Pragma': 'no-cache',
        'Expires': '0'
      }
    });
    
  } catch (error) {
    console.error('Health check error:', error);
    
    return NextResponse.json({
      status: 'unhealthy',
      service: 'frontend', 
      version: '1.0.0',
      timestamp: new Date().toISOString(),
      error: error instanceof Error ? error.message : 'Unknown error',
      checks: {
        health_check_execution: 'failed'
      }
    }, { 
      status: 503,
      headers: {
        'Cache-Control': 'no-cache, no-store, must-revalidate',
        'Pragma': 'no-cache',
        'Expires': '0'
      }
    });
  }
}

/**
 * Support HEAD requests for simple alive checks
 */
export async function HEAD(_request: NextRequest) {
  try {
    // Simple alive check without dependency verification
    return new NextResponse(null, { 
      status: 200,
      headers: {
        'Cache-Control': 'no-cache, no-store, must-revalidate',
        'Pragma': 'no-cache',
        'Expires': '0'
      }
    });
  } catch (error) {
    return new NextResponse(null, { status: 503 });
  }
}

/**
 * Support OPTIONS requests for CORS preflight
 */
export async function OPTIONS(_request: NextRequest) {
  return new NextResponse(null, {
    status: 200,
    headers: {
      'Access-Control-Allow-Origin': '*',
      'Access-Control-Allow-Methods': 'GET, HEAD, OPTIONS',
      'Access-Control-Allow-Headers': 'Content-Type, Authorization, X-API-Key',
      'Access-Control-Max-Age': '86400', // 24 hours
    },
  });
}