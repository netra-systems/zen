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
    response.headers.set(
      'Content-Security-Policy',
      "default-src 'self' https:; script-src 'self' 'unsafe-eval' 'unsafe-inline' https:; style-src 'self' 'unsafe-inline' https:; img-src 'self' data: https:; connect-src 'self' https: wss:; font-src 'self' https:; media-src 'self' https:; frame-src 'self' https:; upgrade-insecure-requests;"
    );
    response.headers.set('X-Content-Type-Options', 'nosniff');
    response.headers.set('X-Frame-Options', 'DENY');
    response.headers.set('X-XSS-Protection', '1; mode=block');
    response.headers.set('Referrer-Policy', 'strict-origin-when-cross-origin');
  } else {
    // Development mode: Explicitly allow all localhost connections
    response.headers.set(
      'Content-Security-Policy',
      "default-src 'self' http://localhost:* http://127.0.0.1:* ws://localhost:* ws://127.0.0.1:*; " +
      "script-src 'self' 'unsafe-eval' 'unsafe-inline' http://localhost:* http://127.0.0.1:*; " +
      "style-src 'self' 'unsafe-inline' http://localhost:* http://127.0.0.1:*; " +
      "img-src 'self' data: blob: http://localhost:* http://127.0.0.1:*; " +
      "connect-src 'self' http://localhost:* http://127.0.0.1:* ws://localhost:* ws://127.0.0.1:* wss://localhost:* wss://127.0.0.1:*; " +
      "font-src 'self' data: http://localhost:* http://127.0.0.1:*; " +
      "media-src 'self' http://localhost:* http://127.0.0.1:*; " +
      "frame-src 'self' http://localhost:* http://127.0.0.1:*;"
    );
  }

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