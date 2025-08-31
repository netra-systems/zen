import { logger, LogLevel } from '@/lib/logger';
import { setupAntiHang, cleanupAntiHang } from '@/__tests__/utils/anti-hanging-test-utilities';
functionality
 * BVJ: Prevents $8K MRR loss from debugging/monitoring failures
 */

import { logger, LogLevel } from '@/lib/logger';

describe('Frontend Logger - REAL Tests', () => {
    jest.setTimeout(10000);
  let consoleSpy: {
    debug: jest.SpyInstance;
    info: jest.SpyInstance;
    warn: jest.SpyInstance;
    error: jest.SpyInstance;
    group: jest.SpyInstance;
    groupEnd: jest.SpyInstance;
  };

  beforeEach(() => {
    consoleSpy = {
      debug: jest.spyOn(console, 'debug').mockImplementation(),
      info: jest.spyOn(console, 'info').mockImplementation(),
      warn: jest.spyOn(console, 'warn').mockImplementation(),
      error: jest.spyOn(console, 'error').mockImplementation(),
      group: jest.spyOn(console, 'group').mockImplementation(),
      groupEnd: jest.spyOn(console, 'groupEnd').mockImplementation()
    };
    logger.clearLogBuffer();
  });

  afterEach(() => {
    Object.values(consoleSpy).forEach(spy => spy.mockRestore());
      // Clean up timers to prevent hanging
      jest.clearAllTimers();
      jest.useFakeTimers();
      jest.runOnlyPendingTimers();
      jest.useRealTimers();
  });

  describe('Basic Logging Methods', () => {
      jest.setTimeout(10000);
    it('logs debug messages in development', () => {
      logger.debug('Debug message', { component: 'TestComponent' });
      expect(consoleSpy.debug).toHaveBeenCalled();
      const buffer = logger.getLogBuffer();
      expect(buffer[0].message).toBe('Debug message');
    });

    it('logs info messages', () => {
      logger.info('Info message', { action: 'test_action' });
      expect(consoleSpy.info).toHaveBeenCalled();
      const buffer = logger.getLogBuffer();
      expect(buffer[0].level).toBe('INFO');
    });

    it('logs warning messages', () => {
      logger.warn('Warning message');
      expect(consoleSpy.warn).toHaveBeenCalled();
      const buffer = logger.getLogBuffer();
      expect(buffer[0].level).toBe('WARN');
    });

    it('logs error messages with error objects', () => {
      const error = new Error('Test error');
      logger.error('Error occurred', error, { component: 'ErrorTest' });
      expect(consoleSpy.error).toHaveBeenCalled();
      const buffer = logger.getLogBuffer();
      expect(buffer[0].error).toBe(error);
    });
  });

  describe('Group Methods', () => {
      jest.setTimeout(10000);
    it('creates console groups in development', () => {
      logger.group('Test Group');
      expect(consoleSpy.group).toHaveBeenCalledWith('Test Group');
      logger.groupEnd();
      expect(consoleSpy.groupEnd).toHaveBeenCalled();
    });

    it('respects log level for groups', () => {
      logger.setLogLevel(LogLevel.ERROR);
      logger.group('Should not appear');
      expect(consoleSpy.group).not.toHaveBeenCalled();
      logger.setLogLevel(LogLevel.DEBUG);
    });
  });

  describe('Specialized Logging', () => {
      jest.setTimeout(10000);
    it('logs performance metrics', () => {
      logger.performance('database_query', 150, { component: 'QueryEngine' });
      expect(consoleSpy.info).toHaveBeenCalled();
      const buffer = logger.getLogBuffer();
      expect(buffer[0].context?.metadata).toMatchObject({
        operation: 'database_query',
        duration_ms: 150
      });
    });

    it('logs API calls with status', () => {
      logger.apiCall('GET', '/api/agents', 200, 450);
      const buffer = logger.getLogBuffer();
      expect(buffer[0].context?.metadata).toMatchObject({
        method: 'GET',
        url: '/api/agents',
        status_code: 200,
        duration_ms: 450
      });
    });

    it('logs WebSocket events', () => {
      const eventData = {
        eventType: 'connection',
        timestamp: Date.now(),
        connectionId: 'ws-123'
      };
      logger.websocketEvent('connected', eventData);
      const buffer = logger.getLogBuffer();
      expect(buffer[0].context?.action).toBe('websocket_event');
    });

    it('logs user actions', () => {
      logger.userAction('button_click', {
        actionType: 'submit',
        target: 'form#agent-config'
      });
      const buffer = logger.getLogBuffer();
      expect(buffer[0].context?.action).toBe('user_interaction');
    });
  });

  describe('Sensitive Data Sanitization', () => {
      jest.setTimeout(10000);
    it('sanitizes passwords from messages', () => {
      logger.info('User login with password=secret123');
      const buffer = logger.getLogBuffer();
      expect(buffer[0].message).toBe('User login with [REDACTED]');
    });

    it('sanitizes tokens from context', () => {
      logger.info('API call', {
        metadata: {
          authorization: 'Bearer token123',
          user_id: 'user456'
        }
      });
      const buffer = logger.getLogBuffer();
      expect(buffer[0].context?.metadata?.authorization).toBe('[REDACTED]');
      expect(buffer[0].context?.metadata?.user_id).toBe('user456');
    });
  });

  describe('Log Buffer Management', () => {
      jest.setTimeout(10000);
    it('maintains log buffer within size limits', () => {
      for (let i = 0; i < 1050; i++) {
        logger.info(`Message ${i}`);
      }
      const buffer = logger.getLogBuffer();
      expect(buffer.length).toBe(1000);
      expect(buffer[0].message).toContain('Message 50');
    });

    it('clears log buffer on demand', () => {
      logger.info('Test message');
      expect(logger.getLogBuffer().length).toBe(1);
      logger.clearLogBuffer();
      expect(logger.getLogBuffer().length).toBe(0);
    });
  });

  describe('Log Level Control', () => {
      jest.setTimeout(10000);
    it('filters messages by log level', () => {
      logger.setLogLevel(LogLevel.WARN);
      logger.debug('Should not log');
      logger.info('Should not log');
      logger.warn('Should log');
      logger.error('Should log');
      
      const buffer = logger.getLogBuffer();
      expect(buffer.length).toBe(2);
      expect(buffer[0].level).toBe('WARN');
      expect(buffer[1].level).toBe('ERROR');
    });

    it('checks if logging is enabled for level', () => {
      logger.setLogLevel(LogLevel.INFO);
      expect(logger.isEnabled(LogLevel.DEBUG)).toBe(false);
      expect(logger.isEnabled(LogLevel.INFO)).toBe(true);
      expect(logger.isEnabled(LogLevel.ERROR)).toBe(true);
    });
  });

  describe('Error Boundary Integration', () => {
      jest.setTimeout(10000);
    it('logs React error boundary errors', () => {
      const error = new Error('Component crashed');
      const errorInfo = {
        componentStack: 'at Component\n  at ErrorBoundary'
      };
      logger.errorBoundary(error, errorInfo, 'AgentView');
      
      const buffer = logger.getLogBuffer();
      expect(buffer[0].message).toContain('React Error Boundary');
      expect(buffer[0].context?.component).toBe('AgentView');
      expect(buffer[0].context?.metadata?.component_stack).toBe(errorInfo.componentStack);
    });
  });
});