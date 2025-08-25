/**
 * Frontend API Proxy - Thread Details
 * Forwards requests to the backend service's /api/threads/[threadId] endpoint
 */
import { NextRequest, NextResponse } from 'next/server'
import { getUnifiedApiConfig } from '@/lib/unified-api-config'

interface RouteParams {
  params: {
    threadId: string;
  };
}

export async function GET(request: NextRequest, { params }: RouteParams) {
  try {
    const config = getUnifiedApiConfig();
    const url = new URL(request.url);
    const backendUrl = `${config.urls.api}/api/threads/${params.threadId}${url.search}`;
    
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
      console.warn(`Backend thread ${params.threadId} GET failed: ${response.status} ${response.statusText}`);
      return NextResponse.json({
        error: 'Backend service unavailable',
        status: response.status,
        statusText: response.statusText,
        threadId: params.threadId,
        source: 'frontend-proxy'
      }, { status: response.status });
    }

    const data = await response.json();
    return NextResponse.json(data, { status: response.status });
    
  } catch (error) {
    console.error(`Thread ${params.threadId} GET proxy error:`, error);
    return NextResponse.json({
      error: 'Proxy error',
      message: error instanceof Error ? error.message : 'Unknown error',
      threadId: params.threadId,
      source: 'frontend-proxy'
    }, { status: 503 });
  }
}

export async function PUT(request: NextRequest, { params }: RouteParams) {
  try {
    const config = getUnifiedApiConfig();
    const backendUrl = `${config.urls.api}/api/threads/${params.threadId}`;
    const body = await request.json();
    
    // Forward the request to the backend
    const response = await fetch(backendUrl, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': request.headers.get('authorization') || '',
        'User-Agent': request.headers.get('user-agent') || 'Netra-Frontend',
      },
      body: JSON.stringify(body),
    });

    if (!response.ok) {
      console.warn(`Backend thread ${params.threadId} PUT failed: ${response.status} ${response.statusText}`);
      return NextResponse.json({
        error: 'Backend service unavailable',
        status: response.status,
        statusText: response.statusText,
        threadId: params.threadId,
        source: 'frontend-proxy'
      }, { status: response.status });
    }

    const data = await response.json();
    return NextResponse.json(data, { status: response.status });
    
  } catch (error) {
    console.error(`Thread ${params.threadId} PUT proxy error:`, error);
    return NextResponse.json({
      error: 'Proxy error',
      message: error instanceof Error ? error.message : 'Unknown error',
      threadId: params.threadId,
      source: 'frontend-proxy'
    }, { status: 503 });
  }
}

export async function DELETE(request: NextRequest, { params }: RouteParams) {
  try {
    const config = getUnifiedApiConfig();
    const backendUrl = `${config.urls.api}/api/threads/${params.threadId}`;
    
    // Forward the request to the backend
    const response = await fetch(backendUrl, {
      method: 'DELETE',
      headers: {
        'Authorization': request.headers.get('authorization') || '',
        'User-Agent': request.headers.get('user-agent') || 'Netra-Frontend',
      },
    });

    if (!response.ok) {
      console.warn(`Backend thread ${params.threadId} DELETE failed: ${response.status} ${response.statusText}`);
      return NextResponse.json({
        error: 'Backend service unavailable',
        status: response.status,
        statusText: response.statusText,
        threadId: params.threadId,
        source: 'frontend-proxy'
      }, { status: response.status });
    }

    // DELETE might not return JSON data
    if (response.status === 204) {
      return new NextResponse(null, { status: 204 });
    }

    const data = await response.json();
    return NextResponse.json(data, { status: response.status });
    
  } catch (error) {
    console.error(`Thread ${params.threadId} DELETE proxy error:`, error);
    return NextResponse.json({
      error: 'Proxy error',
      message: error instanceof Error ? error.message : 'Unknown error',
      threadId: params.threadId,
      source: 'frontend-proxy'
    }, { status: 503 });
  }
}