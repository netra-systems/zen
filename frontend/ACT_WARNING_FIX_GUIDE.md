# Authentication & JWT Token Fix Guide

## Overview
This document outlines the comprehensive fixes applied to resolve authentication and JWT token issues in frontend integration tests.

## Issues Fixed

### 1. JWT Token Format
**Problem**: Tests were using simple mock tokens like `'mock-token'` or `'test-jwt-token'`
**Solution**: Implemented proper JWT token format:
```typescript
const mockJWTToken = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjoidGVzdC11c2VyLTEyMyIsImVtYWlsIjoidGVzdEBleGFtcGxlLmNvbSIsImV4cCI6OTk5OTk5OTk5OX0.test-signature';
```

### 2. MSW Handlers Authentication
**Problem**: Auth endpoints didn't return proper JWT tokens
**Solution**: Updated handlers to return complete auth responses:
```typescript
// /auth/login now returns:
{
  token: mockJWTToken,
  user: { id: 'test-user-123', email: 'test@example.com', full_name: 'Test User' },
  access_token: mockJWTToken,
  token_type: 'Bearer'
}

// /auth/verify validates JWT tokens properly
// /api/protected-data requires Bearer token authentication
```

### 3. LocalStorage Token Management
**Problem**: Tokens weren't properly stored/retrieved from localStorage
**Solution**: 
- Enhanced localStorage mock to persist auth tokens across test cleanup
- Added token validation in auth flows
- Proper token removal during logout

### 4. Authentication State Consistency
**Problem**: Different auth hooks/stores returned inconsistent states
**Solution**: Unified authentication mocks across:
- `@/auth/service` - Auth service layer
- `@/auth/context` - React context provider  
- `@/store/authStore` - Zustand store
- All hooks return `isAuthenticated: true` and proper JWT tokens

### 5. Bearer Token Headers
**Problem**: Authenticated requests didn't include proper Authorization headers
**Solution**: 
- Added `createAuthenticatedRequest` helper
- All authenticated API calls include `Authorization: Bearer <jwt-token>`
- WebSocket auth endpoint validates Bearer tokens

## Key Files Modified

1. **frontend/mocks/handlers.ts**
   - Added JWT token support to auth endpoints
   - Enhanced token validation
   - Added protected data endpoint for testing

2. **frontend/jest.setup.js**
   - Updated all auth-related mocks with proper JWT tokens
   - Enhanced localStorage persistence
   - Unified authentication state across all mocks

3. **frontend/__tests__/helpers/initial-state-helpers.tsx**
   - Added auth token initialization
   - Enhanced token validation in test components

4. **frontend/__tests__/integration/helpers/test-builders.ts**
   - Updated mock factories to use proper JWT format
   - Added authenticated request builders

5. **frontend/__tests__/integration/basic-integration-auth.test.tsx**
   - Enhanced auth flow tests with proper JWT handling
   - Added authentication failure scenarios
   - Improved token storage validation

6. **frontend/__mocks__/services/mcp-client-service.ts**
   - Comprehensive MCP service mock
   - Prevents missing service errors in tests

## Testing Patterns

### Authenticated Requests
```typescript
// Use the helper for consistent auth requests
const authRequest = createAuthenticatedRequest('/api/protected-data');
const response = await fetch(authRequest.url, authRequest.options);
```

### Token Validation
```typescript
// Check token is stored properly
expect(localStorage.getItem('token')).toBe(mockJWTToken);
expect(localStorage.getItem('auth_token')).toBe(mockJWTToken);
```

### Authentication State
```typescript
// All auth hooks now return consistent state
const { isAuthenticated, user, token } = useAuth();
expect(isAuthenticated).toBe(true);
expect(token).toMatch(/^eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ5/);
```

## Error Prevention

### Common Pitfalls Fixed
1. **Token Format**: Always use proper JWT format, not simple strings
2. **Storage Cleanup**: Tokens persist across test cleanup cycles for consistency  
3. **Header Format**: Use `Authorization: Bearer <token>`, not just the token
4. **Response Format**: Auth endpoints return complete objects, not just tokens
5. **Validation**: All auth checks validate actual JWT structure

### Test Stability
- Eliminated race conditions in auth state updates
- Consistent mock state across all test files
- Proper async/await patterns for auth operations
- Act() wrapper usage to prevent React warnings

## Usage Examples

### Login Flow Test
```typescript
it('should handle login with JWT token', async () => {
  const mockUser = createMockUser();
  const mockToken = createMockToken(); // Returns proper JWT
  
  await act(async () => {
    fireEvent.click(getByText('Login'));
  });
  
  expect(localStorage.getItem('token')).toBe(mockToken);
  expect(getByTestId('auth-status')).toHaveTextContent('Logged in');
});
```

### Authenticated API Test
```typescript
it('should make authenticated requests', async () => {
  const { url, options } = createAuthenticatedRequest('/api/protected-data');
  
  const response = await fetch(url, options);
  
  expect(response.ok).toBe(true);
  expect(options.headers.Authorization).toMatch(/^Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9/);
});
```

## Summary

These fixes provide a comprehensive solution for JWT token handling in frontend tests:
- ✅ Proper JWT token format across all tests
- ✅ Consistent authentication state management  
- ✅ Bearer token header support
- ✅ localStorage token persistence
- ✅ Authentication flow validation
- ✅ WebSocket auth token handling
- ✅ Error scenario testing

All authentication-related integration tests should now pass with proper JWT token handling and consistent authentication state.