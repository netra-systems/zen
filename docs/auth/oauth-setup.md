# Google OAuth Setup Guide

## Prerequisites
- Google Cloud Console account
- A Google Cloud project

## Setup Steps

### 1. Create OAuth 2.0 Credentials

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Select your project or create a new one
3. Navigate to **APIs & Services** > **Credentials**
4. Click **+ CREATE CREDENTIALS** > **OAuth client ID**
5. If prompted, configure the OAuth consent screen first:
   - Choose "External" for testing
   - Fill in the required fields
   - Add your email to test users

### 2. Configure OAuth Client

1. Application type: **Web application**
2. Name: `Netra AI Development` (or your preferred name)
3. Authorized JavaScript origins:
   ```
   http://localhost:3000
   http://localhost:8000
   ```
4. Authorized redirect URIs:
   ```
   http://localhost:8000/auth/callback
   http://localhost:3000/auth/callback
   ```
5. Click **CREATE**

### 3. Save Credentials

After creating the OAuth client, you'll receive:
- **Client ID**: Copy this value
- **Client Secret**: Copy this value (keep it secure!)

### 4. Configure Environment Variables

#### Option A: Using .env file (Development)
Create or update `.env` file in the project root:
```bash
GOOGLE_CLIENT_ID=your_client_id_here
GOOGLE_CLIENT_SECRET=your_client_secret_here
```

#### Option B: Using Google Secret Manager (Production)
The application is configured to fetch secrets from Google Secret Manager:
- Secret name: `google-client-id`
- Secret name: `google-client-secret`

### 5. Development Mode

In development mode, the application provides:
- **Auto-login**: Automatically logs in as dev@example.com
- **OAuth Override**: Option to use real Google OAuth login

The development mode is enabled when `environment=development` in the configuration.

## Testing OAuth Flow

### 1. Start the Backend
```bash
python run_server.py
```

### 2. Start the Frontend
```bash
cd frontend
npm run dev
```

### 3. Test Login Flow
1. Navigate to http://localhost:3000
2. In development mode:
   - Auto-login as dev user should work
   - Click "OAuth Login" to test Google OAuth
3. In production mode:
   - Click "Login with Google"
   - Authenticate with your Google account
   - You'll be redirected back to the application

## Troubleshooting

### Common Issues

1. **Redirect URI mismatch**
   - Ensure the redirect URIs in Google Cloud Console match exactly
   - Check both backend and frontend URLs

2. **Invalid client**
   - Verify client ID and secret are correctly set
   - Check environment variables are loaded

3. **CORS errors**
   - Ensure frontend URL is in authorized JavaScript origins
   - Check backend CORS configuration

4. **Token not persisting**
   - Check browser localStorage
   - Verify token is being saved correctly

## Security Best Practices

1. **Never commit credentials**
   - Use environment variables
   - Add `.env` to `.gitignore`

2. **Use HTTPS in production**
   - Update redirect URIs for production
   - Use secure cookies

3. **Rotate secrets regularly**
   - Update client secret periodically
   - Use secret management tools

4. **Restrict OAuth scopes**
   - Only request necessary permissions
   - Currently using: openid, email, profile

## Additional Resources

- [Google OAuth 2.0 Documentation](https://developers.google.com/identity/protocols/oauth2)
- [Google Cloud Console](https://console.cloud.google.com/)
- [OAuth 2.0 Playground](https://developers.google.com/oauthplayground/)