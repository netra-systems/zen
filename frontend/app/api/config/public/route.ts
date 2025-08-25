/**
 * Frontend API Proxy - Public Configuration
 * Forwards requests to the backend service's /api/config/public endpoint
 */
import { NextRequest, NextResponse } from 'next/server'
import { getUnifiedApiConfig } from '@/lib/unified-api-config'

export async function GET(request: NextRequest) {
  try {
    const config = getUnifiedApiConfig();
    const backendUrl = `${config.urls.api}/api/config/public`;
    
    // Forward the request to the backend
    const response = await fetch(backendUrl, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
        // Forward relevant headers
        'User-Agent': request.headers.get('user-agent') || 'Netra-Frontend',
      },
    });

    if (!response.ok) {
      console.warn(`Backend config endpoint failed: ${response.status} ${response.statusText}`);
      
      // Return a fallback config for staging/production environments
      return NextResponse.json({
        environment: config.environment || 'staging',
        features: {
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
        fallback: true,
        source: 'frontend-proxy'
      }, { status: 200 });
    }

    const data = await response.json();
    return NextResponse.json(data, { status: response.status });
    
  } catch (error) {
    console.error('Public config proxy error:', error);
    
    // Return fallback configuration
    const config = getUnifiedApiConfig();
    return NextResponse.json({
      environment: config.environment || 'staging',
      features: {
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
      fallback: true,
      error: error instanceof Error ? error.message : 'Unknown error',
      source: 'frontend-fallback'
    }, { status: 200 });
  }
}