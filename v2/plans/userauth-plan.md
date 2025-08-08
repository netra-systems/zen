
# Plan: User Authentication (OAuth & Dev Mode)

This plan outlines the steps to implement user authentication using Google OAuth for production and a development mode with an auto-login feature, as specified in `userauth.txt`.

## 1. Backend (FastAPI)

### Create Auth Routes (`app/routes/auth.py`)

- **Create a new file `app/routes/auth.py`** to house all authentication-related endpoints.
- **Login (`/api/auth/login/google`):** Create a route that initiates the Google OAuth flow using the `oauth.google.authorize_redirect` method.
- **Callback (`/api/auth/callback/google`):** This route will be the redirect URI for Google. It will handle the OAuth callback, fetch the user information, create or update the user in the database, and set the user's information in the session.
- **Logout (`/api/auth/logout`):** Create a route that clears the user's session.
- **Auth Config (`/api/auth/config`):** Create an endpoint that returns the `AuthConfigResponse` schema, providing the frontend with the Google Client ID, auth endpoints, and development mode status.

### Update `app/main.py`

- Include the new `auth_router` in the main FastAPI app.

### Configuration (`.env` and `config.py`)

- The user will provide the `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET` to be added to the `.env` file.
- Ensure `config.py` loads these variables and the `AUTHORIZED_REDIRECT_URIS` correctly.

## 2. Frontend (Next.js/React)

### Refine `AuthContext.tsx`

- Update the `login` function to redirect to the new `/api/auth/login/google` endpoint.
- Implement the `logout` function to call the `/api/auth/logout` endpoint and clear the user from the state.
- Ensure the `fetchEndpoints` function correctly fetches the configuration from `/api/auth/config`.

### Update Login UI

- The main login button will be in the `AuthProvider`, which will be displayed when the user is not authenticated. It will be large and styled appropriately.
- The dedicated `/login` page will also use this button.

### Create a Header Component

- Create a new header component that will be displayed on all pages.
- The header will display the user's name and a "Logout" button when the user is authenticated.

### Update `layout.tsx`

- Add the new header component to the main layout file so it's persistent across all pages.

## 3. Testing

- **Backend:** Add integration tests for the new authentication endpoints.
- **Frontend:** Add tests for the `AuthContext` and the login/logout functionality.
- **Manual:** Thoroughly test the entire login/logout flow in both development and production (or simulated production) environments.
