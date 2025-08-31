/**
 * Direct test without mocking complications
 */

// Don't mock jwt-decode, let it work naturally
import { jwtDecode } from 'jwt-decode';

describe('Direct Token Refresh Test', () => {
      setupAntiHang();
    jest.setTimeout(10000);
  test('should test needsRefresh with real JWT tokens', () => {
    // Import the service after mocks are set up
    const { unifiedAuthService } = require('@/auth/unified-auth-service');
    
    console.log('Service imported:', typeof unifiedAuthService);
    console.log('needsRefresh method:', typeof unifiedAuthService.needsRefresh);
    
    // Create a real JWT token that expires soon
    const header = { alg: 'HS256', typ: 'JWT' };
    const now = Math.floor(Date.now() / 1000);
    const payload = {
      sub: 'test-user',
      iat: now - 23,  // issued 23 seconds ago
      exp: now + 7    // expires in 7 seconds
    };
    
    // Create base64 encoded JWT (without signature verification)
    const encodedHeader = Buffer.from(JSON.stringify(header)).toString('base64url');
    const encodedPayload = Buffer.from(JSON.stringify(payload)).toString('base64url');
    const fakeJwt = `${encodedHeader}.${encodedPayload}.fake-signature`;
    
    console.log('Created JWT payload:', payload);
    console.log('Total lifetime:', payload.exp - payload.iat, 'seconds');
    console.log('Time until expiry:', payload.exp - now, 'seconds');
    
    // Test decoding works
    try {
      const decoded = jwtDecode(fakeJwt);
      console.log('Decoded JWT:', decoded);
    } catch (e) {
      console.log('JWT decode error:', e);
    }
    
    // Test needsRefresh
    const result = unifiedAuthService.needsRefresh(fakeJwt);
    console.log('needsRefresh result:', result);
  });
  afterEach(() => {
    cleanupAntiHang();
  });

});