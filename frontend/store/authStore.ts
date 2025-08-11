import { create } from 'zustand';
import { immer } from 'zustand/middleware/immer';

interface User {
  id: string;
  email: string;
  name?: string;
  role?: 'standard_user' | 'power_user' | 'developer' | 'admin' | 'super_admin';
  permissions?: string[];
  is_developer?: boolean;
  is_superuser?: boolean;
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
  
  // Permission helpers
  hasPermission: (permission: string) => boolean;
  hasAnyPermission: (permissions: string[]) => boolean;
  hasAllPermissions: (permissions: string[]) => boolean;
  isAdminOrHigher: () => boolean;
  isDeveloperOrHigher: () => boolean;
}

export const useAuthStore = create<AuthState>()(
  immer((set, get) => ({
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
          localStorage.setItem('jwt_token', token);
        }
      }),

    logout: () =>
      set((state) => {
        state.isAuthenticated = false;
        state.user = null;
        state.token = null;
        state.error = null;
        // Remove token from localStorage
        if (typeof window !== 'undefined') {
          localStorage.removeItem('jwt_token');
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

    updateUser: (userUpdate) =>
      set((state) => {
        if (state.user) {
          state.user = { ...state.user, ...userUpdate };
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
          localStorage.removeItem('jwt_token');
        }
      }),

    hasPermission: (permission) => {
      const state = get();
      if (!state.user) return false;
      return state.user.permissions?.includes(permission) || false;
    },

    hasAnyPermission: (permissions) => {
      const state = get();
      if (!state.user) return false;
      return permissions.some(p => state.user?.permissions?.includes(p)) || false;
    },

    hasAllPermissions: (permissions) => {
      const state = get();
      if (!state.user) return false;
      return permissions.every(p => state.user?.permissions?.includes(p)) || false;
    },

    isAdminOrHigher: () => {
      const state = get();
      if (!state.user) return false;
      return ['admin', 'super_admin'].includes(state.user.role || '') || 
             state.user.is_superuser || false;
    },

    isDeveloperOrHigher: () => {
      const state = get();
      if (!state.user) return false;
      return ['developer', 'admin', 'super_admin'].includes(state.user.role || '') || 
             state.user.is_developer || 
             state.user.is_superuser || false;
    },
  }))
);