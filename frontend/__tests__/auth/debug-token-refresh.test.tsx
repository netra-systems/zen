/**
 * Debug test for token refresh functionality
 */

import { unifiedAuthService } from '@/auth/unified-auth-service';

describe('Debug Token Refresh', () => {
  test('should call needsRefresh method', () => {
    // Create a simple mock token
    const mockToken = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyLCJleHAiOjE1MTYyMzkwMjJ9.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c';
    
    console.log('Testing needsRefresh with mock token...');
    console.log('Service:', typeof unifiedAuthService);
    console.log('needsRefresh method:', typeof unifiedAuthService.needsRefresh);
    
    try {
      const result = unifiedAuthService.needsRefresh(mockToken);
      console.log('needsRefresh result:', result);
    } catch (error) {
      console.log('Error calling needsRefresh:', error);
    }
  });
});