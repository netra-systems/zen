/**
 * UVS Error Boundary - Loud error handling with fallback UI
 * 
 * CRITICAL: Implements loud error handling per CLAUDE.md requirements
 * "Make all errors loud. Protect against silent errors."
 * 
 * Business Value: Never lose user engagement due to errors
 */

import React, { Component, ReactNode, ErrorInfo } from 'react';
import { logger } from '@/lib/logger';
import { Button } from '@/components/ui/button';
import { AlertTriangle, RefreshCw, Home } from 'lucide-react';

interface Props {
  children: ReactNode;
  userId?: string;
  fallbackComponent?: React.ComponentType<FallbackProps>;
}

interface State {
  hasError: boolean;
  error: Error | null;
  errorInfo: ErrorInfo | null;
  errorType: ErrorType;
  fallbackAction: FallbackAction;
  errorCount: number;
  lastErrorTime: number;
}

interface FallbackProps {
  error: Error | null;
  errorType: ErrorType;
  onRetry: () => void;
  onReset: () => void;
  onGoHome: () => void;
}

enum ErrorType {
  NETWORK = 'NETWORK',
  WEBSOCKET = 'WEBSOCKET',
  VALIDATION = 'VALIDATION',
  RENDERING = 'RENDERING',
  UNKNOWN = 'UNKNOWN'
}

enum FallbackAction {
  RETRY = 'RETRY',
  RESET = 'RESET',
  RELOAD = 'RELOAD',
  GO_HOME = 'GO_HOME'
}

/**
 * Default fallback UI component
 */
const DefaultFallbackUI: React.FC<FallbackProps> = ({ 
  error, 
  errorType, 
  onRetry, 
  onReset, 
  onGoHome 
}) => (
  <div className="flex flex-col items-center justify-center min-h-[400px] p-8 bg-red-50 dark:bg-red-900/10 rounded-lg border-2 border-red-200 dark:border-red-800">
    <div className="max-w-md w-full space-y-6">
      {/* Error Icon */}
      <div className="flex justify-center">
        <div className="p-4 bg-red-100 dark:bg-red-900/20 rounded-full">
          <AlertTriangle className="w-12 h-12 text-red-600 dark:text-red-400" />
        </div>
      </div>
      
      {/* Error Message */}
      <div className="text-center space-y-2">
        <h2 className="text-xl font-semibold text-red-900 dark:text-red-100">
          Something went wrong
        </h2>
        <p className="text-sm text-red-700 dark:text-red-300">
          {getErrorMessage(errorType)}
        </p>
        {error && (
          <details className="mt-4 text-left">
            <summary className="cursor-pointer text-sm text-red-600 dark:text-red-400 hover:underline">
              Show technical details
            </summary>
            <pre className="mt-2 p-3 bg-red-100 dark:bg-red-900/20 rounded text-xs text-red-800 dark:text-red-200 overflow-auto">
              {error.stack || error.message}
            </pre>
          </details>
        )}
      </div>
      
      {/* Action Buttons */}
      <div className="flex flex-col gap-3">
        <Button 
          onClick={onRetry}
          className="w-full"
          variant="default"
        >
          <RefreshCw className="w-4 h-4 mr-2" />
          Try Again
        </Button>
        
        <Button 
          onClick={onReset}
          className="w-full"
          variant="outline"
        >
          Reset Conversation
        </Button>
        
        <Button 
          onClick={onGoHome}
          className="w-full"
          variant="ghost"
        >
          <Home className="w-4 h-4 mr-2" />
          Go to Home
        </Button>
      </div>
      
      {/* Help Text */}
      <div className="text-center text-sm text-gray-600 dark:text-gray-400">
        <p>If this problem persists, please contact support.</p>
        <p className="mt-1">Error ID: {generateErrorId()}</p>
      </div>
    </div>
  </div>
);

/**
 * Get user-friendly error message based on type
 */
function getErrorMessage(errorType: ErrorType): string {
  switch (errorType) {
    case ErrorType.NETWORK:
      return 'Unable to connect to the server. Please check your internet connection.';
    case ErrorType.WEBSOCKET:
      return 'Real-time connection lost. We\'re trying to reconnect...';
    case ErrorType.VALIDATION:
      return 'The data received was invalid. Please refresh and try again.';
    case ErrorType.RENDERING:
      return 'Unable to display this content. Please try refreshing the page.';
    default:
      return 'An unexpected error occurred. We\'re working to fix it.';
  }
}

/**
 * Generate unique error ID for tracking
 */
function generateErrorId(): string {
  return `ERR-${Date.now()}-${Math.random().toString(36).substr(2, 9).toUpperCase()}`;
}

/**
 * UVS Error Boundary Component
 */
export class UVSErrorBoundary extends Component<Props, State> {
  private errorReportingEndpoint = '/api/errors';
  private maxErrorsPerMinute = 5;
  private errorTimestamps: number[] = [];
  
  constructor(props: Props) {
    super(props);
    
    this.state = {
      hasError: false,
      error: null,
      errorInfo: null,
      errorType: ErrorType.UNKNOWN,
      fallbackAction: FallbackAction.RETRY,
      errorCount: 0,
      lastErrorTime: 0
    };
  }
  
  static getDerivedStateFromError(error: Error): Partial<State> {
    // Update state so the next render will show the fallback UI
    return { hasError: true, error };
  }
  
  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    // LOUD error logging as required by CLAUDE.md
    console.error('🚨 UVS ERROR BOUNDARY TRIGGERED 🚨');
    console.error('Error:', error);
    console.error('Component Stack:', errorInfo.componentStack);
    console.error('Error ID:', generateErrorId());
    
    // Log to our logger
    logger.error('🚨 UVS Error Boundary caught error', {
      error: error.message,
      stack: error.stack,
      componentStack: errorInfo.componentStack,
      userId: this.props.userId
    });
    
    // Categorize error
    const errorType = this.categorizeError(error);
    const fallbackAction = this.determineFallback(error, errorType);
    
    // Update state
    this.setState({
      hasError: true,
      error,
      errorInfo,
      errorType,
      fallbackAction,
      errorCount: this.state.errorCount + 1,
      lastErrorTime: Date.now()
    });
    
    // Send to monitoring
    this.sendToMonitoring({
      error: error.message,
      stack: error.stack,
      componentStack: errorInfo.componentStack,
      errorType,
      userId: this.props.userId,
      timestamp: Date.now(),
      errorId: generateErrorId()
    });
    
    // Check for error storm
    this.checkErrorStorm();
  }
  
  /**
   * Categorize error type
   */
  private categorizeError(error: Error): ErrorType {
    const message = error.message.toLowerCase();
    
    if (message.includes('network') || message.includes('fetch')) {
      return ErrorType.NETWORK;
    }
    
    if (message.includes('websocket') || message.includes('connection')) {
      return ErrorType.WEBSOCKET;
    }
    
    if (message.includes('validation') || message.includes('invalid')) {
      return ErrorType.VALIDATION;
    }
    
    if (message.includes('render') || message.includes('component')) {
      return ErrorType.RENDERING;
    }
    
    return ErrorType.UNKNOWN;
  }
  
  /**
   * Determine best fallback action
   */
  private determineFallback(error: Error, errorType: ErrorType): FallbackAction {
    // Network errors - retry
    if (errorType === ErrorType.NETWORK || errorType === ErrorType.WEBSOCKET) {
      return FallbackAction.RETRY;
    }
    
    // Validation errors - reset
    if (errorType === ErrorType.VALIDATION) {
      return FallbackAction.RESET;
    }
    
    // Rendering errors - reload
    if (errorType === ErrorType.RENDERING) {
      return FallbackAction.RELOAD;
    }
    
    // Default - retry
    return FallbackAction.RETRY;
  }
  
  /**
   * Send error to monitoring service
   */
  private async sendToMonitoring(errorData: any) {
    try {
      // In production, send to actual monitoring service
      if (process.env.NODE_ENV === 'production') {
        await fetch(this.errorReportingEndpoint, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify(errorData)
        });
      }
    } catch (e) {
      // Don't throw if monitoring fails
      console.error('Failed to send error to monitoring:', e);
    }
  }
  
  /**
   * Check for error storm (too many errors)
   */
  private checkErrorStorm() {
    const now = Date.now();
    const oneMinuteAgo = now - 60000;
    
    // Clean old timestamps
    this.errorTimestamps = this.errorTimestamps.filter(t => t > oneMinuteAgo);
    
    // Add current timestamp
    this.errorTimestamps.push(now);
    
    // Check if we're in an error storm
    if (this.errorTimestamps.length >= this.maxErrorsPerMinute) {
      console.error('🚨🚨🚨 ERROR STORM DETECTED 🚨🚨🚨');
      logger.error('ERROR STORM: Too many errors in short period', {
        errorCount: this.errorTimestamps.length,
        userId: this.props.userId
      });
      
      // Force reload after error storm
      setTimeout(() => {
        if (typeof window !== 'undefined') {
          window.location.reload();
        }
      }, 2000);
    }
  }
  
  /**
   * Handle retry action
   */
  private handleRetry = () => {
    logger.info('Error boundary retry attempted');
    this.setState({
      hasError: false,
      error: null,
      errorInfo: null,
      errorType: ErrorType.UNKNOWN,
      fallbackAction: FallbackAction.RETRY
    });
  }
  
  /**
   * Handle reset action
   */
  private handleReset = () => {
    logger.info('Error boundary reset initiated');
    
    // Clear local storage
    if (typeof window !== 'undefined' && window.localStorage) {
      const keysToRemove = Object.keys(localStorage).filter(key => 
        key.startsWith('netra_uvs_')
      );
      keysToRemove.forEach(key => localStorage.removeItem(key));
    }
    
    // Reset state
    this.setState({
      hasError: false,
      error: null,
      errorInfo: null,
      errorType: ErrorType.UNKNOWN,
      fallbackAction: FallbackAction.RESET,
      errorCount: 0
    });
  }
  
  /**
   * Handle go home action
   */
  private handleGoHome = () => {
    logger.info('Error boundary go home initiated');
    if (typeof window !== 'undefined') {
      window.location.href = '/';
    }
  }
  
  render() {
    if (this.state.hasError) {
      // Use custom fallback component if provided
      const FallbackComponent = this.props.fallbackComponent || DefaultFallbackUI;
      
      return (
        <FallbackComponent
          error={this.state.error}
          errorType={this.state.errorType}
          onRetry={this.handleRetry}
          onReset={this.handleReset}
          onGoHome={this.handleGoHome}
        />
      );
    }
    
    return this.props.children;
  }
}

// Export convenience hook for error handling
export function useErrorHandler() {
  return (error: Error, errorInfo?: ErrorInfo) => {
    console.error('🚨 Error caught by useErrorHandler:', error);
    if (errorInfo) {
      console.error('Error info:', errorInfo);
    }
    
    logger.error('Error handled', {
      error: error.message,
      stack: error.stack,
      errorInfo
    });
    
    // In production, could trigger error boundary programmatically
    throw error;
  };
}