/**
 * @fileoverview Fixed tests for environment-aware token refresh behavior
 */

import { unifiedAuthService } from '@/auth/unified-auth-service';
import * as jwtDecodeMock from 'jwt-decode';

// Mock jwt-decode at the module level
jest.mock('jwt-decode', () => ({
  jwtDecode: jest.fn(),
}));

describe('Token Refresh Fixed Tests', () => {
  let mockJwtDecode: jest.MockedFunction<typeof jwtDecodeMock.jwtDecode>;
  
  beforeEach(() => {
    mockJwtDecode = jwtDecodeMock.jwtDecode as jest.MockedFunction<typeof jwtDecodeMock.jwtDecode>;
    jest.clearAllMocks();
  });

  test('should refresh at 25% of lifetime for 30-second token', () => {
    const now = Date.now();
    const iat = Math.floor(now / 1000) - 23; // issued 23 seconds ago
    const exp = Math.floor(now / 1000) + 7;  // expires in 7 seconds
    
    mockJwtDecode.mockReturnValue({
      exp,
      iat,
      sub: 'test-user',
    });

    const result = unifiedAuthService.needsRefresh('fake-token');

    console.log('Test result:', result);
    console.log('Token data:', { iat, exp, now: Math.floor(now / 1000) });
    console.log('Time until expiry:', exp - Math.floor(now / 1000), 'seconds');
    console.log('Total lifetime:', exp - iat, 'seconds');

    // For 30s token (total lifetime), 25% = 7.5s
    // With 7 seconds remaining, should need refresh
    expect(result).toBe(true);
  });

  test('should NOT refresh at 50% of lifetime for 30-second token', () => {
    const now = Date.now();
    const iat = Math.floor(now / 1000) - 15; // issued 15 seconds ago
    const exp = Math.floor(now / 1000) + 15; // expires in 15 seconds
    
    mockJwtDecode.mockReturnValue({
      exp,
      iat,
      sub: 'test-user',
    });

    const result = unifiedAuthService.needsRefresh('fake-token');

    console.log('Test 2 result:', result);
    console.log('Token data:', { iat, exp, now: Math.floor(now / 1000) });
    console.log('Time until expiry:', exp - Math.floor(now / 1000), 'seconds');
    console.log('Total lifetime:', exp - iat, 'seconds');

    // For 30s token, should not refresh at 50% lifetime (15s remaining)
    // Refresh threshold is 25% = 7.5s
    expect(result).toBe(false);
  });

  test('should refresh 5 minutes before expiry for 15-minute token', () => {
    const now = Date.now();
    const iat = Math.floor(now / 1000) - 10 * 60; // issued 10 minutes ago
    const exp = Math.floor(now / 1000) + 4 * 60;  // expires in 4 minutes
    
    mockJwtDecode.mockReturnValue({
      exp,
      iat,
      sub: 'test-user',
    });

    const result = unifiedAuthService.needsRefresh('fake-token');

    console.log('Test 3 result:', result);
    console.log('Token data:', { iat, exp, now: Math.floor(now / 1000) });
    console.log('Time until expiry:', (exp - Math.floor(now / 1000)) / 60, 'minutes');
    console.log('Total lifetime:', (exp - iat) / 60, 'minutes');

    // For 15-minute token, should refresh when < 5 minutes remain
    expect(result).toBe(true);
  });
});