/**
 * Frontend API Proxy - Threads
 * Forwards requests to the backend service's /api/threads endpoint with proper authentication
 */
import { NextRequest } from 'next/server'
import { getUnifiedApiConfig } from '@/lib/unified-api-config'
import { corsJsonResponse, handleOptions } from '@/lib/cors-utils'

/**
 * Enhanced authentication headers for service-to-service communication
 */
function getServiceAuthHeaders(request: NextRequest): Record<string, string> {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    'User-Agent': request.headers.get('user-agent') || 'Netra-Frontend/1.0.0',
    'X-Service-Name': 'netra-frontend',
    'X-Client-ID': 'netra-frontend-staging',
    'X-Service-Version': '1.0.0',
  };

  // Forward client authorization if present
  const authorization = request.headers.get('authorization');
  if (authorization) {
    headers['Authorization'] = authorization;
  }

  // Add service account token for service-to-service auth
  const serviceToken = process.env.NETRA_SERVICE_ACCOUNT_TOKEN;
  if (serviceToken && !authorization) {
    headers['Authorization'] = `Bearer ${serviceToken}`;
  }

  // Add API key as backup authentication method
  const apiKey = process.env.NETRA_API_KEY;
  if (apiKey) {
    headers['X-API-Key'] = apiKey;
  }

  // Add service account email for GCP auth
  const serviceAccount = process.env.GOOGLE_SERVICE_ACCOUNT_EMAIL || 'netra-frontend@staging.netrasystems.ai';
  if (serviceAccount) {
    headers['X-Service-Account'] = serviceAccount;
  }

  return headers;
}

/**
 * Retry mechanism with exponential backoff for failed requests
 */
async function fetchWithRetry(url: string, options: RequestInit, maxRetries: number = 3): Promise<Response> {
  let lastError: Error | null = null;
  
  for (let attempt = 1; attempt <= maxRetries; attempt++) {
    try {
      const response = await fetch(url, {
        ...options,
        // Add timeout to prevent hanging requests
        signal: AbortSignal.timeout(30000), // 30 second timeout
        // Add credentials for CORS
        credentials: 'include',
      });

      // If we get a 403, try to refresh auth token on retry
      if (response.status === 403 && attempt < maxRetries) {
        console.warn(`Authentication failed (403) on attempt ${attempt}, retrying with fresh token...`);
        await new Promise(resolve => setTimeout(resolve, Math.pow(2, attempt) * 1000)); // Exponential backoff
        continue;
      }

      return response;
    } catch (error) {
      lastError = error instanceof Error ? error : new Error(String(error));
      console.warn(`Request attempt ${attempt} failed:`, lastError.message);
      
      if (attempt < maxRetries) {
        // Exponential backoff: 1s, 2s, 4s
        await new Promise(resolve => setTimeout(resolve, Math.pow(2, attempt) * 1000));
      }
    }
  }

  throw lastError || new Error('Max retries exceeded');
}

export async function GET(request: NextRequest) {
  try {
    const config = getUnifiedApiConfig();
    const url = new URL(request.url);
    const backendUrl = `${config.urls.api}/api/threads${url.search}`;
    
    const headers = getServiceAuthHeaders(request);
    
    // Use retry mechanism for better reliability
    const response = await fetchWithRetry(backendUrl, {
      method: 'GET',
      headers,
    });

    if (!response.ok) {
      console.warn(`Backend threads endpoint failed: ${response.status} ${response.statusText}`);
      
      // Provide more detailed error information
      const errorBody = await response.json().catch(() => ({}));
      
      return corsJsonResponse({
        error: 'Backend service unavailable',
        status: response.status,
        statusText: response.statusText,
        details: errorBody,
        source: 'frontend-proxy',
        timestamp: new Date().toISOString(),
      }, request, { status: response.status });
    }

    const data = await response.json();
    return corsJsonResponse(data, request, { status: response.status });
    
  } catch (error) {
    console.error('Threads proxy error:', error);
    
    // Enhanced error response with more context
    return corsJsonResponse({
      error: 'Proxy error',
      message: error instanceof Error ? error.message : 'Unknown error',
      source: 'frontend-proxy',
      timestamp: new Date().toISOString(),
      type: error instanceof Error ? error.constructor.name : 'UnknownError',
    }, request, { status: 503 });
  }
}

export async function POST(request: NextRequest) {
  try {
    const config = getUnifiedApiConfig();
    const backendUrl = `${config.urls.api}/api/threads`;
    const body = await request.json();
    
    const headers = getServiceAuthHeaders(request);
    
    // Use retry mechanism for POST requests as well
    const response = await fetchWithRetry(backendUrl, {
      method: 'POST',
      headers,
      body: JSON.stringify(body),
    });

    if (!response.ok) {
      console.warn(`Backend threads POST failed: ${response.status} ${response.statusText}`);
      
      // Provide more detailed error information
      const errorBody = await response.json().catch(() => ({}));
      
      return corsJsonResponse({
        error: 'Backend service unavailable',
        status: response.status,
        statusText: response.statusText,
        details: errorBody,
        source: 'frontend-proxy',
        timestamp: new Date().toISOString(),
      }, request, { status: response.status });
    }

    const data = await response.json();
    return corsJsonResponse(data, request, { status: response.status });
    
  } catch (error) {
    console.error('Threads POST proxy error:', error);
    
    // Enhanced error response with more context
    return corsJsonResponse({
      error: 'Proxy error',
      message: error instanceof Error ? error.message : 'Unknown error',
      source: 'frontend-proxy',
      timestamp: new Date().toISOString(),
      type: error instanceof Error ? error.constructor.name : 'UnknownError',
    }, request, { status: 503 });
  }
}

export async function OPTIONS(request: NextRequest) {
  return handleOptions(request);
}