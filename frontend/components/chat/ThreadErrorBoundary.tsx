"use client";

import React, { Component, ErrorInfo, ReactNode } from 'react';
import { logger } from '@/lib/logger';
import { ThreadErrorFallback } from './ThreadErrorFallback';

/**
 * Thread Error Boundary Props
 */
interface ThreadErrorBoundaryProps {
  readonly children: ReactNode;
  readonly threadId?: string;
  readonly fallback?: ReactNode;
  readonly onError?: (error: Error, errorInfo: ErrorInfo, threadId?: string) => void;
  readonly onRetry?: (threadId?: string) => void;
}

/**
 * Thread Error Boundary State
 */
interface ThreadErrorBoundaryState {
  readonly hasError: boolean;
  readonly error?: Error;
  readonly errorInfo?: ErrorInfo;
  readonly retryCount: number;
}

/**
 * Thread-specific error boundary for chat operations
 */
export class ThreadErrorBoundary extends Component<
  ThreadErrorBoundaryProps,
  ThreadErrorBoundaryState
> {
  private readonly maxRetries = 3;
  
  constructor(props: ThreadErrorBoundaryProps) {
    super(props);
    this.state = createInitialState();
  }

  static getDerivedStateFromError(error: Error): Partial<ThreadErrorBoundaryState> {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo): void {
    this.logError(error, errorInfo);
    this.notifyErrorHandler(error, errorInfo);
    this.setState(prev => ({ ...prev, errorInfo }));
  }

  private logError = (error: Error, errorInfo: ErrorInfo): void => {
    logger.error('Thread operation error', {
      error: error.message,
      stack: error.stack,
      threadId: this.props.threadId,
      componentStack: errorInfo.componentStack
    });
  };

  private notifyErrorHandler = (error: Error, errorInfo: ErrorInfo): void => {
    this.props.onError?.(error, errorInfo, this.props.threadId);
  };

  private handleRetry = (): void => {
    if (this.state.retryCount < this.maxRetries) {
      this.resetErrorState();
      this.props.onRetry?.(this.props.threadId);
    }
  };

  private resetErrorState = (): void => {
    this.setState(prev => ({
      hasError: false,
      error: undefined,
      errorInfo: undefined,
      retryCount: prev.retryCount + 1
    }));
  };

  render(): ReactNode {
    if (this.state.hasError) {
      return this.renderErrorFallback();
    }

    return this.props.children;
  }

  private renderErrorFallback = (): ReactNode => {
    if (this.props.fallback) {
      return this.props.fallback;
    }

    return (
      <ThreadErrorFallback
        error={this.state.error}
        threadId={this.props.threadId}
        retryCount={this.state.retryCount}
        maxRetries={this.maxRetries}
        onRetry={this.handleRetry}
        onReset={() => this.resetErrorState()}
      />
    );
  };
}

/**
 * Creates initial error boundary state
 */
const createInitialState = (): ThreadErrorBoundaryState => ({
  hasError: false,
  retryCount: 0
});

export default ThreadErrorBoundary;