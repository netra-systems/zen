/**
 * Frontend Health Check API Endpoint
 * Provides health status for the Next.js frontend application
 */
import { NextRequest, NextResponse } from 'next/server'
import { corsJsonResponse, handleOptions } from '@/lib/cors-utils'

export async function GET(request: NextRequest) {
  try {
    // Basic health check for frontend
    const healthData = {
      status: 'healthy',
      service: 'frontend',
      version: '1.0.0',
      timestamp: new Date().toISOString(),
      environment: process.env.NODE_ENV || 'development',
      uptime: process.uptime(),
      memory: {
        used: Math.round(process.memoryUsage().heapUsed / 1024 / 1024),
        total: Math.round(process.memoryUsage().heapTotal / 1024 / 1024),
        rss: Math.round(process.memoryUsage().rss / 1024 / 1024),
      }
    }

    return corsJsonResponse(healthData, request, { status: 200 })
  } catch (error) {
    console.error('Health check error:', error)
    
    return corsJsonResponse({
      status: 'unhealthy',
      service: 'frontend', 
      version: '1.0.0',
      timestamp: new Date().toISOString(),
      error: error instanceof Error ? error.message : 'Unknown error'
    }, request, { status: 503 })
  }
}

export async function OPTIONS(request: NextRequest) {
  return handleOptions(request);
}