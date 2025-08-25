/**
 * Root Level Health Check API Endpoint
 * Provides comprehensive health status for the frontend service
 * This endpoint is designed for load balancer health checks and monitoring systems
 */
import { NextRequest, NextResponse } from 'next/server'
import { getUnifiedApiConfig } from '@/lib/unified-api-config'

/**
 * Check backend service health with timeout
 */
async function checkBackendHealth(): Promise<{ status: string; details?: any }> {
  try {
    const config = getUnifiedApiConfig();
    const response = await fetch(`${config.urls.api}/health`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
        'User-Agent': 'Netra-Frontend-HealthCheck/1.0.0',
      },
      // 5 second timeout for health checks
      signal: AbortSignal.timeout(5000),
    });

    if (response.ok) {
      const data = await response.json();
      return { status: 'healthy', details: data };
    } else {
      return { status: 'unhealthy', details: { status: response.status, statusText: response.statusText } };
    }
  } catch (error) {
    return { 
      status: 'unhealthy', 
      details: { error: error instanceof Error ? error.message : 'Unknown error' }
    };
  }
}

/**
 * Check auth service health with timeout
 */
async function checkAuthHealth(): Promise<{ status: string; details?: any }> {
  try {
    const config = getUnifiedApiConfig();
    const response = await fetch(`${config.urls.auth}/health`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
        'User-Agent': 'Netra-Frontend-HealthCheck/1.0.0',
      },
      // 5 second timeout for health checks
      signal: AbortSignal.timeout(5000),
    });

    if (response.ok) {
      const data = await response.json();
      return { status: 'healthy', details: data };
    } else {
      return { status: 'unhealthy', details: { status: response.status, statusText: response.statusText } };
    }
  } catch (error) {
    return { 
      status: 'unhealthy', 
      details: { error: error instanceof Error ? error.message : 'Unknown error' }
    };
  }
}

export async function GET(request: NextRequest) {
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

    // Determine overall health status
    const allDependenciesHealthy = Object.values(dependencies).every(dep => dep.status === 'healthy');
    const overallStatus = allDependenciesHealthy ? 'healthy' : 'degraded';
    
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
    const statusCode = overallStatus === 'healthy' ? 200 : 503;
    
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
export async function HEAD(request: NextRequest) {
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
export async function OPTIONS(request: NextRequest) {
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