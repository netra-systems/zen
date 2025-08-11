import React, { Component, ReactNode } from 'react';
import { AlertCircle, RefreshCcw, Home, Bug } from 'lucide-react';
import { motion } from 'framer-motion';

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
  onError?: (error: Error, errorInfo: React.ErrorInfo) => void;
}

interface State {
  hasError: boolean;
  error: Error | null;
  errorInfo: React.ErrorInfo | null;
  errorCount: number;
  lastErrorTime: number;
}

export class ChatErrorBoundary extends Component<Props, State> {
  private retryTimeouts: Set<NodeJS.Timeout> = new Set();
  private readonly MAX_RETRIES = 3;
  private readonly RETRY_DELAY = 1000;

  constructor(props: Props) {
    super(props);
    this.state = {
      hasError: false,
      error: null,
      errorInfo: null,
      errorCount: 0,
      lastErrorTime: 0
    };
  }

  static getDerivedStateFromError(error: Error): Partial<State> {
    return {
      hasError: true,
      error,
      lastErrorTime: Date.now()
    };
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    const { onError } = this.props;
    const { errorCount } = this.state;

    // Update error count
    this.setState(prevState => ({
      errorInfo,
      errorCount: prevState.errorCount + 1
    }));

    // Log to console in development
    if (process.env.NODE_ENV === 'development') {
      console.error('Chat Error Boundary caught:', error, errorInfo);
    }

    // Call error handler if provided
    if (onError) {
      onError(error, errorInfo);
    }

    // Send error to monitoring service
    this.reportError(error, errorInfo);

    // Auto-retry for transient errors
    if (this.shouldAutoRetry(error) && errorCount < this.MAX_RETRIES) {
      this.scheduleRetry();
    }
  }

  componentWillUnmount() {
    // Clear any pending retries
    this.retryTimeouts.forEach(timeout => clearTimeout(timeout));
    this.retryTimeouts.clear();
  }

  private shouldAutoRetry(error: Error): boolean {
    // Identify transient errors that might resolve with a retry
    const transientErrors = [
      'ChunkLoadError',
      'NetworkError',
      'TimeoutError',
      'WebSocketError'
    ];

    return transientErrors.some(errorType => 
      error.name.includes(errorType) || 
      error.message.includes(errorType)
    );
  }

  private scheduleRetry() {
    const timeout = setTimeout(() => {
      this.handleReset();
      this.retryTimeouts.delete(timeout);
    }, this.RETRY_DELAY * Math.pow(2, this.state.errorCount)); // Exponential backoff

    this.retryTimeouts.add(timeout);
  }

  private reportError(error: Error, errorInfo: React.ErrorInfo) {
    // Send to error tracking service
    const errorReport = {
      message: error.message,
      stack: error.stack,
      componentStack: errorInfo.componentStack,
      timestamp: new Date().toISOString(),
      userAgent: navigator.userAgent,
      url: window.location.href,
      errorCount: this.state.errorCount
    };

    // In production, send to monitoring service
    if (process.env.NODE_ENV === 'production') {
      // Example: send to Sentry, LogRocket, etc.
      console.error('Error Report:', errorReport);
    }

    // Store in localStorage for debugging
    const errors = JSON.parse(localStorage.getItem('chat_errors') || '[]');
    errors.push(errorReport);
    if (errors.length > 10) errors.shift(); // Keep only last 10 errors
    localStorage.setItem('chat_errors', JSON.stringify(errors));
  }

  private handleReset = () => {
    this.setState({
      hasError: false,
      error: null,
      errorInfo: null,
      errorCount: 0
    });
  };

  private handleReload = () => {
    window.location.reload();
  };

  private handleGoHome = () => {
    window.location.href = '/';
  };

  private downloadErrorReport = () => {
    const { error, errorInfo } = this.state;
    const report = {
      error: {
        message: error?.message,
        stack: error?.stack
      },
      errorInfo: errorInfo?.componentStack,
      timestamp: new Date().toISOString(),
      localStorage: { ...localStorage },
      sessionStorage: { ...sessionStorage }
    };

    const blob = new Blob([JSON.stringify(report, null, 2)], {
      type: 'application/json'
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `error-report-${Date.now()}.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  render() {
    const { hasError, error, errorCount } = this.state;
    const { children, fallback } = this.props;

    if (hasError && error) {
      if (fallback) {
        return <>{fallback}</>;
      }

      return (
        <div className="min-h-screen flex items-center justify-center bg-gray-50 p-4">
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: 0.3 }}
            className="max-w-2xl w-full"
          >
            <div className="bg-white/95 backdrop-blur-lg rounded-2xl shadow-xl border border-red-100 overflow-hidden">
              {/* Header */}
              <div className="bg-gradient-to-r from-red-50 to-orange-50 p-6 border-b border-red-100">
                <div className="flex items-center space-x-3">
                  <div className="p-3 bg-red-100 rounded-full">
                    <AlertCircle className="w-6 h-6 text-red-600" />
                  </div>
                  <div>
                    <h1 className="text-xl font-bold text-gray-900">
                      Oops! Something went wrong
                    </h1>
                    <p className="text-sm text-gray-600 mt-1">
                      {errorCount > 1 && `Retry attempt ${errorCount} of ${this.MAX_RETRIES} • `}
                      The application encountered an unexpected error
                    </p>
                  </div>
                </div>
              </div>

              {/* Error Details */}
              <div className="p-6 space-y-4">
                <div className="bg-red-50 rounded-lg p-4 border border-red-200">
                  <h2 className="text-sm font-semibold text-red-900 mb-2">
                    Error Message
                  </h2>
                  <p className="text-sm text-red-800 font-mono">
                    {error.message}
                  </p>
                </div>

                {process.env.NODE_ENV === 'development' && (
                  <details className="bg-gray-50 rounded-lg p-4 border border-gray-200">
                    <summary className="cursor-pointer text-sm font-semibold text-gray-700 hover:text-gray-900">
                      Technical Details (Development Only)
                    </summary>
                    <pre className="mt-3 text-xs text-gray-600 overflow-auto max-h-48">
                      {error.stack}
                    </pre>
                  </details>
                )}

                {/* Actions */}
                <div className="flex flex-wrap gap-3 pt-2">
                  <button
                    onClick={this.handleReset}
                    className="flex items-center space-x-2 px-4 py-2 bg-emerald-500 hover:bg-emerald-600 text-white rounded-lg transition-colors"
                  >
                    <RefreshCcw className="w-4 h-4" />
                    <span>Try Again</span>
                  </button>

                  <button
                    onClick={this.handleReload}
                    className="flex items-center space-x-2 px-4 py-2 bg-gray-600 hover:bg-gray-700 text-white rounded-lg transition-colors"
                  >
                    <RefreshCcw className="w-4 h-4" />
                    <span>Reload Page</span>
                  </button>

                  <button
                    onClick={this.handleGoHome}
                    className="flex items-center space-x-2 px-4 py-2 bg-gray-200 hover:bg-gray-300 text-gray-700 rounded-lg transition-colors"
                  >
                    <Home className="w-4 h-4" />
                    <span>Go Home</span>
                  </button>

                  <button
                    onClick={this.downloadErrorReport}
                    className="flex items-center space-x-2 px-4 py-2 border border-gray-300 hover:bg-gray-50 text-gray-700 rounded-lg transition-colors"
                  >
                    <Bug className="w-4 h-4" />
                    <span>Download Report</span>
                  </button>
                </div>

                {/* Auto-retry indicator */}
                {this.shouldAutoRetry(error) && errorCount < this.MAX_RETRIES && (
                  <motion.div
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    className="flex items-center space-x-2 text-sm text-amber-600 bg-amber-50 rounded-lg p-3"
                  >
                    <motion.div
                      animate={{ rotate: 360 }}
                      transition={{ duration: 2, repeat: Infinity, ease: "linear" }}
                    >
                      <RefreshCcw className="w-4 h-4" />
                    </motion.div>
                    <span>Automatically retrying...</span>
                  </motion.div>
                )}
              </div>
            </div>
          </motion.div>
        </div>
      );
    }

    return children;
  }
}

// Wrapper hook for functional components
export const useErrorHandler = () => {
  const [error, setError] = React.useState<Error | null>(null);

  React.useEffect(() => {
    if (error) {
      throw error;
    }
  }, [error]);

  const resetError = () => setError(null);
  const throwError = (error: Error) => setError(error);

  return { throwError, resetError };
};