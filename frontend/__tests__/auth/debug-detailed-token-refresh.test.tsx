/**
 * Debug test with detailed logging
 */

import { unifiedAuthService } from '@/auth/unified-auth-service';
import * as jwtDecodeMock from 'jwt-decode';

// Mock jwt-decode
jest.mock('jwt-decode', () => ({
  jwtDecode: jest.fn(),
}));

// Create a custom logger to capture the debug calls
const mockLogger = {
  debug: jest.fn(),
  info: jest.fn(),
  warn: jest.fn(),
  error: jest.fn(),
};

// Mock the logger 
jest.mock('@/lib/logger', () => ({
  logger: mockLogger,
}));

describe('Debug Detailed Token Refresh', () => {
  let mockJwtDecode: jest.MockedFunction<typeof jwtDecodeMock.jwtDecode>;
  
  beforeEach(() => {
    mockJwtDecode = jwtDecodeMock.jwtDecode as jest.MockedFunction<typeof jwtDecodeMock.jwtDecode>;
    jest.clearAllMocks();
  });

  test('should log the detailed calculation for 30-second token', () => {
    const now = Date.now();
    const iat = Math.floor(now / 1000) - 23; // issued 23 seconds ago
    const exp = Math.floor(now / 1000) + 7;  // expires in 7 seconds
    
    mockJwtDecode.mockReturnValue({
      exp,
      iat,
      sub: 'test-user',
    });

    console.log('=== BEFORE CALL ===');
    console.log('now (ms):', now);
    console.log('iat (seconds):', iat, '=> ms:', iat * 1000);
    console.log('exp (seconds):', exp, '=> ms:', exp * 1000);
    console.log('Expected totalLifetime (ms):', exp * 1000 - iat * 1000);
    console.log('Expected timeUntilExpiry (ms):', exp * 1000 - now);
    console.log('Expected refreshThreshold (ms, 25%):', (exp * 1000 - iat * 1000) * 0.25);

    const result = unifiedAuthService.needsRefresh('fake-token');

    console.log('=== AFTER CALL ===');
    console.log('Result:', result);
    console.log('Logger debug calls:', mockLogger.debug.mock.calls);

    if (mockLogger.debug.mock.calls.length > 0) {
      const debugCall = mockLogger.debug.mock.calls[0];
      console.log('Debug message:', debugCall[0]);
      console.log('Debug data:', debugCall[1]);
    }
  });
});