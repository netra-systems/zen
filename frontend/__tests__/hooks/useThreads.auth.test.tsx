import { renderHook, waitFor } from '@testing-library/react';
import { useThreads } from '@/hooks/useThreads';
import { ThreadService } from '@/services/threadService';
import { useAuthStore } from '@/store/authStore';

jest.mock('@/services/threadService');
jest.mock('@/store/authStore');

describe('useThreads Authentication Tests', () => {
  const mockThreadService = ThreadService as jest.Mocked<typeof ThreadService>;
  const mockUseAuthStore = useAuthStore as unknown as jest.Mock;

  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('should not fetch threads when not authenticated', async () => {
    mockUseAuthStore.mockReturnValue({
      isAuthenticated: false
    });

    mockThreadService.listThreads = jest.fn();

    const { result } = renderHook(() => useThreads());

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    expect(mockThreadService.listThreads).not.toHaveBeenCalled();
    expect(result.current.threads).toEqual([]);
  });

  it('should fetch threads when authenticated', async () => {
    const mockThreads = [
      { id: '1', title: 'Thread 1', created_at: Date.now() },
      { id: '2', title: 'Thread 2', created_at: Date.now() }
    ];

    mockUseAuthStore.mockReturnValue({
      isAuthenticated: true
    });

    mockThreadService.listThreads = jest.fn().mockResolvedValue(mockThreads);

    const { result } = renderHook(() => useThreads());

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    expect(mockThreadService.listThreads).toHaveBeenCalledTimes(1);
    expect(result.current.threads).toEqual(mockThreads);
  });

  it('should clear threads when authentication changes to false', async () => {
    const mockThreads = [
      { id: '1', title: 'Thread 1', created_at: Date.now() }
    ];

    // Start authenticated
    mockUseAuthStore.mockReturnValue({
      isAuthenticated: true
    });

    mockThreadService.listThreads = jest.fn().mockResolvedValue(mockThreads);

    const { result, rerender } = renderHook(() => useThreads());

    await waitFor(() => {
      expect(result.current.threads).toEqual(mockThreads);
    });

    // Change to unauthenticated
    mockUseAuthStore.mockReturnValue({
      isAuthenticated: false
    });

    rerender();

    await waitFor(() => {
      expect(result.current.threads).toEqual([]);
    });
  });

  it('should not call API in fetchThreads when not authenticated', async () => {
    mockUseAuthStore.mockReturnValue({
      isAuthenticated: false
    });

    mockThreadService.listThreads = jest.fn();

    const { result } = renderHook(() => useThreads());

    await result.current.fetchThreads();

    expect(mockThreadService.listThreads).not.toHaveBeenCalled();
    expect(result.current.threads).toEqual([]);
  });
});