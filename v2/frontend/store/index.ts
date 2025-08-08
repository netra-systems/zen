import { create } from 'zustand';
import { User } from '@/types';

interface AppState {
  isSidebarCollapsed: boolean;
  toggleSidebar: () => void;
  user: User | null;
  logout: () => void;
  login: (user: User) => void;
}

const useAppStore = create<AppState>((set) => ({
  isSidebarCollapsed: false,
  toggleSidebar: () => set((state) => ({ isSidebarCollapsed: !state.isSidebarCollapsed })),
  user: null,
  logout: () => set({ user: null }),
  login: (user) => set({ user }),
}));

export default useAppStore;