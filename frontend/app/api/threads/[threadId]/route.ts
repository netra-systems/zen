/**
 * Frontend API Proxy - Thread Details
 * Forwards requests to the backend service's /api/threads/[threadId] endpoint
 */
import { NextRequest } from 'next/server'
import { getUnifiedApiConfig } from '@/lib/unified-api-config'
import { corsJsonResponse, corsEmptyResponse, handleOptions } from '@/lib/cors-utils'

interface RouteParams {
  params: Promise<{
    threadId: string;
  }>;
}

export async function GET(request: NextRequest, { params }: RouteParams) {
  try {
    const config = getUnifiedApiConfig();
    const url = new URL(request.url);
    const resolvedParams = await params;
    const backendUrl = `${config.urls.api}/api/threads/${resolvedParams.threadId}${url.search}`;
    
    // Forward the request to the backend
    const response = await fetch(backendUrl, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': request.headers.get('authorization') || '',
        'User-Agent': request.headers.get('user-agent') || 'Netra-Frontend',
      },
      credentials: 'include',
    });

    if (!response.ok) {
      console.warn(`Backend thread ${resolvedParams.threadId} GET failed: ${response.status} ${response.statusText}`);
      return corsJsonResponse({
        error: 'Backend service unavailable',
        status: response.status,
        statusText: response.statusText,
        threadId: resolvedParams.threadId,
        source: 'frontend-proxy'
      }, request, { status: response.status });
    }

    const data = await response.json();
    return corsJsonResponse(data, request, { status: response.status });
    
  } catch (error) {
    const resolvedParams = await params;
    console.error(`Thread ${resolvedParams.threadId} GET proxy error:`, error);
    return corsJsonResponse({
      error: 'Proxy error',
      message: error instanceof Error ? error.message : 'Unknown error',
      threadId: resolvedParams.threadId,
      source: 'frontend-proxy'
    }, request, { status: 503 });
  }
}

export async function PUT(request: NextRequest, { params }: RouteParams) {
  try {
    const config = getUnifiedApiConfig();
    const resolvedParams = await params;
    const backendUrl = `${config.urls.api}/api/threads/${resolvedParams.threadId}`;
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
      credentials: 'include',
    });

    if (!response.ok) {
      console.warn(`Backend thread ${resolvedParams.threadId} PUT failed: ${response.status} ${response.statusText}`);
      return corsJsonResponse({
        error: 'Backend service unavailable',
        status: response.status,
        statusText: response.statusText,
        threadId: resolvedParams.threadId,
        source: 'frontend-proxy'
      }, request, { status: response.status });
    }

    const data = await response.json();
    return corsJsonResponse(data, request, { status: response.status });
    
  } catch (error) {
    const resolvedParams = await params;
    console.error(`Thread ${resolvedParams.threadId} PUT proxy error:`, error);
    return corsJsonResponse({
      error: 'Proxy error',
      message: error instanceof Error ? error.message : 'Unknown error',
      threadId: resolvedParams.threadId,
      source: 'frontend-proxy'
    }, request, { status: 503 });
  }
}

export async function DELETE(request: NextRequest, { params }: RouteParams) {
  try {
    const config = getUnifiedApiConfig();
    const resolvedParams = await params;
    const backendUrl = `${config.urls.api}/api/threads/${resolvedParams.threadId}`;
    
    // Forward the request to the backend
    const response = await fetch(backendUrl, {
      method: 'DELETE',
      headers: {
        'Authorization': request.headers.get('authorization') || '',
        'User-Agent': request.headers.get('user-agent') || 'Netra-Frontend',
      },
      credentials: 'include',
    });

    if (!response.ok) {
      console.warn(`Backend thread ${resolvedParams.threadId} DELETE failed: ${response.status} ${response.statusText}`);
      return corsJsonResponse({
        error: 'Backend service unavailable',
        status: response.status,
        statusText: response.statusText,
        threadId: resolvedParams.threadId,
        source: 'frontend-proxy'
      }, request, { status: response.status });
    }

    // DELETE might not return JSON data
    if (response.status === 204) {
      return corsEmptyResponse(request, { status: 204 });
    }

    const data = await response.json();
    return corsJsonResponse(data, request, { status: response.status });
    
  } catch (error) {
    console.error(`Thread ${resolvedParams.threadId} DELETE proxy error:`, error);
    return corsJsonResponse({
      error: 'Proxy error',
      message: error instanceof Error ? error.message : 'Unknown error',
      threadId: resolvedParams.threadId,
      source: 'frontend-proxy'
    }, request, { status: 503 });
  }
}

export async function OPTIONS(request: NextRequest, { params: _params }: RouteParams) {
  return handleOptions(request);
}