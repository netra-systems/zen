import { create } from 'zustand';
import { immer } from 'zustand/middleware/immer';
import { User } from '@/types/unified';
import { unifiedAuthService } from '@/auth/unified-auth-service';

interface ExtendedUser extends User {
  role?: 'standard_user' | 'power_user' | 'developer' | 'admin' | 'super_admin';
  permissions?: string[];
  is_developer?: boolean;
}

interface AuthState {
  isAuthenticated: boolean;
  user: ExtendedUser | null;
  token: string | null;
  loading: boolean;
  error: string | null;
  
  // Actions
  login: (user: ExtendedUser, token: string) => void;
  logout: () => void;
  setLoading: (loading: boolean) => void;
  setError: (error: string | null) => void;
  updateUser: (user: Partial<ExtendedUser>) => void;
  updateToken: (token: string) => void;
  reset: () => void;
  initializeFromStorage: () => void;
  
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
        // Use UnifiedAuthService as SSOT for token storage
        unifiedAuthService.setToken(token);
      }),

    logout: () =>
      set((state) => {
        clearUserAuthState(state);
        // Use UnifiedAuthService as SSOT for token removal
        unifiedAuthService.removeToken();
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

    updateToken: (token) =>
      set((state) => {
        state.token = token;
        // Use UnifiedAuthService as SSOT for token storage
        unifiedAuthService.setToken(token);
      }),

    reset: () =>
      set((state) => {
        resetAuthState(state);
        // Use UnifiedAuthService as SSOT for token removal
        unifiedAuthService.removeToken();
      }),

    initializeFromStorage: () =>
      set((state) => {
        initializeAuthFromStorage(state);
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
  // Store user data for persistence
  if (typeof window !== 'undefined') {
    localStorage.setItem('user_data', JSON.stringify(user));
  }
};

const clearUserAuthState = (state: any): void => {
  state.isAuthenticated = false;
  state.user = null;
  state.token = null;
  state.error = null;
  // Clear stored user data
  if (typeof window !== 'undefined') {
    localStorage.removeItem('user_data');
  }
};

const resetAuthState = (state: any): void => {
  state.isAuthenticated = false;
  state.user = null;
  state.token = null;
  state.loading = false;
  state.error = null;
};

// DEPRECATED: Token storage now handled by UnifiedAuthService (SSOT)
// Keep functions for backward compatibility but delegate to UnifiedAuthService
const storeTokenInLocalStorage = (token: string): void => {
  unifiedAuthService.setToken(token);
};

const removeTokenFromLocalStorage = (): void => {
  unifiedAuthService.removeToken();
};

const initializeAuthFromStorage = (state: any): void => {
  if (typeof window !== 'undefined') {
    // Use UnifiedAuthService as SSOT for token retrieval
    const token = unifiedAuthService.getToken();
    const userData = localStorage.getItem('user_data');
    
    if (token && userData) {
      try {
        const user = JSON.parse(userData);
        state.isAuthenticated = true;
        state.user = user;
        state.token = token;
        state.error = null;
      } catch (error) {
        // Clear corrupted data through UnifiedAuthService
        unifiedAuthService.removeToken();
        localStorage.removeItem('user_data');
        clearUserAuthState(state);
      }
    } else {
      clearUserAuthState(state);
    }
  }
};