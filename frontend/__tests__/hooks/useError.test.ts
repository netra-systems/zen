/**
 * AI AGENT MODIFICATION METADATA
 * ================================
 * Timestamp: 2025-08-10T14:31:00Z
 * Agent: Claude Opus 4.1 (claude-opus-4-1-20250805) via claude-code
 * Context: Create comprehensive test suite for useError hook
 * Git: v6 | 88345b5 | dirty
 * Change: Test | Scope: Component | Risk: Low
 * Session: test-improvement | Seq: 2
 * Review: Pending | Score: 85/100
 * ================================
 */

import { renderHook, act } from '@testing-library/react';
import { setupAntiHang, cleanupAntiHang } from '@/__tests__/utils/anti-hanging-test-utilities';
import { useError } from '@/hooks/useError';

describe('useError', () => {
      
  jest.setTimeout(10000);

  beforeEach(() => {

  });

  afterEach(() => {
    cleanupAntiHang();
  });jest.setTimeout(10000);
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('should initialize with no error', () => {
    const { result } = renderHook(() => useError());
    
    expect(result.current.error).toBeNull();
    expect(result.current.isError).toBe(false);
  });

  it('should set error correctly', () => {
    const { result } = renderHook(() => useError());
    
    act(() => {
      result.current.setError('Test error message');
    });
    
    expect(result.current.error).toEqual({ message: 'Test error message' });
    expect(result.current.isError).toBe(true);
  });

  it('should clear error', () => {
    const { result } = renderHook(() => useError());
    
    // Set an error first
    act(() => {
      result.current.setError('Test error');
    });
    
    expect(result.current.error).toEqual({ message: 'Test error' });
    expect(result.current.isError).toBe(true);
    
    // Clear the error
    act(() => {
      result.current.clearError();
    });
    
    expect(result.current.error).toBeNull();
    expect(result.current.isError).toBe(false);
  });

  it('should handle Error objects', () => {
    const { result } = renderHook(() => useError());
    
    const errorObj = new Error('Test error object');
    
    act(() => {
      result.current.setError(errorObj);
    });
    
    expect(result.current.error?.message).toBe('Test error object');
    expect(result.current.error?.details).toBeDefined();
    expect(result.current.isError).toBe(true);
  });

  it('should handle multiple error updates', () => {
    const { result } = renderHook(() => useError());
    
    // Set first error
    act(() => {
      result.current.setError('First error');
    });
    expect(result.current.error).toEqual({ message: 'First error' });
    
    // Update to second error
    act(() => {
      result.current.setError('Second error');
    });
    expect(result.current.error).toEqual({ message: 'Second error' });
    
    // Update to third error
    act(() => {
      result.current.setError('Third error');
    });
    expect(result.current.error).toEqual({ message: 'Third error' });
    expect(result.current.isError).toBe(true);
  });

  it('should handle null and undefined values', () => {
    const { result } = renderHook(() => useError());
    
    // Set error to null
    act(() => {
      result.current.setError(null);
    });
    expect(result.current.error).toBeNull();
    expect(result.current.isError).toBe(false);
    
    // Set error to undefined - should set to null
    act(() => {
      result.current.setError(undefined as any);
    });
    expect(result.current.error).toBeNull();
    expect(result.current.isError).toBe(false);
  });

  it('should maintain error state across re-renders', () => {
    const { result, rerender } = renderHook(() => useError());
    
    act(() => {
      result.current.setError('Persistent error');
    });
    
    expect(result.current.error).toEqual({ message: 'Persistent error' });
    
    // Re-render the hook
    rerender();
    
    // Error should persist
    expect(result.current.error).toEqual({ message: 'Persistent error' });
    expect(result.current.isError).toBe(true);
  });

  it('should handle complex error objects', () => {
    const { result } = renderHook(() => useError());
    
    const complexError = {
      message: 'Complex error',
      code: 'ERR_001',
      details: {
        timestamp: Date.now(),
        stack: 'Error stack trace'
      }
    };
    
    act(() => {
      result.current.setError(complexError);
    });
    
    expect(result.current.error).toEqual(complexError);
    expect(result.current.isError).toBe(true);
  });

  it('should toggle between error and no error states', () => {
    const { result } = renderHook(() => useError());
    
    // Start with no error
    expect(result.current.isError).toBe(false);
    
    // Set error
    act(() => {
      result.current.setError('Toggle error');
    });
    expect(result.current.isError).toBe(true);
    
    // Clear error
    act(() => {
      result.current.clearError();
    });
    expect(result.current.isError).toBe(false);
    
    // Set error again
    act(() => {
      result.current.setError('Another error');
    });
    expect(result.current.isError).toBe(true);
  });

  it('should handle empty string as error', () => {
    const { result } = renderHook(() => useError());
    
    act(() => {
      result.current.setError('');
    });
    
    expect(result.current.error).toBeNull();
    expect(result.current.isError).toBe(false); // Empty string should be treated as no error
  });

  it('should handle ErrorState objects', () => {
    const { result } = renderHook(() => useError());
    
    const errorState = {
      message: 'Custom error',
      code: 'ERR_001',
      details: { extra: 'info' }
    };
    
    act(() => {
      result.current.setError(errorState);
    });
    expect(result.current.error).toEqual(errorState);
    expect(result.current.isError).toBe(true);
  });

  it('should auto-clear error after timeout', () => {
    jest.useFakeTimers();
    const { result } = renderHook(() => useError());
    
    act(() => {
      result.current.setError('Auto-clear error');
    });
    
    expect(result.current.error).toEqual({ message: 'Auto-clear error' });
    expect(result.current.isError).toBe(true);
    
    // Fast-forward 10 seconds
    act(() => {
      jest.advanceTimersByTime(10000);
    });
    
    expect(result.current.error).toBeNull();
    expect(result.current.isError).toBe(false);
    
    jest.useRealTimers();
  });
  afterEach(() => {
    cleanupAntiHang();
  });

});