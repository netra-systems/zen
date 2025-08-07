import { create } from 'zustand';
import { User } from '@/app/types/index';

interface AppState {
    user: User | null;
    setUser: (user: User | null) => void;
}

const useAppStore = create<AppState>((set) => ({
    user: null,
    setUser: (user) => set({ user }),
}));

export default useAppStore;
