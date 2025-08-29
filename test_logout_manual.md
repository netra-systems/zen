# Manual Logout Test Instructions

## Issue Fixed
The logout button was not working because the frontend was not sending the Authorization header with the JWT token when calling the logout endpoint.

## Fix Applied
Modified `frontend/lib/auth-service-client.ts` in the `logout()` method to:
1. Get the JWT token from localStorage
2. Include it in the Authorization header when calling the logout endpoint

## Test Steps

1. Start the development environment:
   ```bash
   python scripts/dev_launcher.py
   ```

2. Open browser to http://localhost:3000

3. Login (if in dev mode, it should auto-login)

4. Click the "Logout" button

5. Verify:
   - The logout button should successfully log you out
   - You should be redirected to the login page
   - The JWT token should be cleared from localStorage
   - Check browser console for any errors

## Expected Behavior
- Logout should complete successfully without errors
- User should be logged out and redirected appropriately
- No 401 Unauthorized errors in the network tab

## Code Changes
File: `frontend/lib/auth-service-client.ts`
- Added logic to retrieve JWT token from localStorage
- Added Authorization header with Bearer token to logout request
- Maintains backward compatibility (works without token too)

## Test Coverage
Created new test file: `frontend/__tests__/lib/auth-service-client-logout.test.ts`
- Tests logout with token (Authorization header included)
- Tests logout without token (no Authorization header)
- Tests error handling
- All tests passing ✓