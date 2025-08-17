import React, { Component } from 'react';
import type { 
  ErrorBoundaryProps, 
  ErrorBoundaryState 
} from './error-boundary-types';
import { RetryManager } from './retry-manager';
import { ErrorReporter } from './error-reporter';
import { 
  ErrorContainer,
  ErrorHeader,
  ErrorDetails,
  ActionButtons,
  AutoRetryIndicator
} from './error-boundary-ui';

export class ChatErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  private retryManager: RetryManager;
  private readonly MAX_RETRIES = 3;

  constructor(props: ErrorBoundaryProps) {
    super(props);
    this.state = {
      hasError: false,
      error: null,
      errorInfo: null,
      errorCount: 0,
      lastErrorTime: 0
    };
    this.retryManager = new RetryManager();
  }

  static getDerivedStateFromError(error: Error): Partial<ErrorBoundaryState> {
    return {
      hasError: true,
      error,
      lastErrorTime: Date.now()
    };
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    this.updateErrorState(errorInfo);
    this.callErrorHandler(error, errorInfo);
    this.reportError(error, errorInfo);
    this.handleAutoRetry(error);
  }

  componentWillUnmount() {
    this.retryManager.clearAllRetries();
  }

  private updateErrorState(errorInfo: React.ErrorInfo): void {
    this.setState(prevState => ({
      errorInfo,
      errorCount: prevState.errorCount + 1
    }));
  }

  private callErrorHandler(error: Error, errorInfo: React.ErrorInfo): void {
    const { onError } = this.props;
    if (onError) {
      onError(error, errorInfo);
    }
  }

  private reportError(error: Error, errorInfo: React.ErrorInfo): void {
    ErrorReporter.reportError(error, errorInfo, this.state.errorCount);
  }

  private handleAutoRetry(error: Error): void {
    const { errorCount } = this.state;
    if (this.retryManager.shouldRetry(error, errorCount)) {
      this.retryManager.scheduleRetry(this.handleReset, errorCount);
    }
  }

  private handleReset = (): void => {
    this.setState({
      hasError: false,
      error: null,
      errorInfo: null,
      errorCount: 0
    });
  };

  private handleReload = (): void => {
    window.location.reload();
  };

  private handleGoHome = (): void => {
    window.location.href = '/';
  }

  private downloadErrorReport = (): void => {
    const { error, errorInfo } = this.state;
    if (error) {
      this.createAndDownloadReport(error, errorInfo);
    }
  };

  private createAndDownloadReport(error: Error, errorInfo: React.ErrorInfo | null): void {
    const report = this.buildErrorReport(error, errorInfo);
    this.downloadReport(report);
  }

  private buildErrorReport(error: Error, errorInfo: React.ErrorInfo | null) {
    return {
      error: { message: error.message, stack: error.stack },
      errorInfo: errorInfo?.componentStack,
      timestamp: new Date().toISOString(),
      localStorage: { ...localStorage },
      sessionStorage: { ...sessionStorage }
    };
  }

  private downloadReport(report: object): void {
    const blob = new Blob([JSON.stringify(report, null, 2)], {
      type: 'application/json'
    });
    this.downloadBlob(blob, `error-report-${Date.now()}.json`);
  }

  private downloadBlob(blob: Blob, filename: string): void {
    const url = URL.createObjectURL(blob);
    this.triggerDownload(url, filename);
    URL.revokeObjectURL(url);
  }

  private triggerDownload(url: string, filename: string): void {
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
  }

  render() {
    return this.renderErrorBoundary();
  }

  private renderErrorBoundary() {
    const { hasError, error, errorCount } = this.state;
    const { children, fallback } = this.props;

    if (hasError && error) {
      return this.renderErrorUI(error, errorCount, fallback);
    }
    return children;
  }

  private renderErrorUI(error: Error, errorCount: number, fallback?: React.ReactNode) {
    if (fallback) {
      return <>{fallback}</>;
    }
    return this.renderFullErrorDisplay(error, errorCount);
  }

  private renderFullErrorDisplay(error: Error, errorCount: number) {
    const shouldShowRetry = this.retryManager.shouldRetry(error, errorCount);
    
    return (
      <ErrorContainer>
        {this.renderErrorContent(error, errorCount)}
        <AutoRetryIndicator shouldShow={shouldShowRetry} />
      </ErrorContainer>
    );
  }

  private renderErrorContent(error: Error, errorCount: number) {
    return (
      <>
        <ErrorHeader errorCount={errorCount} maxRetries={this.MAX_RETRIES} />
        <ErrorDetails error={error} />
        {this.renderActionButtons()}
      </>
    );
  }

  private renderActionButtons() {
    return (
      <ActionButtons
        onReset={this.handleReset}
        onReload={this.handleReload}
        onGoHome={this.handleGoHome}
        onDownloadReport={this.downloadErrorReport}
      />
    );
  }
}

// Re-export hooks for backwards compatibility
export { useErrorHandler } from './error-boundary-hooks';