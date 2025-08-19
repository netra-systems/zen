/**
 * Logger Integration Tests - Validates logger usage across components
 * BVJ: Prevents $15K MRR loss from monitoring/debugging failures
 */

import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { logger } from '@/lib/logger';
import { debugLayerVisibility } from '@/utils/layer-visibility-manager';
import type { LayerVisibilityConfig } from '@/utils/layer-visibility-manager';

// Test component that uses the logger
const TestComponent: React.FC = () => {
  const handleClick = () => {
    logger.userAction('test_button_click', {
      actionType: 'test',
      timestamp: Date.now()
    });
  };

  const handleApiCall = async () => {
    const start = Date.now();
    logger.apiCall('GET', '/api/test', 200, Date.now() - start);
  };

  const handleWebSocketEvent = () => {
    logger.websocketEvent('test_event', {
      eventType: 'test',
      timestamp: Date.now()
    });
  };

  const handlePerformanceLog = () => {
    logger.performance('test_operation', 100);
  };

  const handleDebugLayer = () => {
    const config: LayerVisibilityConfig = {
      fastLayerData: {
        agentName: 'TestAgent',
        activeTools: ['tool1'],
        toolStatuses: [],
        taskId: 'test-123',
        status: 'running',
        startTime: Date.now()
      },
      mediumLayerData: null,
      slowLayerData: null,
      isProcessing: true
    };
    debugLayerVisibility(config);
  };

  return (
    <div>
      <button onClick={handleClick}>User Action</button>
      <button onClick={handleApiCall}>API Call</button>
      <button onClick={handleWebSocketEvent}>WebSocket Event</button>
      <button onClick={handlePerformanceLog}>Performance Log</button>
      <button onClick={handleDebugLayer}>Debug Layer</button>
    </div>
  );
};

describe('Logger Integration - Cross-Component Usage', () => {
  let loggerSpies: {
    debug: jest.SpyInstance;
    info: jest.SpyInstance;
    warn: jest.SpyInstance;
    error: jest.SpyInstance;
    userAction: jest.SpyInstance;
    apiCall: jest.SpyInstance;
    websocketEvent: jest.SpyInstance;
    performance: jest.SpyInstance;
    group: jest.SpyInstance;
    groupEnd: jest.SpyInstance;
  };

  beforeEach(() => {
    loggerSpies = {
      debug: jest.spyOn(logger, 'debug'),
      info: jest.spyOn(logger, 'info'),
      warn: jest.spyOn(logger, 'warn'),
      error: jest.spyOn(logger, 'error'),
      userAction: jest.spyOn(logger, 'userAction'),
      apiCall: jest.spyOn(logger, 'apiCall'),
      websocketEvent: jest.spyOn(logger, 'websocketEvent'),
      performance: jest.spyOn(logger, 'performance'),
      group: jest.spyOn(logger, 'group'),
      groupEnd: jest.spyOn(logger, 'groupEnd')
    };
    logger.clearLogBuffer();
  });

  afterEach(() => {
    Object.values(loggerSpies).forEach(spy => spy.mockRestore());
  });

  describe('Component Logger Usage', () => {
    it('logs user actions from components', () => {
      render(<TestComponent />);
      const button = screen.getByText('User Action');
      fireEvent.click(button);
      
      expect(loggerSpies.userAction).toHaveBeenCalledWith(
        'test_button_click',
        expect.objectContaining({
          actionType: 'test',
          timestamp: expect.any(Number)
        })
      );
    });

    it('logs API calls from components', async () => {
      render(<TestComponent />);
      const button = screen.getByText('API Call');
      fireEvent.click(button);
      
      expect(loggerSpies.apiCall).toHaveBeenCalledWith(
        'GET',
        '/api/test',
        200,
        expect.any(Number)
      );
    });

    it('logs WebSocket events from components', () => {
      render(<TestComponent />);
      const button = screen.getByText('WebSocket Event');
      fireEvent.click(button);
      
      expect(loggerSpies.websocketEvent).toHaveBeenCalledWith(
        'test_event',
        expect.objectContaining({
          eventType: 'test',
          timestamp: expect.any(Number)
        })
      );
    });

    it('logs performance metrics from components', () => {
      render(<TestComponent />);
      const button = screen.getByText('Performance Log');
      fireEvent.click(button);
      
      expect(loggerSpies.performance).toHaveBeenCalledWith(
        'test_operation',
        100
      );
    });
  });

  describe('Layer Visibility Manager Integration', () => {
    it('uses logger group methods for debugging', () => {
      render(<TestComponent />);
      const button = screen.getByText('Debug Layer');
      fireEvent.click(button);
      
      expect(loggerSpies.group).toHaveBeenCalledWith('Layer Visibility Debug');
      expect(loggerSpies.debug).toHaveBeenCalled();
      expect(loggerSpies.groupEnd).toHaveBeenCalled();
    });
  });

  describe('Error Handling Integration', () => {
    it('logs errors with proper context', () => {
      const error = new Error('Test error');
      const ErrorComponent: React.FC = () => {
        React.useEffect(() => {
          try {
            throw error;
          } catch (e) {
            logger.error('Component error', e as Error, {
              component: 'ErrorComponent',
              action: 'mount'
            });
          }
        }, []);
        return <div>Error Component</div>;
      };

      render(<ErrorComponent />);
      
      expect(loggerSpies.error).toHaveBeenCalledWith(
        'Component error',
        error,
        expect.objectContaining({
          component: 'ErrorComponent',
          action: 'mount'
        })
      );
    });
  });

  describe('Log Buffer Verification', () => {
    it('accumulates logs from multiple sources', () => {
      render(<TestComponent />);
      
      // Trigger multiple logging actions
      fireEvent.click(screen.getByText('User Action'));
      fireEvent.click(screen.getByText('API Call'));
      fireEvent.click(screen.getByText('WebSocket Event'));
      fireEvent.click(screen.getByText('Performance Log'));
      
      const buffer = logger.getLogBuffer();
      expect(buffer.length).toBeGreaterThanOrEqual(4);
      
      // Verify different log types in buffer
      const logTypes = buffer.map(entry => entry.context?.action);
      expect(logTypes).toContain('user_interaction');
      expect(logTypes).toContain('api_call');
      expect(logTypes).toContain('websocket_event');
      expect(logTypes).toContain('performance');
    });
  });

  describe('Production Safety', () => {
    it('sanitizes sensitive data in logs', () => {
      const SensitiveComponent: React.FC = () => {
        const handleSensitive = () => {
          logger.info('Auth token=Bearer abc123 password=secret');
          logger.info('User data', {
            metadata: {
              token: 'xyz789',
              user_id: 'user123'
            }
          });
        };

        return <button onClick={handleSensitive}>Log Sensitive</button>;
      };

      render(<SensitiveComponent />);
      fireEvent.click(screen.getByText('Log Sensitive'));
      
      const buffer = logger.getLogBuffer();
      
      // Check that sensitive data is redacted
      expect(buffer[0].message).toContain('[REDACTED]');
      expect(buffer[0].message).not.toContain('abc123');
      expect(buffer[0].message).not.toContain('secret');
      
      expect(buffer[1].context?.metadata?.token).toBe('[REDACTED]');
      expect(buffer[1].context?.metadata?.user_id).toBe('user123');
    });
  });

  describe('Multi-Component Orchestration', () => {
    it('tracks logs across component hierarchy', () => {
      const ParentComponent: React.FC = () => {
        React.useEffect(() => {
          logger.info('Parent mounted', { component: 'Parent' });
        }, []);

        return (
          <div>
            <ChildComponent />
          </div>
        );
      };

      const ChildComponent: React.FC = () => {
        React.useEffect(() => {
          logger.info('Child mounted', { component: 'Child' });
        }, []);

        return <GrandchildComponent />;
      };

      const GrandchildComponent: React.FC = () => {
        React.useEffect(() => {
          logger.info('Grandchild mounted', { component: 'Grandchild' });
        }, []);

        return <div>Grandchild</div>;
      };

      render(<ParentComponent />);
      
      const buffer = logger.getLogBuffer();
      const components = buffer.map(entry => entry.context?.component);
      
      expect(components).toContain('Parent');
      expect(components).toContain('Child');
      expect(components).toContain('Grandchild');
    });
  });
});