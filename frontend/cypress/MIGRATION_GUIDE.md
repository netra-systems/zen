# Cypress Authentication Migration Guide

## Overview
This guide helps migrate existing Cypress tests to use the unified authentication system.

## Quick Start

### Before (Old Pattern)
```typescript
// Multiple inconsistent methods:
cy.window().then((win) => {
  win.localStorage.setItem('jwt_token', 'test-jwt-token');
});

// Or:
cy.window().then((win) => {
  win.localStorage.setItem('auth_token', TEST_USER.token);
});

// Or:
export function setupAuth(): void {
  cy.window().then((win) => {
    win.localStorage.setItem('jwt_token', 'test-jwt-token');
  });
}
```

### After (New Unified Pattern)
```typescript
import { setupAuthenticatedState } from '../support/auth-helpers';
// Or for complete test setup:
import { setupTestWithAuth, visitWithAuth } from '../support/test-auth-config';

// Simple auth setup:
setupAuthenticatedState();

// Visit page with auth:
visitWithAuth('/chat');

// Complete test setup with auth:
beforeEach(() => {
  setupTestWithAuth();
  cy.visit('/chat');
});
```

## Migration Steps

### 1. Update Imports
Replace local auth functions with unified imports:

```typescript
// Remove:
function setupAuth() { /* ... */ }

// Add:
import { setupAuthenticatedState } from '../support/auth-helpers';
```

### 2. Update BeforeEach Hooks
```typescript
// Old:
beforeEach(() => {
  cy.window().then((win) => {
    win.localStorage.setItem('jwt_token', 'test-jwt-token');
  });
  cy.visit('/chat');
});

// New:
import { authBeforeEach } from '../support/test-auth-config';

beforeEach(() => {
  authBeforeEach();
  cy.visit('/chat');
});
```

### 3. Update Login Commands
```typescript
// Old:
cy.login('test@example.com', 'password');

// New (for most tests):
setupAuthenticatedState();
cy.visit('/chat');

// Or for real login tests:
Cypress.env('USE_REAL_LOGIN', true);
cy.login();
```

### 4. Consistent Token Names
All tests now use `jwt_token` (not `auth_token` or other variations):

```typescript
// Checking for token:
cy.window().then((win) => {
  const token = win.localStorage.getItem('jwt_token'); // Always jwt_token
  expect(token).to.exist;
});
```

## Available Helpers

### Core Authentication (`auth-helpers.ts`)
- `setupAuthenticatedState(user?)` - Set up JWT token and user data
- `clearAuthState()` - Clear all auth data
- `setupAuthEndpoints()` - Mock auth API endpoints
- `performUILogin(email?, password?)` - Real UI login flow
- `verifyAuthenticated()` - Verify auth state

### Test Configuration (`test-auth-config.ts`)
- `setupTestWithAuth()` - Complete test setup with auth
- `visitWithAuth(url)` - Visit page with auth
- `authBeforeEach()` - Standard beforeEach hook
- `verifyAuthenticatedPage(url)` - Verify auth and URL
- `TEST_USERS` - Pre-configured test users
- `AUTH_ALIASES` - Standard intercept aliases

## Example Migration

### Thread Management Test
```typescript
// Before:
export function setupAuth(): void {
  cy.window().then((win) => {
    win.localStorage.setItem('jwt_token', 'test-jwt-token');
  });
}

export function setupThreadTestEnvironment(): void {
  setupAuth();
  setupThreadMocks();
  cy.visit('/chat');
}

// After:
import { setupAuthenticatedState } from '../support/auth-helpers';

export function setupAuth(): void {
  setupAuthenticatedState();
}

export function setupThreadTestEnvironment(): void {
  setupAuth();
  setupThreadMocks();
  cy.visit('/chat');
}
```

## Benefits of Migration

1. **Consistency**: All tests use the same authentication method
2. **Maintainability**: Single source of truth for auth logic
3. **Flexibility**: Easy to switch between mock and real auth
4. **Reliability**: Proper JWT token structure with expiry handling
5. **Type Safety**: TypeScript interfaces for user data

## Testing Different User Types

```typescript
import { setupAuthenticatedState } from '../support/auth-helpers';
import { TEST_USERS } from '../support/test-auth-config';

// Default user:
setupAuthenticatedState();

// Admin user:
setupAuthenticatedState(TEST_USERS.admin);

// Custom user:
setupAuthenticatedState({
  id: 'custom-id',
  email: 'custom@example.com',
  full_name: 'Custom User'
});
```

## Troubleshooting

### Token Not Found
Ensure you're checking for `jwt_token` (not `auth_token`):
```typescript
win.localStorage.getItem('jwt_token'); // Correct
win.localStorage.getItem('auth_token'); // Wrong
```

### Login Failing
Check if you need real login vs mock:
```typescript
// For integration tests needing real login:
Cypress.env('USE_REAL_LOGIN', true);

// For most tests (faster):
setupAuthenticatedState();
```

### WebSocket Authentication
WebSocket tests should also use the unified auth:
```typescript
beforeEach(() => {
  setupTestWithAuth(); // Includes WebSocket mock
  cy.visit('/chat');
});
```