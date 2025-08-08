import { create } from 'zustand';
import { User } from '@/types/index';
import { devLogin as apiDevLogin, logout as apiLogout } from '@/services/authService';

interface AppState {
  user: User | null;
  isLoading: boolean;
  devLogin: () => Promise<void>;
  logout: () => Promise<void>;
  setUser: (user: User | null) => void;
}

const useAppStore = create<AppState>((set) => ({
  user: null,
  isLoading: true,
  devLogin: async () => {
    set({ isLoading: true });
    try {
      const user = await apiDevLogin();
      set({ user, isLoading: false });
    } catch (error) {
      console.error('Failed to login as dev user', error);
      set({ isLoading: false });
    }
  },
  logout: async () => {
    set({ isLoading: true });
    try {
      await apiLogout();
      set({ user: null, isLoading: false });
    } catch (error) {
      console.error('Failed to logout', error);
      set({ isLoading: false });
    }
  },
  setUser: (user) => set({ user, isLoading: false }),
}));

export default useAppStore;
