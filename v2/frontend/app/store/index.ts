import { create } from 'zustand';
import { devtools } from 'zustand/middleware';
import { User } from '@/types';
import { useWebSocketStore } from './websocket';

interface AppState {
  user: User | null;
  isLoading: boolean;
  token: string | null;
  setToken: (token: string) => void;
  clearAuth: () => void;
  fetchUser: (token: string) => Promise<void>;
  devLogin: () => Promise<void>;
  logout: () => void;
  initializeWebSocket: () => void;
}

const useAppStore = create<AppState>()(
  devtools((set) => ({
    user: null,
    isLoading: true,
    token: null,
    setToken: (token) => set({ token }),
    clearAuth: () => set({ user: null, token: null }),
    fetchUser: async (token) => {
      try {
        const response = await fetch('http://localhost:8000/api/v3/auth/users/me', {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        });
        if (response.ok) {
          const user = await response.json();
          set({ user, isLoading: false });
        } else {
          set({ user: null, isLoading: false });
        }
      } catch (error) {
        set({ user: null, isLoading: false });
      }
    },
    devLogin: async () => {
      try {
        const response = await fetch('http://localhost:8000/api/v3/auth/dev-login', {
          method: 'POST',
        });
        if (response.ok) {
          const { access_token } = await response.json();
          document.cookie = `access_token=${access_token}; path=/; samesite=lax;`;
          const userResponse = await fetch('http://localhost:8000/api/v3/auth/users/me', {
            headers: {
              Authorization: `Bearer ${access_token}`,
            },
          });
          if (userResponse.ok) {
            const user = await userResponse.json();
            set({ user, isLoading: false });
          } else {
            set({ user: null, isLoading: false });
          }
        } else {
          set({ user: null, isLoading: false });
        }
      } catch (error) {
        set({ user: null, isLoading: false });
      }
    },
    logout: () => {
      document.cookie = 'access_token=; path=/; expires=Thu, 01 Jan 1970 00:00:00 GMT';
      set({ user: null });
    },
    initializeWebSocket: () => {
      const token = document.cookie.split('; ').find(row => row.startsWith('access_token='))?.split('=')[1];
      if (token) {
        const { connect } = useWebSocketStore.getState();
        connect(token);
      }
    },
  }))
);

export default useAppStore;
