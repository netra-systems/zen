import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';

export function middleware(request: NextRequest) {
  const response = NextResponse.next();

  // Check if we're in development mode
  // In middleware, we check the URL hostname or use a header-based approach
  const isDevelopment = request.nextUrl.hostname === 'localhost' || 
                        request.nextUrl.hostname === '127.0.0.1' ||
                        request.headers.get('host')?.includes('localhost');

  if (!isDevelopment) {
    // Production/staging environments
    response.headers.set('Strict-Transport-Security', 'max-age=31536000; includeSubDomains');
    // Remove CSP header here - let Next.js handle it with proper nonce support
    // The CSP should be configured in next.config.ts or _document.tsx for proper nonce injection
    response.headers.set('X-Content-Type-Options', 'nosniff');
    response.headers.set('X-Frame-Options', 'DENY');
    response.headers.set('X-XSS-Protection', '1; mode=block');
    response.headers.set('Referrer-Policy', 'strict-origin-when-cross-origin');
  }
  // In development, don't set CSP to avoid conflicts with Next.js hot reload

  return response;
}

export const config = {
  matcher: [
    /*
     * Match all request paths except for the ones starting with:
     * - api (API routes)
     * - _next/static (static files)
     * - _next/image (image optimization files)
     * - favicon.ico (favicon file)
     */
    '/((?!api|_next/static|_next/image|favicon.ico).*)',
  ],
};