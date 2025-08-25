/**
 * Frontend API Proxy - Threads
 * Forwards requests to the backend service's /api/threads endpoint
 */
import { NextRequest, NextResponse } from 'next/server'
import { getUnifiedApiConfig } from '@/lib/unified-api-config'

export async function GET(request: NextRequest) {
  try {
    const config = getUnifiedApiConfig();
    const url = new URL(request.url);
    const backendUrl = `${config.urls.api}/api/threads${url.search}`;
    
    // Forward the request to the backend
    const response = await fetch(backendUrl, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': request.headers.get('authorization') || '',
        'User-Agent': request.headers.get('user-agent') || 'Netra-Frontend',
      },
    });

    if (!response.ok) {
      console.warn(`Backend threads endpoint failed: ${response.status} ${response.statusText}`);
      return NextResponse.json({
        error: 'Backend service unavailable',
        status: response.status,
        statusText: response.statusText,
        source: 'frontend-proxy'
      }, { status: response.status });
    }

    const data = await response.json();
    return NextResponse.json(data, { status: response.status });
    
  } catch (error) {
    console.error('Threads proxy error:', error);
    return NextResponse.json({
      error: 'Proxy error',
      message: error instanceof Error ? error.message : 'Unknown error',
      source: 'frontend-proxy'
    }, { status: 503 });
  }
}

export async function POST(request: NextRequest) {
  try {
    const config = getUnifiedApiConfig();
    const backendUrl = `${config.urls.api}/api/threads`;
    const body = await request.json();
    
    // Forward the request to the backend
    const response = await fetch(backendUrl, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': request.headers.get('authorization') || '',
        'User-Agent': request.headers.get('user-agent') || 'Netra-Frontend',
      },
      body: JSON.stringify(body),
    });

    if (!response.ok) {
      console.warn(`Backend threads POST failed: ${response.status} ${response.statusText}`);
      return NextResponse.json({
        error: 'Backend service unavailable',
        status: response.status,
        statusText: response.statusText,
        source: 'frontend-proxy'
      }, { status: response.status });
    }

    const data = await response.json();
    return NextResponse.json(data, { status: response.status });
    
  } catch (error) {
    console.error('Threads POST proxy error:', error);
    return NextResponse.json({
      error: 'Proxy error',
      message: error instanceof Error ? error.message : 'Unknown error',
      source: 'frontend-proxy'
    }, { status: 503 });
  }
}