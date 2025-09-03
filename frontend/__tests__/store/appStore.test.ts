import { create } from 'zustand';

// Simple app store for testing
interface AppState {
  count: number;
  isLoading: boolean;
  error: string | null;
  increment: () => void;
  decrement: () => void;
  setLoading: (loading: boolean) => void;
  setError: (error: string | null) => void;
  reset: () => void;
}

const useAppStore = create<AppState>((set) => ({
  count: 0,
  isLoading: false,
  error: null,
  increment: () => set((state) => ({ count: state.count + 1 })),
  decrement: () => set((state) => ({ count: state.count - 1 })),
  setLoading: (loading) => set({ isLoading: loading }),
  setError: (error) => set({ error }),
  reset: () => set({ count: 0, isLoading: false, error: null }),
}));

describe('App Store', () => {
  beforeEach(() => {
    useAppStore.getState().reset();
  });

  it('initializes with default values', () => {
    const state = useAppStore.getState();
    expect(state.count).toBe(0);
    expect(state.isLoading).toBe(false);
    expect(state.error).toBeNull();
  });

  it('increments count', () => {
    const { increment } = useAppStore.getState();
    increment();
    
    const state = useAppStore.getState();
    expect(state.count).toBe(1);
  });

  it('decrements count', () => {
    const { increment, decrement } = useAppStore.getState();
    increment();
    increment();
    decrement();
    
    const state = useAppStore.getState();
    expect(state.count).toBe(1);
  });

  it('sets loading state', () => {
    const { setLoading } = useAppStore.getState();
    setLoading(true);
    
    expect(useAppStore.getState().isLoading).toBe(true);
    
    setLoading(false);
    expect(useAppStore.getState().isLoading).toBe(false);
  });

  it('sets error state', () => {
    const { setError } = useAppStore.getState();
    setError('Something went wrong');
    
    expect(useAppStore.getState().error).toBe('Something went wrong');
    
    setError(null);
    expect(useAppStore.getState().error).toBeNull();
  });

  it('resets all state', () => {
    const { increment, setLoading, setError, reset } = useAppStore.getState();
    
    increment();
    increment();
    setLoading(true);
    setError('Error message');
    
    reset();
    
    const state = useAppStore.getState();
    expect(state.count).toBe(0);
    expect(state.isLoading).toBe(false);
    expect(state.error).toBeNull();
  });

  it('handles subscriptions', () => {
    const listener = jest.fn();
    const unsubscribe = useAppStore.subscribe(listener);
    
    useAppStore.getState().increment();
    expect(listener).toHaveBeenCalledTimes(1);
    
    unsubscribe();
    useAppStore.getState().increment();
    expect(listener).toHaveBeenCalledTimes(1);
  });
});