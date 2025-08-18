/**
 * Debug Logger Utility
 * Provides environment-aware logging with different levels
 * In production, only error and warn are shown
 * In development, all levels are shown
 */

type LogLevel = 'debug' | 'info' | 'warn' | 'error';

interface LoggerConfig {
  isDevelopment: boolean;
  enableDebug: boolean;
}

class DebugLogger {
  private config: LoggerConfig;

  constructor() {
    this.config = {
      isDevelopment: process.env.NODE_ENV === 'development',
      enableDebug: process.env.NEXT_PUBLIC_DEBUG === 'true'
    };
  }

  private shouldLog(level: LogLevel): boolean {
    if (!this.config.isDevelopment) {
      return level === 'error' || level === 'warn';
    }
    
    if (level === 'debug' && !this.config.enableDebug) {
      return false;
    }
    
    return true;
  }

  debug(...args: any[]): void {
    if (this.shouldLog('debug')) {
      console.debug('[DEBUG]', ...args);
    }
  }

  info(...args: any[]): void {
    if (this.shouldLog('info')) {
      console.info('[INFO]', ...args);
    }
  }

  warn(...args: any[]): void {
    if (this.shouldLog('warn')) {
      console.warn('[WARN]', ...args);
    }
  }

  error(...args: any[]): void {
    if (this.shouldLog('error')) {
      console.error('[ERROR]', ...args);
    }
  }

  // For critical errors that should always be logged
  critical(...args: any[]): void {
    console.error('[CRITICAL]', ...args);
  }

  // Group logging for better organization
  group(label: string): void {
    if (this.config.isDevelopment) {
      console.group(label);
    }
  }

  groupEnd(): void {
    if (this.config.isDevelopment) {
      console.groupEnd();
    }
  }

  // Table logging for structured data
  table(data: any): void {
    if (this.config.isDevelopment) {
      console.table(data);
    }
  }

  // Timing utilities
  time(label: string): void {
    if (this.config.isDevelopment) {
      console.time(label);
    }
  }

  timeEnd(label: string): void {
    if (this.config.isDevelopment) {
      console.timeEnd(label);
    }
  }
}

// Export singleton instance
export const logger = new DebugLogger();

// Export for testing purposes
export { DebugLogger };