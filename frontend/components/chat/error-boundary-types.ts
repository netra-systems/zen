import { ReactNode } from 'react';

export interface ErrorBoundaryProps {
  children: ReactNode;
  fallback?: ReactNode;
  onError?: (error: Error, errorInfo: React.ErrorInfo) => void;
}

export interface ErrorBoundaryState {
  hasError: boolean;
  error: Error | null;
  errorInfo: React.ErrorInfo | null;
  errorCount: number;
  lastErrorTime: number;
}

export interface ErrorReport {
  message: string;
  stack?: string;
  componentStack: string;
  timestamp: string;
  userAgent: string;
  url: string;
  errorCount: number;
}

export interface ErrorBoundaryRetryConfig {
  maxRetries: number;
  retryDelay: number;
  useExponentialBackoff: boolean;
}

export interface TransientErrorConfig {
  errorTypes: string[];
  shouldAutoRetry: (error: Error) => boolean;
}

export interface ErrorHandlerHookReturn {
  throwError: (error: Error) => void;
  resetError: () => void;
}

export const DEFAULT_RETRY_CONFIG: ErrorBoundaryRetryConfig = {
  maxRetries: 3,
  retryDelay: 1000,
  useExponentialBackoff: true,
};

export const DEFAULT_TRANSIENT_ERRORS = [
  'ChunkLoadError',
  'NetworkError',
  'TimeoutError',
  'WebSocketError'
];