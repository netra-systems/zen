import React from 'react';
import { renderHook, act, waitFor } from '@testing-library/react';
import { GTMProvider } from '@/providers/GTMProvider';
import { useGTMDebug } from '@/hooks/useGTMDebug';

// Mock Next.js Script component
jest.mock('next/script', () => {
  return function MockScript({ onLoad, onReady, ...props }: any) {
    React.useEffect(() => {
      if (onReady) onReady();
      const timer = setTimeout(() => {
        if (onLoad) onLoad();
      }, 50);
      return () => clearTimeout(timer);
    }, [onLoad, onReady]);
    return <script {...props} data-testid="gtm-script" />;
  };
});

// Mock logger
jest.mock('@/lib/logger', () => ({
  logger: {
    debug: jest.fn(),
    error: jest.fn(),
  },
}));

const createWrapper = (enabled = true, debug = true) => {
  return ({ children }: { children: React.ReactNode }) => (
    <GTMProvider enabled={enabled} config={{ debug, environment: 'development' }}>
      {children}
    </GTMProvider>
  );
};

describe('useGTMDebug Hook', () => {
  let mockDataLayer: any[];
  let consoleSpy: jest.SpyInstance;

  beforeEach(() => {
    mockDataLayer = [];
    Object.defineProperty(global, 'window', {
      value: {
        dataLayer: mockDataLayer,
        location: {
          pathname: '/debug-test-path'
        },
        gtag: jest.fn(),
        google_tag_manager: {
          'GTM-WKP28PNQ': {
            dataLayer: mockDataLayer
          }
        }
      },
      writable: true
    });

    consoleSpy = jest.spyOn(console, 'log').mockImplementation();
  });

  afterEach(() => {
    jest.clearAllMocks();
    consoleSpy.mockRestore();
  });

  describe('Hook Initialization', () => {
    it('should provide debug functionality', async () => {
      const { result } = renderHook(() => useGTMDebug(), {
        wrapper: createWrapper()
      });

      await waitFor(() => {
        expect(result.current).toHaveProperty('isDebugMode');
        expect(result.current).toHaveProperty('debugInfo');
        expect(result.current).toHaveProperty('enableDebug');
        expect(result.current).toHaveProperty('disableDebug');
        expect(result.current).toHaveProperty('getDataLayerSnapshot');
        expect(result.current).toHaveProperty('validateEvent');
        expect(result.current).toHaveProperty('getPerformanceMetrics');
        expect(result.current).toHaveProperty('exportDebugData');
      });
    });

    it('should correctly identify debug mode status', async () => {
      const { result } = renderHook(() => useGTMDebug(), {
        wrapper: createWrapper(true, true)
      });

      await waitFor(() => {
        expect(result.current.isDebugMode).toBe(true);
      });
    });

    it('should handle non-debug mode', async () => {
      const { result } = renderHook(() => useGTMDebug(), {
        wrapper: createWrapper(true, false)
      });

      await waitFor(() => {
        expect(result.current.isDebugMode).toBe(false);
      });
    });
  });

  describe('Debug Mode Toggle', () => {
    it('should enable debug mode and push debug event', async () => {
      const { result } = renderHook(() => useGTMDebug(), {
        wrapper: createWrapper()
      });

      await waitFor(() => {
        expect(result.current.isDebugMode).toBe(true);
      });

      act(() => {
        result.current.enableDebug();
      });

      await waitFor(() => {
        const debugEvent = mockDataLayer.find(item => item.event === 'gtm.debug.enable');
        expect(debugEvent).toBeDefined();
        expect(debugEvent.debug_mode).toBe(true);
        expect(consoleSpy).toHaveBeenCalledWith(expect.stringContaining('[GTM Debug] Debug mode enabled'));
      });
    });

    it('should disable debug mode and push debug event', async () => {
      const { result } = renderHook(() => useGTMDebug(), {
        wrapper: createWrapper()
      });

      await waitFor(() => {
        expect(result.current.isDebugMode).toBe(true);
      });

      act(() => {
        result.current.disableDebug();
      });

      await waitFor(() => {
        const debugEvent = mockDataLayer.find(item => item.event === 'gtm.debug.disable');
        expect(debugEvent).toBeDefined();
        expect(debugEvent.debug_mode).toBe(false);
        expect(consoleSpy).toHaveBeenCalledWith(expect.stringContaining('[GTM Debug] Debug mode disabled'));
      });
    });
  });

  describe('Debug Information', () => {
    it('should provide comprehensive debug info', async () => {
      const { result } = renderHook(() => useGTMDebug(), {
        wrapper: createWrapper()
      });

      await waitFor(() => {
        expect(result.current.debugInfo).toBeDefined();
        expect(result.current.debugInfo).toHaveProperty('containerId');
        expect(result.current.debugInfo).toHaveProperty('environment');
        expect(result.current.debugInfo).toHaveProperty('scriptStatus');
        expect(result.current.debugInfo).toHaveProperty('loadTime');
        expect(result.current.debugInfo).toHaveProperty('totalEvents');
        expect(result.current.debugInfo).toHaveProperty('recentEvents');
        expect(result.current.debugInfo).toHaveProperty('errors');
        expect(result.current.debugInfo).toHaveProperty('performance');
        expect(result.current.debugInfo).toHaveProperty('configuration');
      });

      expect(result.current.debugInfo.containerId).toBe('GTM-WKP28PNQ');
      expect(result.current.debugInfo.environment).toBe('development');
      expect(result.current.debugInfo.scriptStatus).toBe('loaded');
    });

    it('should track performance metrics', async () => {
      const { result } = renderHook(() => useGTMDebug(), {
        wrapper: createWrapper()
      });

      await waitFor(() => {
        expect(result.current.debugInfo.performance).toBeDefined();
        expect(result.current.debugInfo.performance).toHaveProperty('scriptLoadTime');
        expect(result.current.debugInfo.performance).toHaveProperty('eventProcessingTimes');
        expect(result.current.debugInfo.performance).toHaveProperty('averageEventTime');
        expect(result.current.debugInfo.performance).toHaveProperty('dataLayerSize');
      });
    });
  });

  describe('DataLayer Snapshot', () => {
    it('should provide current dataLayer snapshot', async () => {
      const { result } = renderHook(() => useGTMDebug(), {
        wrapper: createWrapper()
      });

      // Add some test data to dataLayer
      mockDataLayer.push(
        { event: 'test_event_1', category: 'test' },
        { event: 'test_event_2', category: 'test' }
      );

      await waitFor(() => {
        const snapshot = result.current.getDataLayerSnapshot();
        expect(snapshot).toBeInstanceOf(Array);
        expect(snapshot.length).toBeGreaterThanOrEqual(2);
        
        const testEvents = snapshot.filter(item => 
          item.event && item.event.startsWith('test_event_')
        );
        expect(testEvents).toHaveLength(2);
      });
    });

    it('should provide filtered dataLayer snapshot', async () => {
      const { result } = renderHook(() => useGTMDebug(), {
        wrapper: createWrapper()
      });

      mockDataLayer.push(
        { event: 'user_login', event_category: 'authentication' },
        { event: 'page_view', event_category: 'navigation' },
        { event: 'user_signup', event_category: 'authentication' }
      );

      await waitFor(() => {
        const authSnapshot = result.current.getDataLayerSnapshot({
          eventFilter: (event) => event.event_category === 'authentication'
        });
        
        expect(authSnapshot).toHaveLength(2);
        expect(authSnapshot.every(item => item.event_category === 'authentication')).toBe(true);
      });
    });

    it('should provide limited dataLayer snapshot', async () => {
      const { result } = renderHook(() => useGTMDebug(), {
        wrapper: createWrapper()
      });

      // Add many events
      for (let i = 0; i < 50; i++) {
        mockDataLayer.push({ event: `test_${i}`, index: i });
      }

      await waitFor(() => {
        const limitedSnapshot = result.current.getDataLayerSnapshot({ limit: 10 });
        expect(limitedSnapshot).toHaveLength(10);
        // Should get the most recent events
        expect(limitedSnapshot[0].index).toBeGreaterThan(40);
      });
    });
  });

  describe('Event Validation', () => {
    it('should validate well-formed events', async () => {
      const { result } = renderHook(() => useGTMDebug(), {
        wrapper: createWrapper()
      });

      await waitFor(() => {
        const validEvent = {
          event: 'user_login',
          event_category: 'authentication',
          event_action: 'login_success'
        };

        const validation = result.current.validateEvent(validEvent);
        expect(validation.isValid).toBe(true);
        expect(validation.errors).toHaveLength(0);
        expect(validation.warnings).toHaveLength(0);
        expect(validation.suggestions).toBeDefined();
      });
    });

    it('should identify missing required fields', async () => {
      const { result } = renderHook(() => useGTMDebug(), {
        wrapper: createWrapper()
      });

      await waitFor(() => {
        const invalidEvent = {
          event_category: 'test'
          // Missing required 'event' field
        };

        const validation = result.current.validateEvent(invalidEvent as any);
        expect(validation.isValid).toBe(false);
        expect(validation.errors).toContain('Missing required field: event');
      });
    });

    it('should provide warnings for best practices', async () => {
      const { result } = renderHook(() => useGTMDebug(), {
        wrapper: createWrapper()
      });

      await waitFor(() => {
        const eventWithIssues = {
          event: 'User Login',  // Should be snake_case
          event_category: 'auth',  // Could be more descriptive
          custom_field: 'very_long_value_that_exceeds_typical_limits_for_event_parameters'
        };

        const validation = result.current.validateEvent(eventWithIssues);
        expect(validation.warnings.length).toBeGreaterThan(0);
        expect(validation.warnings).toContain(expect.stringContaining('Event names should use snake_case'));
      });
    });

    it('should suggest improvements', async () => {
      const { result } = renderHook(() => useGTMDebug(), {
        wrapper: createWrapper()
      });

      await waitFor(() => {
        const basicEvent = {
          event: 'click',
          event_category: 'interaction'
        };

        const validation = result.current.validateEvent(basicEvent);
        expect(validation.suggestions).toBeDefined();
        expect(validation.suggestions.length).toBeGreaterThan(0);
        expect(validation.suggestions).toContain(expect.stringContaining('event_action'));
      });
    });
  });

  describe('Performance Metrics', () => {
    it('should provide detailed performance metrics', async () => {
      const { result } = renderHook(() => useGTMDebug(), {
        wrapper: createWrapper()
      });

      await waitFor(() => {
        const metrics = result.current.getPerformanceMetrics();
        expect(metrics).toHaveProperty('scriptLoad');
        expect(metrics).toHaveProperty('eventProcessing');
        expect(metrics).toHaveProperty('dataLayer');
        expect(metrics).toHaveProperty('memory');
        expect(metrics).toHaveProperty('timing');
      });
    });

    it('should track script loading performance', async () => {
      const { result } = renderHook(() => useGTMDebug(), {
        wrapper: createWrapper()
      });

      await waitFor(() => {
        const metrics = result.current.getPerformanceMetrics();
        expect(metrics.scriptLoad).toHaveProperty('loadTime');
        expect(metrics.scriptLoad).toHaveProperty('status');
        expect(metrics.scriptLoad).toHaveProperty('retries');
        
        expect(metrics.scriptLoad.status).toBe('loaded');
        expect(typeof metrics.scriptLoad.loadTime).toBe('number');
      });
    });

    it('should track event processing performance', async () => {
      const { result } = renderHook(() => useGTMDebug(), {
        wrapper: createWrapper()
      });

      await waitFor(() => {
        const metrics = result.current.getPerformanceMetrics();
        expect(metrics.eventProcessing).toHaveProperty('totalEvents');
        expect(metrics.eventProcessing).toHaveProperty('averageProcessingTime');
        expect(metrics.eventProcessing).toHaveProperty('errorRate');
        expect(metrics.eventProcessing).toHaveProperty('queueSize');
      });
    });

    it('should track dataLayer performance', async () => {
      const { result } = renderHook(() => useGTMDebug(), {
        wrapper: createWrapper()
      });

      await waitFor(() => {
        const metrics = result.current.getPerformanceMetrics();
        expect(metrics.dataLayer).toHaveProperty('size');
        expect(metrics.dataLayer).toHaveProperty('memoryUsage');
        expect(metrics.dataLayer).toHaveProperty('pushRate');
        
        expect(typeof metrics.dataLayer.size).toBe('number');
      });
    });
  });

  describe('Debug Data Export', () => {
    it('should export comprehensive debug data', async () => {
      const { result } = renderHook(() => useGTMDebug(), {
        wrapper: createWrapper()
      });

      // Add some test events
      mockDataLayer.push(
        { event: 'test_event', category: 'test' },
        { event: 'another_event', category: 'test' }
      );

      await waitFor(() => {
        const exportData = result.current.exportDebugData();
        
        expect(exportData).toHaveProperty('timestamp');
        expect(exportData).toHaveProperty('configuration');
        expect(exportData).toHaveProperty('performance');
        expect(exportData).toHaveProperty('dataLayer');
        expect(exportData).toHaveProperty('events');
        expect(exportData).toHaveProperty('errors');
        expect(exportData).toHaveProperty('environment');
        
        expect(exportData.timestamp).toBeInstanceOf(Date);
        expect(exportData.configuration.containerId).toBe('GTM-WKP28PNQ');
        expect(exportData.dataLayer).toBeInstanceOf(Array);
      });
    });

    it('should export filtered debug data', async () => {
      const { result } = renderHook(() => useGTMDebug(), {
        wrapper: createWrapper()
      });

      await waitFor(() => {
        const filteredExport = result.current.exportDebugData({
          includeDataLayer: false,
          eventFilter: (event) => event.event_category === 'authentication',
          timeRange: {
            start: new Date(Date.now() - 3600000), // 1 hour ago
            end: new Date()
          }
        });
        
        expect(filteredExport).not.toHaveProperty('dataLayer');
        expect(filteredExport).toHaveProperty('configuration');
        expect(filteredExport).toHaveProperty('performance');
        expect(filteredExport.events.every((event: any) => 
          event.event_category === 'authentication'
        )).toBe(true);
      });
    });

    it('should format export data for different formats', async () => {
      const { result } = renderHook(() => useGTMDebug(), {
        wrapper: createWrapper()
      });

      await waitFor(() => {
        // JSON format (default)
        const jsonExport = result.current.exportDebugData({ format: 'json' });
        expect(typeof jsonExport).toBe('object');
        
        // CSV format for events
        const csvExport = result.current.exportDebugData({ 
          format: 'csv',
          includeDataLayer: false 
        });
        expect(typeof csvExport).toBe('string');
        expect(csvExport).toContain('event,event_category,timestamp');
        
        // Summary format
        const summaryExport = result.current.exportDebugData({ format: 'summary' });
        expect(summaryExport).toHaveProperty('summary');
        expect(summaryExport.summary).toHaveProperty('totalEvents');
        expect(summaryExport.summary).toHaveProperty('errorCount');
        expect(summaryExport.summary).toHaveProperty('performanceMetrics');
      });
    });
  });

  describe('Real-time Monitoring', () => {
    it('should provide real-time event monitoring', async () => {
      const { result } = renderHook(() => useGTMDebug(), {
        wrapper: createWrapper()
      });

      let capturedEvents: any[] = [];
      
      await waitFor(() => {
        // Start monitoring
        const stopMonitoring = result.current.startRealTimeMonitoring({
          onEvent: (event) => capturedEvents.push(event),
          onError: (error) => console.error('Monitor error:', error),
          filter: (event) => event.event_category === 'test'
        });

        expect(typeof stopMonitoring).toBe('function');
      });

      // Simulate events being added to dataLayer
      act(() => {
        mockDataLayer.push({ event: 'test_monitored', event_category: 'test' });
        mockDataLayer.push({ event: 'other_event', event_category: 'other' });
      });

      await waitFor(() => {
        expect(capturedEvents).toHaveLength(1);
        expect(capturedEvents[0].event).toBe('test_monitored');
      });
    });

    it('should handle monitoring lifecycle', async () => {
      const { result } = renderHook(() => useGTMDebug(), {
        wrapper: createWrapper()
      });

      let monitoringActive = false;

      await waitFor(() => {
        const stopMonitoring = result.current.startRealTimeMonitoring({
          onEvent: () => { monitoringActive = true; },
          onStart: () => { monitoringActive = true; },
          onStop: () => { monitoringActive = false; }
        });

        expect(monitoringActive).toBe(true);

        // Stop monitoring
        stopMonitoring();
        expect(monitoringActive).toBe(false);
      });
    });
  });

  describe('Error Handling and Edge Cases', () => {
    it('should handle missing window object', () => {
      const originalWindow = global.window;
      // @ts-ignore
      delete global.window;

      const { result } = renderHook(() => useGTMDebug(), {
        wrapper: createWrapper()
      });

      expect(result.current.isDebugMode).toBe(true); // From config
      expect(() => result.current.getDataLayerSnapshot()).not.toThrow();

      global.window = originalWindow;
    });

    it('should handle missing dataLayer', async () => {
      global.window.dataLayer = undefined;

      const { result } = renderHook(() => useGTMDebug(), {
        wrapper: createWrapper()
      });

      await waitFor(() => {
        const snapshot = result.current.getDataLayerSnapshot();
        expect(snapshot).toEqual([]);

        const metrics = result.current.getPerformanceMetrics();
        expect(metrics.dataLayer.size).toBe(0);
      });
    });

    it('should handle GTM script errors', async () => {
      const { result } = renderHook(() => useGTMDebug(), {
        wrapper: createWrapper()
      });

      await waitFor(() => {
        const metrics = result.current.getPerformanceMetrics();
        expect(metrics.scriptLoad).toHaveProperty('status');
        
        // Even with errors, should provide meaningful debug info
        const exportData = result.current.exportDebugData();
        expect(exportData).toHaveProperty('errors');
      });
    });
  });
});