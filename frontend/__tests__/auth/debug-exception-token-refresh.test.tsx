/**
 * Debug test to check for exceptions
 */

import { unifiedAuthService } from '@/auth/unified-auth-service';
import * as jwtDecodeMock from 'jwt-decode';

// Mock jwt-decode
jest.mock('jwt-decode', () => ({
  jwtDecode: jest.fn(),
}));

describe('Debug Exception Token Refresh', () => {
  let mockJwtDecode: jest.MockedFunction<typeof jwtDecodeMock.jwtDecode>;
  
  beforeEach(() => {
    mockJwtDecode = jwtDecodeMock.jwtDecode as jest.MockedFunction<typeof jwtDecodeMock.jwtDecode>;
    jest.clearAllMocks();
  });

  test('should check if exception occurs in needsRefresh', () => {
    const now = Date.now();
    const iat = Math.floor(now / 1000) - 23; // issued 23 seconds ago
    const exp = Math.floor(now / 1000) + 7;  // expires in 7 seconds
    
    mockJwtDecode.mockReturnValue({
      exp,
      iat,
      sub: 'test-user',
    });

    console.log('Mocked jwt decode return:', mockJwtDecode('fake-token'));
    
    // Monkey patch the needsRefresh method to add logging
    const originalNeedsRefresh = unifiedAuthService.needsRefresh;
    unifiedAuthService.needsRefresh = function(token: string) {
      console.log('needsRefresh called with token:', token);
      try {
        const result = originalNeedsRefresh.call(this, token);
        console.log('needsRefresh completed, result:', result);
        return result;
      } catch (error) {
        console.log('needsRefresh threw error:', error);
        throw error;
      }
    };

    const result = unifiedAuthService.needsRefresh('fake-token');
    console.log('Final result:', result);
  });
});