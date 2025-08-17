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
        setUserLoginState(state, user, token);
        storeTokenInLocalStorage(token);
      }),

    logout: () =>
      set((state) => {
        clearUserAuthState(state);
        removeTokenFromLocalStorage();
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
        resetAuthState(state);
        removeTokenFromLocalStorage();
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

// Helper functions for auth state updates (≤8 lines each)
const setUserLoginState = (state: any, user: User, token: string): void => {
  state.isAuthenticated = true;
  state.user = user;
  state.token = token;
  state.error = null;
};

const clearUserAuthState = (state: any): void => {
  state.isAuthenticated = false;
  state.user = null;
  state.token = null;
  state.error = null;
};

const resetAuthState = (state: any): void => {
  state.isAuthenticated = false;
  state.user = null;
  state.token = null;
  state.loading = false;
  state.error = null;
};

const storeTokenInLocalStorage = (token: string): void => {
  if (typeof window !== 'undefined') {
    localStorage.setItem('jwt_token', token);
  }
};

const removeTokenFromLocalStorage = (): void => {
  if (typeof window !== 'undefined') {
    localStorage.removeItem('jwt_token');
  }
};