import { create } from 'zustand';

interface AppState {
  isSidebarCollapsed: boolean;
  toggleSidebar: () => void;
  user: any;
  setUser: (user: any) => void;
  logout: () => void;
}

export const useAppStore = create<AppState>((set) => ({
  isSidebarCollapsed: false,
  toggleSidebar: () =>
    set((state) => ({ isSidebarCollapsed: !state.isSidebarCollapsed })),
  user: null,
  setUser: (user) => set({ user }),
  logout: () => set({ user: null }),
}));
