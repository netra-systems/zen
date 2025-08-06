
const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000';
const WS_BASE_URL = process.env.NEXT_PUBLIC_WS_BASE_URL || 'ws://localhost:8000';

export const config = {
    api: {
        baseUrl: `${API_BASE_URL}/api/v3`,
        wsBaseUrl: WS_BASE_URL,
        endpoints: {
            login: `${API_BASE_URL}/auth/token`,
            currentUser: `${API_BASE_URL}/auth/users/me`,
            runs: `${API_BASE_URL}/runs`,
        },
    },
};
