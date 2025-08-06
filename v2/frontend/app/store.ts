import { create } from 'zustand';
import { apiService } from './api';
import { config } from './config';
import { Message } from './types';


interface User {
    id: number;
    full_name?: string;
    email: string;
    picture?: string;
}

interface AppState {
    user: User | null;
    token: string | null;
    isLoading: boolean;
    authError: string | null;
    messages: Message[];
    fetchUser: (token: string) => Promise<void>;
    login: (formData: FormData) => Promise<void>;
    logout: () => void;
    setToken: (token: string | null) => void;
    setIsLoading: (isLoading: boolean) => void;
    addMessage: (message: Message) => void;
    devLogin: () => Promise<void>;
}

const useAppStore = create<AppState>((set, get) => ({
    user: null,
    token: null,
    isLoading: true,
    authError: null,
    messages: [],
    setToken: (token) => set({ token }),
    setIsLoading: (isLoading) => set({ isLoading }),
    addMessage: (message) => set((state) => ({ messages: [...state.messages, message] })),
    fetchUser: async (token) => {
        try {
            const userData = await apiService.get(config.api.endpoints.currentUser, token);
            set({ user: userData, token, isLoading: false });
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
            set({ token: access_token });
            await get().fetchUser(access_token);
            window.location.href = '/';
        } catch (error: unknown) {
            console.error(error);
            set({ authError: error instanceof Error ? error.message : 'An unexpected error occurred during login.', isLoading: false });
        }
    },
    logout: () => {
        set({ user: null, token: null });
        if (typeof window !== 'undefined') {
            localStorage.removeItem('authToken');
        }
    },
    devLogin: async () => {
        try {
            const response = await apiService.post(config.api.endpoints.devLogin, {});
            const { access_token } = response;
            localStorage.setItem('authToken', access_token);
            set({ token: access_token });
            await get().fetchUser(access_token);
        } catch (error) {
            console.error('Failed to login as dev user', error);
        }
    },
}));


export default useAppStore;