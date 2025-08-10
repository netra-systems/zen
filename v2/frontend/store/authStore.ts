import { create } from 'zustand';
import { immer } from 'zustand/middleware/immer';

interface User {
  id: string;
  email: string;
  name?: string;
  role?: string;
}

interface AuthState {
  isAuthenticated: boolean;
  user: User | null;
  token: string | null;
  loading: boolean;
  error: string | null;
  
  // Actions
  login: (user: User, token: string) => void;
  logout: () => void;
  setLoading: (loading: boolean) => void;
  setError: (error: string | null) => void;
  updateUser: (user: Partial<User>) => void;
  reset: () => void;
}

export const useAuthStore = create<AuthState>()(
  immer((set) => ({
    isAuthenticated: false,
    user: null,
    token: null,
    loading: false,
    error: null,

    login: (user, token) =>
      set((state) => {
        state.isAuthenticated = true;
        state.user = user;
        state.token = token;
        state.error = null;
        // Store token in localStorage
        if (typeof window !== 'undefined') {
          localStorage.setItem('auth_token', token);
        }
      }),

    logout: () =>
      set((state) => {
        state.isAuthenticated = false;
        state.user = null;
        state.token = null;
        state.error = null;
        // Clear token from localStorage
        if (typeof window !== 'undefined') {
          localStorage.removeItem('auth_token');
        }
      }),

    setLoading: (loading) =>
      set((state) => {
        state.loading = loading;
      }),

    setError: (error) =>
      set((state) => {
        state.error = error;
      }),

    updateUser: (userData) =>
      set((state) => {
        if (state.user) {
          state.user = { ...state.user, ...userData };
        }
      }),

    reset: () =>
      set((state) => {
        state.isAuthenticated = false;
        state.user = null;
        state.token = null;
        state.loading = false;
        state.error = null;
        if (typeof window !== 'undefined') {
          localStorage.removeItem('auth_token');
        }
      }),
  }))
);