import { renderHook, waitFor } from '@testing-library/react';
import { ThreadService } from '@/services/threadService';
import { useAuthStore } from '@/store/authStore';
import { setupAntiHang, cleanupAntiHang } from '@/__tests__/utils/anti-hanging-test-utilities';

// Import the actual useThreads to test (not the mocked version)
import { useThreads as actualUseThreads } from '@/hooks/useThreads';

// Unmock the useThreads hook for this test
jest.unmock('@/hooks/useThreads');

describe('useThreads Authentication Tests', () => {
  jest.setTimeout(10000);
  const mockUseAuthStore = useAuthStore as unknown as jest.Mock;

  beforeEach(() => {
    jest.clearAllMocks();
    // Reset the ThreadService mock
    (ThreadService.listThreads as jest.Mock).mockReset();
  });

  it('should not fetch threads when not authenticated', async () => {
    // Set the auth store state
    useAuthStore.setState({ isAuthenticated: false });
    mockUseAuthStore.mockReturnValue({
      isAuthenticated: false
    });

    const { result } = renderHook(() => actualUseThreads());

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    expect(ThreadService.listThreads).not.toHaveBeenCalled();
    expect(result.current.threads).toEqual([]);
  });

  it('should fetch threads when authenticated', async () => {
    const mockThreads = [
      { id: '1', title: 'Thread 1', created_at: Date.now() },
      { id: '2', title: 'Thread 2', created_at: Date.now() }
    ];

    (ThreadService.listThreads as jest.Mock).mockResolvedValue(mockThreads);

    // Mock the useAuthStore hook directly to always return authenticated
    mockUseAuthStore.mockImplementation(() => ({
      isAuthenticated: true,
      user: { id: 'test-user' },
      token: 'test-token'
    }));

    const { result } = renderHook(() => actualUseThreads());

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    expect(ThreadService.listThreads).toHaveBeenCalledTimes(1);
    expect(result.current.threads).toEqual(mockThreads);
  });

  it('should clear threads when authentication changes to false', async () => {
    const mockThreads = [
      { id: '1', title: 'Thread 1', created_at: Date.now() }
    ];

    // Start authenticated
    useAuthStore.setState({ isAuthenticated: true });
    mockUseAuthStore.mockReturnValue({
      isAuthenticated: true
    });

    (ThreadService.listThreads as jest.Mock).mockResolvedValue(mockThreads);

    const { result, rerender } = renderHook(() => actualUseThreads());

    await waitFor(() => {
      expect(result.current.threads).toEqual(mockThreads);
    });

    // Change to unauthenticated
    useAuthStore.setState({ isAuthenticated: false });
    mockUseAuthStore.mockReturnValue({
      isAuthenticated: false
    });

    rerender();

    await waitFor(() => {
      expect(result.current.threads).toEqual([]);
    });
  });

  it('should not call API in fetchThreads when not authenticated', async () => {
    useAuthStore.setState({ isAuthenticated: false });
    mockUseAuthStore.mockReturnValue({
      isAuthenticated: false
    });

    const { result } = renderHook(() => actualUseThreads());

    await result.current.fetchThreads();

    expect(ThreadService.listThreads).not.toHaveBeenCalled();
    expect(result.current.threads).toEqual([]);
  });
});