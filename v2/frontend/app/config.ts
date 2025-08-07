
const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000';
const WS_BASE_URL = process.env.NEXT_PUBLIC_WS_BASE_URL || 'ws://localhost:8000';

export const config = {
    api: {
        baseUrl: `${API_BASE_URL}/api/v3`,
        wsBaseUrl: WS_BASE_URL,
        endpoints: {
            login: '/auth/token',
            devLogin: '/auth/dev-login',
            login: '/auth/token',
            devLogin: '/auth/dev-login',
            currentUser: '/auth/users/me',
            googleLogin: '/auth/google',
            logout: '/auth/logout',
            runs: '/runs'
        },
    },
};
