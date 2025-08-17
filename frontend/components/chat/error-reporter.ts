import type { ErrorReport } from './error-boundary-types';

export class ErrorReporter {
  private static readonly MAX_STORED_ERRORS = 10;
  private static readonly STORAGE_KEY = 'chat_errors';

  static createReport(
    error: Error,
    errorInfo: React.ErrorInfo,
    errorCount: number
  ): ErrorReport {
    return {
      message: error.message,
      stack: error.stack,
      componentStack: errorInfo.componentStack,
      timestamp: new Date().toISOString(),
      userAgent: navigator.userAgent,
      url: window.location.href,
      errorCount
    };
  }

  static logToDevelopment(error: Error, errorInfo: React.ErrorInfo): void {
    if (process.env.NODE_ENV === 'development') {
      console.error('Chat Error Boundary caught:', error, errorInfo);
    }
  }

  static sendToProduction(errorReport: ErrorReport): void {
    if (process.env.NODE_ENV === 'production') {
      console.error('Error Report:', errorReport);
    }
  }

  static storeToLocalStorage(errorReport: ErrorReport): void {
    const errors = this.getStoredErrors();
    errors.push(errorReport);
    this.trimStoredErrors(errors);
    this.saveStoredErrors(errors);
  }

  static getStoredErrors(): ErrorReport[] {
    const stored = localStorage.getItem(this.STORAGE_KEY);
    return stored ? JSON.parse(stored) : [];
  }

  private static trimStoredErrors(errors: ErrorReport[]): void {
    if (errors.length > this.MAX_STORED_ERRORS) {
      errors.shift();
    }
  }

  private static saveStoredErrors(errors: ErrorReport[]): void {
    localStorage.setItem(this.STORAGE_KEY, JSON.stringify(errors));
  }

  static reportError(
    error: Error,
    errorInfo: React.ErrorInfo,
    errorCount: number
  ): void {
    const report = this.createReport(error, errorInfo, errorCount);
    this.logToDevelopment(error, errorInfo);
    this.sendToProduction(report);
    this.storeToLocalStorage(report);
  }
}