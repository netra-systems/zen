# CRITICAL: Dev Auto-Login Dependencies

## ⚠️ WARNING
**ANY changes to the following subsystems MUST be tested with `__tests__/auth/dev-auto-login.test.tsx`**

Breaking the dev auto-login system severely impacts developer productivity.

## Critical Files and Functions

### 1. Auth Context (`frontend/auth/context.tsx`)
- **Lines 45-58**: Token state initialization from localStorage
- **Lines 177-225**: Token processing logic (MUST handle storedToken === currentToken)
- **Lines 225-251**: Dev auto-login attempt
- **Lines 293-335**: useEffect initialization (uses hasMountedRef to prevent duplicates)

### 2. Unified Auth Service (`frontend/auth/unified-auth-service.ts`)
- **Lines 86-175**: `handleDevLogin()` - Requires 5+ retries with exponential backoff
- **Lines 38-80**: `getAuthConfig()` - Must handle backend being offline gracefully

### 3. Components
- **LoginButton.tsx**: Changes must preserve auto-login flow
- **AuthProvider**: Loading states must not block UI completely

## Cross-Referenced Learnings

1. **`SPEC/learnings/frontend_dev_autologin.xml`** - Complete auto-login implementation details
2. **`SPEC/learnings/frontend_loading_states.xml`** - Loading state hierarchy and UX requirements
3. **`SPEC/learnings/frontend_initialization_patterns.xml`** - Initialization best practices

## Testing Requirements

### Must Run After Changes To:
- Auth context initialization
- Token processing logic
- Loading states
- UX components that interact with auth
- Environment configuration
- Backend startup sequence

### Test Command:
```bash
cd frontend
npm test -- __tests__/auth/dev-auto-login.test.tsx
```

### Expected Results:
- 11 tests passing (1 skipped due to timing sensitivity)
- Auto-login completes within 3 seconds under normal conditions
- Handles backend startup delays up to ~63 seconds with retries

## Common Regression Points

### 1. Token Processing
**Issue**: Checking `storedToken !== currentToken` before processing
**Fix**: Process token if `storedToken` exists, regardless of equality

### 2. Retry Logic
**Issue**: Simple retries without backoff
**Fix**: Exponential backoff: 1s, 2s, 4s, 8s, 16s (+ jitter)

### 3. Loading States
**Issue**: Blocking entire UI during auth initialization
**Fix**: Show partial content, use skeleton screens

### 4. Dev Logout Flag
**Issue**: Not respecting user's explicit logout
**Fix**: Check `dev_logout_flag` before auto-login attempt

## Implementation Checklist

When modifying auth/loading/init systems:

- [ ] Read this document completely
- [ ] Review `frontend_dev_autologin.xml` learning
- [ ] Make changes
- [ ] Run dev-auto-login tests
- [ ] Test manually with backend offline
- [ ] Test manually with slow backend startup
- [ ] Test page refresh preserves login state
- [ ] Test explicit logout prevents auto-login
- [ ] Update learnings if new patterns discovered

## Contact for Issues

If dev auto-login breaks:
1. Check recent commits to auth/context.tsx
2. Review token processing logic (lines 177-225)
3. Verify retry logic has exponential backoff
4. Run tests to identify specific failure
5. Consult learnings documents for solutions