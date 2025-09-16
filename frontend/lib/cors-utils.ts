/**
 * CORS Utility Functions for Next.js Frontend API Routes
 * 
 * Provides centralized CORS handling consistent with the shared CORS configuration
 * from shared/cors_config.py. This ensures consistent CORS behavior across
 * all services in the Netra platform.
 * 
 * Business Value Justification (BVJ):
 * - Segment: ALL (Required for frontend-backend communication)
 * - Business Goal: Enable secure cross-origin requests while maintaining security
 * - Value Impact: Prevents CORS errors that block user interactions
 * - Strategic Impact: Foundation for microservice architecture communication
 */

import { NextRequest, NextResponse } from 'next/server'

/**
 * Environment detection based on environment variables
 */
function detectEnvironment(): string {
  const envVars = [
    process.env.ENVIRONMENT?.toLowerCase() || '',
    process.env.ENV?.toLowerCase() || '',
    process.env.NODE_ENV?.toLowerCase() || '',
    process.env.NETRA_ENV?.toLowerCase() || '',
  ]

  for (const env of envVars) {
    if (env === 'production' || env === 'prod') {
      return 'production'
    } else if (env === 'staging' || env === 'stage' || env === 'stg') {
      return 'staging'
    } else if (env === 'development' || env === 'dev' || env === 'local') {
      return 'development'
    }
  }

  return 'development'
}

/**
 * Get CORS origins based on environment
 */
function getCorsOrigins(environment?: string): string[] {
  const env = environment || detectEnvironment()

  // Check for explicit CORS_ORIGINS environment variable first
  const corsOriginsEnv = process.env.CORS_ORIGINS
  if (corsOriginsEnv) {
    if (corsOriginsEnv.trim() === '*') {
      return getDevelopmentOrigins()
    }
    const origins = corsOriginsEnv.split(',').map(origin => origin.trim()).filter(Boolean)
    return origins.length > 0 ? origins : getDevelopmentOrigins()
  }

  // Fallback to environment-specific defaults
  switch (env) {
    case 'production':
      return getProductionOrigins()
    case 'staging':
      return getStagingOrigins()
    default:
      return getDevelopmentOrigins()
  }
}

/**
 * Production CORS origins
 */
function getProductionOrigins(): string[] {
  return [
    'https://netrasystems.ai',
    'https://www.netrasystems.ai',
    'https://app.netrasystems.ai',
    'https://api.netrasystems.ai',
    'https://auth.netrasystems.ai'
  ]
}

/**
 * Staging CORS origins
 */
function getStagingOrigins(): string[] {
  return [
    // Staging domains
    'https://app.staging.netrasystems.ai',
    'https://auth.staging.netrasystems.ai',
    'https://api.staging.netrasystems.ai',
    
    // Cloud Run patterns for staging
    'https://netra-frontend-701982941522.us-central1.run.app',
    'https://netra-backend-staging-pnovr5vsba-uc.a.run.app',
    
    // Local development support for staging testing
    'http://localhost:3000',
    'http://localhost:3001',
    'http://localhost:8000',
    'http://localhost:8080',
    'http://127.0.0.1:3000',
    'http://127.0.0.1:3001',
    'http://127.0.0.1:8000',
    'http://127.0.0.1:8080'
  ]
}

/**
 * Development CORS origins with comprehensive localhost support
 */
function getDevelopmentOrigins(): string[] {
  return [
    // Standard localhost ports
    'http://localhost:3000',
    'http://localhost:3001',
    'http://localhost:3002',
    'http://localhost:8000',
    'http://localhost:8080',
    'http://localhost:8081',
    'http://localhost:5173', // Vite
    'http://localhost:4200', // Angular
    
    // 127.0.0.1 variants
    'http://127.0.0.1:3000',
    'http://127.0.0.1:3001',
    'http://127.0.0.1:3002',
    'http://127.0.0.1:8000',
    'http://127.0.0.1:8080',
    'http://127.0.0.1:8081',
    'http://127.0.0.1:5173',
    'http://127.0.0.1:4200',
    
    // HTTPS variants for local cert testing
    'https://localhost:3000',
    'https://localhost:3001',
    'https://localhost:8000',
    'https://localhost:8080',
    'https://127.0.0.1:3000',
    'https://127.0.0.1:3001',
    'https://127.0.0.1:8000',
    'https://127.0.0.1:8080',
    
    // 0.0.0.0 for Docker/container scenarios
    'http://0.0.0.0:3000',
    'http://0.0.0.0:8000',
    'http://0.0.0.0:8080',
    
    // Docker service names and internal networking
    'http://frontend:3000',
    'http://backend:8000',
    'http://auth:8081',
    'http://netra-frontend:3000',
    'http://netra-backend:8000',
    'http://netra-auth:8081',
    
    // Docker bridge network IP ranges
    'http://172.17.0.1:3000',
    'http://172.17.0.1:8000',
    'http://172.18.0.1:3000',
    'http://172.18.0.1:8000',
    'http://172.19.0.1:3000',
    'http://172.19.0.1:8000',
    'http://172.20.0.1:3000',
    'http://172.20.0.1:8000',
    
    // IPv6 localhost
    'http://[::1]:3000',
    'http://[::1]:8000',
    'http://[::1]:8080'
  ]
}

/**
 * Check if an origin is allowed
 */
function isOriginAllowed(origin: string, allowedOrigins: string[], environment?: string): boolean {
  if (!origin) {
    return false
  }

  const env = environment || detectEnvironment()

  // Direct match
  if (allowedOrigins.includes(origin)) {
    return true
  }

  // In development, allow any localhost origin
  if (env === 'development' && isLocalhostOrigin(origin)) {
    return true
  }

  // Check for wildcard match
  if (allowedOrigins.includes('*')) {
    return true
  }

  // Pattern matching for staging Cloud Run URLs
  if (env === 'staging' && matchesStagingPatterns(origin)) {
    return true
  }

  return false
}

/**
 * Check if origin is localhost-based or Docker service
 */
function isLocalhostOrigin(origin: string): boolean {
  try {
    const url = new URL(origin)
    const localhostHosts = [
      'localhost', '127.0.0.1', '0.0.0.0', '::1',
      // Docker service names
      'frontend', 'backend', 'auth',
      // Docker container names
      'netra-frontend', 'netra-backend', 'netra-auth'
    ]

    if (localhostHosts.includes(url.hostname)) {
      return true
    }

    // Check for Docker bridge network IPs (172.x.x.x range)
    if (url.hostname.startsWith('172.')) {
      return true
    }

    return false
  } catch {
    // Fallback regex pattern matching
    const localhostPattern = /^https?:\/\/(localhost|127\.0\.0\.1|0\.0\.0\.0|\[::1\]|frontend|backend|auth|netra-frontend|netra-backend|netra-auth|172\.\d+\.\d+\.\d+)(:\d+)?\/?$/i
    return localhostPattern.test(origin)
  }
}

/**
 * Check if origin matches staging patterns
 */
function matchesStagingPatterns(origin: string): boolean {
  const stagingPatterns = [
    // Staging subdomain patterns
    /^https:\/\/[a-zA-Z0-9\-]+\.staging\.netrasystems\.ai$/,
    
    // Cloud Run patterns
    /^https:\/\/netra-(frontend|backend|auth)-[0-9]+\.(us-central1|europe-west1|asia-northeast1)\.run\.app$/,
    /^https:\/\/[a-zA-Z0-9\-]+(-[a-zA-Z0-9]+)*-[a-z]{2}\.a\.run\.app$/
  ]

  return stagingPatterns.some(pattern => pattern.test(origin))
}

/**
 * Get CORS headers for a request
 */
export function getCorsHeaders(request: NextRequest): Record<string, string> {
  const origin = request.headers.get('origin') || ''
  const allowedOrigins = getCorsOrigins()
  const environment = detectEnvironment()
  
  // Determine the allowed origin for this request
  let allowOrigin = ''
  if (isOriginAllowed(origin, allowedOrigins, environment)) {
    allowOrigin = origin
  } else if (environment === 'development' && !origin) {
    // Allow requests without origin in development (e.g., Postman, server-to-server)
    allowOrigin = 'http://localhost:3000'
  }

  return {
    'Access-Control-Allow-Origin': allowOrigin,
    'Access-Control-Allow-Credentials': 'true',
    'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS, PATCH, HEAD',
    'Access-Control-Allow-Headers': 'Authorization, Content-Type, X-Request-ID, X-Trace-ID, Accept, Origin, Referer, X-Requested-With',
    'Access-Control-Expose-Headers': 'X-Trace-ID, X-Request-ID, Content-Length, Content-Type',
    'Access-Control-Max-Age': '3600',
    'Vary': 'Origin'
  }
}

/**
 * Handle OPTIONS preflight requests
 */
export function handleOptions(request: NextRequest): NextResponse {
  const corsHeaders = getCorsHeaders(request)
  
  return new NextResponse(null, {
    status: 204,
    headers: corsHeaders
  })
}

/**
 * Add CORS headers to a NextResponse
 */
export function addCorsHeaders(response: NextResponse, request: NextRequest): NextResponse {
  const corsHeaders = getCorsHeaders(request)
  
  Object.entries(corsHeaders).forEach(([key, value]) => {
    response.headers.set(key, value)
  })
  
  return response
}

/**
 * Create a JSON response with CORS headers
 */
export function corsJsonResponse(
  data: unknown, 
  request: NextRequest, 
  options: { status?: number } = {}
): NextResponse {
  const response = NextResponse.json(data, { status: options.status || 200 })
  return addCorsHeaders(response, request)
}

/**
 * Create an empty response with CORS headers
 */
export function corsEmptyResponse(
  request: NextRequest,
  options: { status?: number } = {}
): NextResponse {
  const response = new NextResponse(null, { status: options.status || 204 })
  return addCorsHeaders(response, request)
}