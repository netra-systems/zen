import { useState, useCallback, useEffect } from 'react';

interface ErrorState {
  message: string | null;
  code?: string;
  details?: any;
}

interface UseErrorReturn {
  error: ErrorState | null;
  setError: (error: Error | string | ErrorState | null) => void;
  clearError: () => void;
  isError: boolean;
}

export function useError(): UseErrorReturn {
  const [error, setErrorState] = useState<ErrorState | null>(null);

  const setError = useCallback((error: Error | string | ErrorState | null) => {
    if (!error || (typeof error === 'string' && error === '')) {
      setErrorState(null);
      return;
    }

    if (typeof error === 'string') {
      setErrorState({ message: error });
    } else if (error instanceof Error) {
      setErrorState({
        message: error.message,
        details: error.stack,
      });
    } else {
      setErrorState(error);
    }
  }, []);

  const clearError = useCallback(() => {
    setErrorState(null);
  }, []);

  // Auto-clear error after 10 seconds
  useEffect(() => {
    if (error) {
      const timer = setTimeout(() => {
        clearError();
      }, 10000);

      return () => clearTimeout(timer);
    }
  }, [error, clearError]);

  return {
    error,
    setError,
    clearError,
    isError: !!error,
  };
}

// Global error handler hook
export function useGlobalErrorHandler() {
  const { setError } = useError();

  useEffect(() => {
    const handleError = (event: ErrorEvent) => {
      setError({
        message: event.message,
        details: {
          filename: event.filename,
          lineno: event.lineno,
          colno: event.colno,
        },
      });
    };

    const handleUnhandledRejection = (event: PromiseRejectionEvent) => {
      setError({
        message: 'Unhandled promise rejection',
        details: event.reason,
      });
    };

    window.addEventListener('error', handleError);
    window.addEventListener('unhandledrejection', handleUnhandledRejection);

    return () => {
      window.removeEventListener('error', handleError);
      window.removeEventListener('unhandledrejection', handleUnhandledRejection);
    };
  }, [setError]);
}