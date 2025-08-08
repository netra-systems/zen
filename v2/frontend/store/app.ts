import { create } from 'zustand';

interface AppState {
  isSidebarCollapsed: boolean;
  toggleSidebar: () => void;
}

export const useAppStore = create<AppState>((set) => ({
  isSidebarCollapsed: false,
  toggleSidebar: () =>
    set((state) => ({ isSidebarCollapsed: !state.isSidebarCollapsed })),
}));