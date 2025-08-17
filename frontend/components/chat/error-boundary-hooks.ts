import React from 'react';
import type { ErrorHandlerHookReturn } from './error-boundary-types';

export const useErrorHandler = (): ErrorHandlerHookReturn => {
  const [error, setError] = React.useState<Error | null>(null);

  React.useEffect(() => {
    if (error) {
      throw error;
    }
  }, [error]);

  const resetError = (): void => {
    setError(null);
  };

  const throwError = (error: Error): void => {
    setError(error);
  };

  return { throwError, resetError };
};

export const useErrorReporting = () => {
  const reportError = React.useCallback((
    error: Error,
    context: string = 'unknown'
  ) => {
    console.error(`Error in ${context}:`, error);
  }, []);

  return { reportError };
};

export const useDownloadErrorReport = () => {
  const downloadReport = React.useCallback((
    error: Error,
    errorInfo?: React.ErrorInfo
  ) => {
    const report = createErrorReport(error, errorInfo);
    downloadJsonReport(report);
  }, []);

  return { downloadReport };
};

const createErrorReport = (
  error: Error,
  errorInfo?: React.ErrorInfo
) => ({
  error: {
    message: error?.message,
    stack: error?.stack
  },
  errorInfo: errorInfo?.componentStack,
  timestamp: new Date().toISOString(),
  localStorage: { ...localStorage },
  sessionStorage: { ...sessionStorage }
});

const downloadJsonReport = (report: object): void => {
  const blob = createJsonBlob(report);
  const url = URL.createObjectURL(blob);
  downloadBlobAsFile(url, `error-report-${Date.now()}.json`);
  URL.revokeObjectURL(url);
};

const createJsonBlob = (data: object): Blob => {
  return new Blob([JSON.stringify(data, null, 2)], {
    type: 'application/json'
  });
};

const downloadBlobAsFile = (url: string, filename: string): void => {
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
};