
import { create } from 'zustand';
import { apiService } from './api'; // Assuming apiService is exported from page.tsx
import { config } from './config';

interface User {
    full_name?: string;
    email: string;
}

interface AppState {
    user: User | null;
    token: string | null;
    isLoading: boolean;
    authError: string | null;
    fetchUser: (token: string) => Promise<void>;
    login: (formData: FormData) => Promise<void>;
    logout: () => void;
}

export const useAppStore = create<AppState>((set, get) => ({
    user: null,
    token: null,
    isLoading: true,
    authError: null,
    fetchUser: async (token) => {
        try {
            const userData = await apiService.get(config.api.endpoints.currentUser, token);
            set({ user: userData, token });
        } catch (error) {
            console.error("Failed to fetch user, logging out.", error);
            set({ user: null, token: null, isLoading: false });
            if (typeof window !== 'undefined') {
                localStorage.removeItem('authToken');
            }
        }
    },
    login: async (formData) => {
        set({ authError: null });
        try {
            const response = await fetch(config.api.endpoints.login, {
                method: 'POST',
                body: formData,
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || 'Login failed');
            }

            const { access_token } = await response.json();
            localStorage.setItem('authToken', access_token);
            await get().fetchUser(access_token);
        } catch (error: unknown) {
            console.error(error);
            set({ authError: error instanceof Error ? error.message : 'An unexpected error occurred during login.', isLoading: false });
        }
    },
    logout: () => {
        set({ user: null, token: null });
        localStorage.removeItem('authToken');
    },
}));
