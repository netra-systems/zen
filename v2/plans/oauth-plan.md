
# OAuth Implementation and Bug Fix Plan

This plan outlines the steps to implement a production-ready OAuth solution and fix the existing authentication bugs.

## 1. Triage and Bug Fix

- **Problem:** The frontend is throwing a `TypeError: devLogin is not a function` and a 404 error for `/api/v3/auth/endpoints`.
- **Action:**
    1. Examine `frontend/contexts/AuthContext.tsx` and `frontend/services/authService.ts` to identify the source of the `devLogin` error.
    2. Correct the import/export or usage of the `devLogin` function.
    3. Ensure the `getAuthConfig` function is called correctly and the frontend can successfully retrieve the authentication endpoints from the backend.

## 2. Backend OAuth Implementation

- **Goal:** Ensure the backend is fully configured to handle OAuth2 authentication.
- **Action:**
    1. **Configuration:**
        - Verify that the `OAuthConfig` in `app/schemas.py` is correctly populated from the application's configuration.
        - Ensure the `authorized_javascript_origins` and `authorized_redirect_uris` are correctly set for both development and production environments.
    2. **Routes:**
        - Review the existing OAuth routes in `app/routes/auth.py` (`/login/google`, `/callback/google`, `/logout`) to ensure they are functioning correctly.
        - The `/api/v3/auth/endpoints` route will be the single source of truth for the frontend to discover all authentication-related URLs.

## 3. Frontend OAuth Implementation

- **Goal:** Implement a seamless OAuth login experience on the frontend.
- **Action:**
    1. **Auth Context:**
        - Modify `frontend/contexts/AuthContext.tsx` to handle both the development login and the new OAuth flow.
        - The `login` function will redirect the user to the Google OAuth login page.
        - The `logout` function will call the backend's logout endpoint.
    2. **UI:**
        - Create a prominent and well-designed "Login with Google" button.
        - The application will show the user's information when they are logged in.
    3. **Development Mode:**
        - Maintain the existing functionality where the application automatically logs in a development user when in development mode.
        - The OAuth login will supersede the development login.

## 4. Validation

- **Goal:** Thoroughly test the entire authentication flow.
- **Action:**
    1. **Development:**
        - Verify that the application automatically logs in the development user on page load.
        - Test the OAuth login and logout flow in the development environment.
    2. **Production:**
        - Verify that the OAuth login and logout flow work correctly in a production-like environment.
    3. **Hot Reloading:**
        - Ensure that the authentication state is preserved during hot reloading in the development environment.
