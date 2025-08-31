/**
 * @fileoverview Fixed tests for environment-aware token refresh behavior
 */

// First unmock the unified-auth-service to test real implementation
jest.unmock('@/auth/unified-auth-service');
jest.unmock('@/lib/unified-api-config');
jest.unmock('@/lib/logger');
jest.unmock('@/lib/auth-service-client');

import { unifiedAuthService } from '@/auth/unified-auth-service';
import { jwtDecode } from 'jwt-decode';
import { setupAntiHang, cleanupAntiHang } from '@/__tests__/utils/anti-hanging-test-utilities';

// Mock jwt-decode at the module level
jest.mock('jwt-decode', () => ({
  jwtDecode: jest.fn(),
}));

describe('Token Refresh Fixed Tests', () => {
  setupAntiHang();
    jest.setTimeout(10000);
  const mockJwtDecode = jwtDecode as jest.MockedFunction<typeof jwtDecode>;
  
  beforeEach(() => {
    jest.clearAllMocks();
  });

  test('should refresh at 25% of lifetime for 30-second token', () => {
    // Use a fixed timestamp to ensure consistency
    const fixedNow = 1640995200000; // Fixed timestamp for testing
    jest.spyOn(Date, 'now').mockReturnValue(fixedNow);
    
    const nowInSeconds = Math.floor(fixedNow / 1000);
    const iat = nowInSeconds - 23; // issued 23 seconds ago
    const exp = nowInSeconds + 7;  // expires in 7 seconds
    
    mockJwtDecode.mockReturnValue({
      exp,
      iat,
      sub: 'test-user',
    });

    const result = unifiedAuthService.needsRefresh('fake-token');

    // For 30s token (total lifetime), 25% = 7.5s
    // With 7 seconds remaining, should need refresh
    expect(result).toBe(true);
    
    // Restore Date.now
    jest.restoreAllMocks();
  });

  test('should NOT refresh at 50% of lifetime for 30-second token', () => {
    // Use a fixed timestamp to ensure consistency
    const fixedNow = 1640995200000; // Fixed timestamp for testing
    jest.spyOn(Date, 'now').mockReturnValue(fixedNow);
    
    const nowInSeconds = Math.floor(fixedNow / 1000);
    const iat = nowInSeconds - 15; // issued 15 seconds ago
    const exp = nowInSeconds + 15; // expires in 15 seconds
    
    mockJwtDecode.mockReturnValue({
      exp,
      iat,
      sub: 'test-user',
    });

    const result = unifiedAuthService.needsRefresh('fake-token');

    // For 30s token, should not refresh at 50% lifetime (15s remaining)
    // Refresh threshold is 25% = 7.5s
    expect(result).toBe(false);
    
    // Restore Date.now
    jest.restoreAllMocks();
  });

  test('should refresh 5 minutes before expiry for 15-minute token', () => {
    // Use a fixed timestamp to ensure consistency
    const fixedNow = 1640995200000; // Fixed timestamp for testing
    jest.spyOn(Date, 'now').mockReturnValue(fixedNow);
    
    const nowInSeconds = Math.floor(fixedNow / 1000);
    const iat = nowInSeconds - 10 * 60; // issued 10 minutes ago
    const exp = nowInSeconds + 4 * 60;  // expires in 4 minutes
    
    mockJwtDecode.mockReturnValue({
      exp,
      iat,
      sub: 'test-user',
    });

    const result = unifiedAuthService.needsRefresh('fake-token');

    // For 15-minute token, should refresh when < 5 minutes remain
    expect(result).toBe(true);
    
    // Restore Date.now
    jest.restoreAllMocks();
  });
  afterEach(() => {
    cleanupAntiHang();
  });

});