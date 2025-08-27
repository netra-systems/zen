/**
 * Frontend Readiness Check API Endpoint
 * Indicates if the frontend is ready to serve traffic
 */
import { NextRequest, NextResponse } from 'next/server'
import { corsJsonResponse, handleOptions } from '@/lib/cors-utils'

export async function GET(request: NextRequest) {
  try {
    // Check if the application is ready to serve requests
    const readinessChecks = await performReadinessChecks()
    
    if (readinessChecks.ready) {
      return corsJsonResponse({
        status: 'ready',
        service: 'frontend',
        version: '1.0.0',
        timestamp: new Date().toISOString(),
        checks: readinessChecks.details
      }, request, { status: 200 })
    } else {
      return corsJsonResponse({
        status: 'not_ready',
        service: 'frontend',
        version: '1.0.0', 
        timestamp: new Date().toISOString(),
        checks: readinessChecks.details,
        errors: readinessChecks.errors
      }, request, { status: 503 })
    }
  } catch (error) {
    console.error('Readiness check error:', error)
    
    return corsJsonResponse({
      status: 'not_ready',
      service: 'frontend',
      version: '1.0.0',
      timestamp: new Date().toISOString(),
      error: error instanceof Error ? error.message : 'Unknown error'
    }, request, { status: 503 })
  }
}

async function performReadinessChecks(): Promise<{
  ready: boolean
  details: Record<string, { status: string; message?: string }>
  errors: string[]
}> {
  const checks: Record<string, { status: string; message?: string }> = {}
  const errors: string[] = []

  // Check if basic Node.js runtime is ready
  try {
    checks.runtime = {
      status: 'ok',
      message: `Node.js ${process.version}, uptime: ${Math.floor(process.uptime())}s`
    }
  } catch (error) {
    checks.runtime = { status: 'error', message: 'Runtime check failed' }
    errors.push('Runtime check failed')
  }

  // Check if environment variables are loaded
  try {
    const hasBasicConfig = process.env.NODE_ENV !== undefined
    checks.configuration = {
      status: hasBasicConfig ? 'ok' : 'warning',
      message: hasBasicConfig ? 'Environment loaded' : 'Limited configuration'
    }
  } catch (error) {
    checks.configuration = { status: 'error', message: 'Config check failed' }
    errors.push('Configuration check failed')
  }

  // Check memory usage (warn if over 500MB)
  try {
    const memoryUsageMB = Math.round(process.memoryUsage().heapUsed / 1024 / 1024)
    const memoryStatus = memoryUsageMB > 500 ? 'warning' : 'ok'
    checks.memory = {
      status: memoryStatus,
      message: `Heap usage: ${memoryUsageMB}MB`
    }
  } catch (error) {
    checks.memory = { status: 'error', message: 'Memory check failed' }
    errors.push('Memory check failed')
  }

  // Optional: Check backend connectivity (non-blocking)
  try {
    const backendUrl = process.env.NEXT_PUBLIC_API_URL || process.env.API_URL
    if (backendUrl) {
      // We'll mark as ready even if backend is unavailable since frontend can still serve
      checks.backend_connectivity = {
        status: 'info',
        message: `Backend configured: ${backendUrl}`
      }
    } else {
      checks.backend_connectivity = {
        status: 'warning', 
        message: 'Backend URL not configured'
      }
    }
  } catch (error) {
    checks.backend_connectivity = {
      status: 'warning',
      message: 'Backend connectivity check failed'
    }
  }

  // Frontend is considered ready if basic runtime checks pass
  const criticalErrors = errors.filter(error => 
    error.includes('Runtime') || error.includes('Configuration')
  )
  
  return {
    ready: criticalErrors.length === 0,
    details: checks,
    errors: criticalErrors
  }
}

export async function OPTIONS(request: NextRequest) {
  return handleOptions(request);
}