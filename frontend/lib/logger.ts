/**
 * Frontend Logger Utility
 * Provides structured logging with environment-aware configuration
 * Replaces console.log/warn/error with proper logging patterns
 */

export interface WebSocketEventData {
  eventType: string;
  payload?: unknown;
  timestamp: number;
  connectionId?: string;
  error?: string;
}

export interface UserActionDetails {
  actionType: string;
  target?: string;
  metadata?: Record<string, string | number | boolean>;
  timestamp?: number;
}

export interface ErrorBoundaryInfo {
  componentStack?: string;
  errorBoundary?: string;
  props?: Record<string, unknown>;
}

export enum LogLevel {
  DEBUG = 0,
  INFO = 1,
  WARN = 2,
  ERROR = 3,
  SILENT = 4
}

interface LogContext {
  component?: string;
  action?: string;
  userId?: string;
  sessionId?: string;
  traceId?: string;
  metadata?: Record<string, unknown>;
}

interface LogEntry {
  timestamp: string;
  level: string;
  message: string;
  context?: LogContext;
  error?: Error;
  source: string;
}

class FrontendLogger {
  private currentLevel: LogLevel;
  private isDevelopment: boolean;
  private isProduction: boolean;
  private logBuffer: LogEntry[] = [];
  private maxBufferSize = 1000;

  constructor() {
    this.isDevelopment = process.env.NODE_ENV === 'development' || process.env.NODE_ENV === 'test';
    this.isProduction = process.env.NODE_ENV === 'production';
    
    // Set log level based on environment
    const envLevel = process.env.NEXT_PUBLIC_LOG_LEVEL?.toUpperCase();
    this.currentLevel = this.parseLogLevel(envLevel) ?? (
      this.isProduction ? LogLevel.WARN : LogLevel.DEBUG
    );
    
    // Bind all public methods to ensure 'this' context is preserved
    // when methods are passed as callbacks
    this.debug = this.debug.bind(this);
    this.info = this.info.bind(this);
    this.warn = this.warn.bind(this);
    this.error = this.error.bind(this);
    this.performance = this.performance.bind(this);
    this.apiCall = this.apiCall.bind(this);
    this.websocketEvent = this.websocketEvent.bind(this);
    this.userAction = this.userAction.bind(this);
    this.errorBoundary = this.errorBoundary.bind(this);
    this.getLogBuffer = this.getLogBuffer.bind(this);
    this.clearLogBuffer = this.clearLogBuffer.bind(this);
    this.setLogLevel = this.setLogLevel.bind(this);
    this.isEnabled = this.isEnabled.bind(this);
    this.group = this.group.bind(this);
    this.groupEnd = this.groupEnd.bind(this);
  }

  private parseLogLevel(level?: string): LogLevel | null {
    switch (level) {
      case 'DEBUG': return LogLevel.DEBUG;
      case 'INFO': return LogLevel.INFO;
      case 'WARN': return LogLevel.WARN;
      case 'ERROR': return LogLevel.ERROR;
      case 'SILENT': return LogLevel.SILENT;
      default: return null;
    }
  }

  private shouldLog(level: LogLevel): boolean {
    return level >= this.currentLevel;
  }

  private formatMessage(level: string, message: string, context?: LogContext): string {
    const timestamp = new Date().toISOString();
    
    if (this.isDevelopment) {
      // Human-readable format for development
      let formatted = `[${timestamp}] ${level.toUpperCase()}: ${message}`;
      if (context?.component) {
        formatted += ` [${context.component}]`;
      }
      if (context?.action) {
        formatted += ` (${context.action})`;
      }
      return formatted;
    }

    // Structured format for production
    return JSON.stringify({
      timestamp,
      level: level.toUpperCase(),
      message,
      source: 'frontend',
      ...context
    });
  }

  private log(level: LogLevel, levelName: string, message: string, context?: LogContext, error?: Error): void {
    if (!this.shouldLog(level)) {
      return;
    }

    // Filter sensitive data
    const sanitizedContext = this.sanitizeContext(context);
    const sanitizedMessage = this.sanitizeMessage(message);

    const logEntry: LogEntry = {
      timestamp: new Date().toISOString(),
      level: levelName.toUpperCase(),
      message: sanitizedMessage,
      context: sanitizedContext,
      error,
      source: 'frontend'
    };

    // Add to buffer for potential remote logging
    this.addToBuffer(logEntry);

    // Output to console in development, or for errors in production
    if (this.isDevelopment || level >= LogLevel.ERROR) {
      const formattedMessage = this.formatMessage(levelName, sanitizedMessage, sanitizedContext);
      
      // Guard against environments where console might not be available
      if (typeof console !== 'undefined' && console) {
        switch (level) {
          case LogLevel.DEBUG:
            if (console.debug) console.debug(formattedMessage, sanitizedContext);
            break;
          case LogLevel.INFO:
            if (console.info) console.info(formattedMessage, sanitizedContext);
            break;
          case LogLevel.WARN:
            if (console.warn) console.warn(formattedMessage, sanitizedContext);
            break;
          case LogLevel.ERROR:
            if (console.error) console.error(formattedMessage, error || sanitizedContext);
            break;
        }
      }
    }
  }

  private sanitizeMessage(message: string): string {
    // Remove sensitive patterns from messages
    const sensitivePatterns = [
      /password[\s:=]+[^\s]+/gi,
      /token[\s:=]+(?:Bearer\s+)?[^\s]+/gi,
      /key[\s:=]+[^\s]+/gi,
      /secret[\s:=]+[^\s]+/gi,
      /bearer\s+[^\s]+/gi,
      /authorization[\s:=]+[^\s]+/gi
    ];

    let sanitized = message;
    sensitivePatterns.forEach(pattern => {
      sanitized = sanitized.replace(pattern, '[REDACTED]');
    });

    return sanitized;
  }

  private sanitizeContext(context?: LogContext): LogContext | undefined {
    if (!context) return context;

    const sensitiveFields = ['password', 'token', 'key', 'secret', 'authorization', 'bearer'];
    const sanitized = { ...context };

    // Sanitize metadata
    if (sanitized.metadata) {
      sanitized.metadata = { ...sanitized.metadata };
      Object.keys(sanitized.metadata).forEach(key => {
        if (sensitiveFields.some(field => key.toLowerCase().includes(field))) {
          sanitized.metadata![key] = '[REDACTED]';
        }
      });
    }

    return sanitized;
  }

  private addToBuffer(entry: LogEntry): void {
    this.logBuffer.push(entry);
    
    // Trim buffer if it exceeds max size
    if (this.logBuffer.length > this.maxBufferSize) {
      this.logBuffer = this.logBuffer.slice(-this.maxBufferSize);
    }
  }

  // Public logging methods
  debug(message: string, context?: LogContext): void {
    this.log(LogLevel.DEBUG, 'debug', message, context);
  }

  info(message: string, context?: LogContext): void {
    this.log(LogLevel.INFO, 'info', message, context);
  }

  warn(message: string, context?: LogContext): void {
    this.log(LogLevel.WARN, 'warn', message, context);
  }

  error(message: string, error?: Error, context?: LogContext): void {
    this.log(LogLevel.ERROR, 'error', message, context, error);
  }

  // Specialized logging methods
  performance(operation: string, duration: number, context?: LogContext): void {
    this.info(`Performance: ${operation} took ${duration}ms`, {
      ...context,
      action: 'performance',
      metadata: {
        ...context?.metadata,
        operation,
        duration_ms: duration
      }
    });
  }

  apiCall(method: string, url: string, status?: number, duration?: number, context?: LogContext): void {
    const message = `API ${method} ${url}${status ? ` -> ${status}` : ''}`;
    this.info(message, {
      ...context,
      action: 'api_call',
      metadata: {
        ...context?.metadata,
        method,
        url,
        status_code: status,
        duration_ms: duration
      }
    });
  }

  websocketEvent(event: string, data?: WebSocketEventData, context?: LogContext): void {
    this.debug(`WebSocket: ${event}`, {
      ...context,
      action: 'websocket_event',
      metadata: {
        ...context?.metadata,
        event,
        data_preview: data ? (typeof data === 'string' ? data.substring(0, 100) : JSON.stringify(data).substring(0, 100)) : undefined
      }
    });
  }

  userAction(action: string, details?: UserActionDetails, context?: LogContext): void {
    this.info(`User Action: ${action}`, {
      ...context,
      action: 'user_interaction',
      metadata: {
        ...context?.metadata,
        user_action: action,
        details
      }
    });
  }

  // Error boundary logging
  errorBoundary(error: Error, errorInfo: ErrorBoundaryInfo, component?: string): void {
    this.error('React Error Boundary caught an error', error, {
      component,
      action: 'error_boundary',
      metadata: {
        error_info: errorInfo,
        component_stack: errorInfo.componentStack
      }
    });
  }

  // Get log buffer for remote submission
  getLogBuffer(): LogEntry[] {
    return [...this.logBuffer];
  }

  // Clear log buffer
  clearLogBuffer(): void {
    this.logBuffer = [];
  }

  // Set log level dynamically
  setLogLevel(level: LogLevel): void {
    this.currentLevel = level;
  }

  // Check if logging is enabled for a level
  isEnabled(level: LogLevel): boolean {
    return this.shouldLog(level);
  }

  // Console group methods for development debugging
  group(label: string): void {
    if ((this.isDevelopment || process.env.NODE_ENV === 'test') && this.shouldLog(LogLevel.DEBUG)) {
      if (typeof console !== 'undefined' && console?.group) {
        console.group(label);
      }
    }
  }

  groupEnd(): void {
    if ((this.isDevelopment || process.env.NODE_ENV === 'test') && this.shouldLog(LogLevel.DEBUG)) {
      if (typeof console !== 'undefined' && console?.groupEnd) {
        console.groupEnd();
      }
    }
  }
}

// Create singleton instance
export const logger = new FrontendLogger();

// Convenience exports
export default logger;
export type { LogContext, LogEntry };