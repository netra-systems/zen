# User Authentication Plan

This document outlines the plan to implement user authentication (login, logout, OAuth) based on the `userauth.txt` spec.

## Backend

- **`app/auth/services.py`**: Created a `SecurityService` class with methods to get a user by ID and to get or create a user from OAuth information. This service is used by the auth routes.
- **`app/routes/auth.py`**: This file was already implemented with endpoints for `/login/google`, `/callback/google`, `/logout`, `/dev-login`, and `/user`.
- **`app/models/user.py`**: The `User` model was already defined.
- **`app/schemas.py`**: User-related schemas were already defined.
- **`app/config.py`**: Configuration for OAuth and the development user was already in place.

## Frontend

- **`frontend/services/auth.ts`**: Created functions to fetch the auth configuration from the backend and to handle login and logout redirects.
- **`frontend/contexts/AuthContext.tsx`**: The `AuthContext` was already implemented to manage the user's authentication state.
- **`frontend/components/auth/LoginButton.tsx`**: Created a new `LoginButton` component to provide a consistent login/logout UI.
- **`frontend/components/Header.tsx`**: Replaced the existing login/logout UI with the new `LoginButton` component to centralize the logic and match the spec.
- **`frontend/app/auth/callback/page.tsx`**: This page was already implemented to handle the redirect from the backend after a successful OAuth login.

## Next Steps

- The implementation is now complete based on the provided files and the `userauth.txt` spec.
- The next step would be to run the application and test the authentication flow thoroughly.