import React from 'react';
import { render, screen, waitFor, act } from '@testing-library/react';
import { GTMProvider, useGTMContext } from '@/providers/GTMProvider';
import type { GTMConfig, GTMEventData } from '@/types/gtm.types';
import { setupAntiHang, cleanupAntiHang } from '@/__tests__/utils/anti-hanging-test-utilities';

// Mock Next.js Script component
jest.mock('next/script', () => {
  return function MockScript({ 
    src, 
    onLoad, 
    onError, 
    onReady, 
    children, 
    ...props 
  }: any) {
    React.useEffect(() => {
      // Simulate script loading sequence
      if (onReady) onReady();
      
      // Simulate successful load after a short delay
      const timer = setTimeout(() => {
        if (onLoad) onLoad();
      }, 100);

      return () => clearTimeout(timer);
    }, [onLoad, onReady]);

    return (
      <script {...props} src={src} data-testid="gtm-script">
        {children}
      </script>
    );
  };
});

// Mock logger
jest.mock('@/lib/logger', () => ({
  logger: {
    debug: jest.fn(),
    error: jest.fn(),
  },
}));

// Test component that uses GTM context
const TestComponent: React.FC<{ 
  onContextReady?: (context: any) => void;
  eventToTrack?: GTMEventData;
}> = ({ onContextReady, eventToTrack }) => {
  const gtmContext = useGTMContext();
  
  React.useEffect(() => {
    if (onContextReady) {
      onContextReady(gtmContext);
    }
  }, [gtmContext, onContextReady]);
  
  React.useEffect(() => {
    if (eventToTrack && gtmContext.isLoaded) {
      gtmContext.pushEvent(eventToTrack);
    }
  }, [eventToTrack, gtmContext]);
  
  return (
    <div data-testid="test-component">
      <div data-testid="gtm-loaded">{gtmContext.isLoaded ? 'loaded' : 'not-loaded'}</div>
      <div data-testid="gtm-enabled">{gtmContext.isEnabled ? 'enabled' : 'disabled'}</div>
      <div data-testid="container-id">{gtmContext.config.containerId}</div>
      <div data-testid="total-events">{gtmContext.debug.totalEvents}</div>
    </div>
  );
};

describe('GTMProvider', () => {
  setupAntiHang();
    jest.setTimeout(10000);
  let mockDataLayer: any[];
  let originalWindow: any;

  beforeEach(() => {
    mockDataLayer = [];
    originalWindow = global.window;
    
    // Mock window object
    Object.defineProperty(global, 'window', {
      value: {
        ...originalWindow,
        dataLayer: mockDataLayer,
        location: {
          pathname: '/test-path'
        }
      },
      writable: true
    });

    // Clear environment variables
    delete process.env.NEXT_PUBLIC_GTM_CONTAINER_ID;
    delete process.env.NEXT_PUBLIC_GTM_ENABLED;
    delete process.env.NEXT_PUBLIC_GTM_DEBUG;
    delete process.env.NEXT_PUBLIC_ENVIRONMENT;
  });

  afterEach(() => {
    jest.clearAllMocks();
    global.window = originalWindow;
      // Clean up timers to prevent hanging
      jest.clearAllTimers();
      jest.useFakeTimers();
      jest.runOnlyPendingTimers();
      jest.useRealTimers();
      cleanupAntiHang();
  });

  describe('Provider Initialization', () => {
        setupAntiHang();
      jest.setTimeout(10000);
    it('should render with default configuration', () => {
      render(
        <GTMProvider>
          <TestComponent />
        </GTMProvider>
      );

      expect(screen.getByTestId('gtm-enabled')).toHaveTextContent('disabled');
      expect(screen.getByTestId('container-id')).toHaveTextContent('GTM-WKP28PNQ');
    });

    it('should use environment variables for configuration', () => {
      process.env.NEXT_PUBLIC_GTM_CONTAINER_ID = 'GTM-TEST123';
      process.env.NEXT_PUBLIC_GTM_ENABLED = 'true';
      process.env.NEXT_PUBLIC_GTM_DEBUG = 'true';
      process.env.NEXT_PUBLIC_ENVIRONMENT = 'production';

      render(
        <GTMProvider>
          <TestComponent />
        </GTMProvider>
      );

      expect(screen.getByTestId('gtm-enabled')).toHaveTextContent('enabled');
      expect(screen.getByTestId('container-id')).toHaveTextContent('GTM-TEST123');
    });

    it('should override defaults with provided config', () => {
      const customConfig: Partial<GTMConfig> = {
        containerId: 'GTM-CUSTOM',
        enabled: true,
        debug: false,
        environment: 'staging'
      };

      render(
        <GTMProvider config={customConfig}>
          <TestComponent />
        </GTMProvider>
      );

      expect(screen.getByTestId('gtm-enabled')).toHaveTextContent('enabled');
      expect(screen.getByTestId('container-id')).toHaveTextContent('GTM-CUSTOM');
    });

    it('should respect enabled prop', () => {
      const customConfig: Partial<GTMConfig> = {
        enabled: true
      };

      render(
        <GTMProvider config={customConfig} enabled={false}>
          <TestComponent />
        </GTMProvider>
      );

      expect(screen.getByTestId('gtm-enabled')).toHaveTextContent('disabled');
    });
  });

  describe('DataLayer Initialization', () => {
        setupAntiHang();
      jest.setTimeout(10000);
    it('should initialize dataLayer when enabled', async () => {
      render(
        <GTMProvider enabled={true}>
          <TestComponent />
        </GTMProvider>
      );

      await waitFor(() => {
        expect(window.dataLayer).toBeDefined();
        expect(window.dataLayer.length).toBeGreaterThan(0);
        
        // Check initial GTM event
        const initEvent = window.dataLayer.find((item: any) => item.event === 'gtm.js');
        expect(initEvent).toBeDefined();
        expect(initEvent['gtm.start']).toBeDefined();
        expect(initEvent.environment).toBe('development');
      });
    });

    it('should not initialize dataLayer when disabled', async () => {
      global.window.dataLayer = undefined;

      render(
        <GTMProvider enabled={false}>
          <TestComponent />
        </GTMProvider>
      );

      // Wait a bit to ensure no initialization happens
      await new Promise(resolve => setTimeout(resolve, 100));
      
      expect(window.dataLayer).toBeUndefined();
    });

    it('should not reinitialize existing dataLayer', async () => {
      const existingDataLayer = [{ existing: 'event' }];
      window.dataLayer = existingDataLayer;

      render(
        <GTMProvider enabled={true}>
          <TestComponent />
        </GTMProvider>
      );

      await waitFor(() => {
        // Should still have the existing event
        expect(window.dataLayer[0]).toEqual({ existing: 'event' });
        expect(window.dataLayer.length).toBe(1);
      });
    });
  });

  describe('Script Loading', () => {
        setupAntiHang();
      jest.setTimeout(10000);
    it('should render GTM script when enabled', async () => {
      render(
        <GTMProvider enabled={true}>
          <TestComponent />
        </GTMProvider>
      );

      const script = screen.getByTestId('gtm-script');
      expect(script).toBeInTheDocument();
      expect(script).toHaveAttribute('src', 'https://www.googletagmanager.com/gtm.js?id=GTM-WKP28PNQ');
    });

    it('should not render GTM script when disabled', () => {
      render(
        <GTMProvider enabled={false}>
          <TestComponent />
        </GTMProvider>
      );

      expect(screen.queryByTestId('gtm-script')).not.toBeInTheDocument();
    });

    it('should handle script load success', async () => {
      let contextValue: any;

      render(
        <GTMProvider enabled={true}>
          <TestComponent onContextReady={(ctx) => { contextValue = ctx; }} />
        </GTMProvider>
      );

      await waitFor(() => {
        expect(screen.getByTestId('gtm-loaded')).toHaveTextContent('loaded');
        expect(contextValue.isLoaded).toBe(true);
      });
    });

    it('should render noscript fallback when enabled', () => {
      const { container } = render(
        <GTMProvider enabled={true}>
          <TestComponent />
        </GTMProvider>
      );

      const noscript = container.querySelector('noscript');
      expect(noscript).toBeInTheDocument();
      
      const iframe = noscript?.querySelector('iframe');
      expect(iframe).toHaveAttribute('src', 'https://www.googletagmanager.com/ns.html?id=GTM-WKP28PNQ');
    });
  });

  describe('Event Tracking', () => {
        setupAntiHang();
      jest.setTimeout(10000);
    it('should push events to dataLayer when loaded', async () => {
      const testEvent: GTMEventData = {
        event: 'test_event',
        event_category: 'testing',
        event_action: 'unit_test'
      };

      render(
        <GTMProvider enabled={true}>
          <TestComponent eventToTrack={testEvent} />
        </GTMProvider>
      );

      await waitFor(() => {
        expect(screen.getByTestId('gtm-loaded')).toHaveTextContent('loaded');
      });

      await waitFor(() => {
        const pushedEvent = window.dataLayer.find((item: any) => item.event === 'test_event');
        expect(pushedEvent).toBeDefined();
        expect(pushedEvent.event_category).toBe('testing');
        expect(pushedEvent.event_action).toBe('unit_test');
        expect(pushedEvent.timestamp).toBeDefined();
        expect(pushedEvent.environment).toBe('development');
        expect(pushedEvent.page_path).toBe('/test-path');
      });
    });

    it('should update debug state when events are pushed', async () => {
      const testEvent: GTMEventData = {
        event: 'debug_test',
        event_category: 'testing'
      };

      render(
        <GTMProvider enabled={true}>
          <TestComponent eventToTrack={testEvent} />
        </GTMProvider>
      );

      await waitFor(() => {
        expect(screen.getByTestId('gtm-loaded')).toHaveTextContent('loaded');
      });

      await waitFor(() => {
        expect(screen.getByTestId('total-events')).toHaveTextContent('1');
      });
    });

    it('should handle event push when GTM is disabled', async () => {
      const consoleSpy = jest.spyOn(console, 'warn').mockImplementation();
      
      const testEvent: GTMEventData = {
        event: 'disabled_test',
        event_category: 'testing'
      };

      render(
        <GTMProvider enabled={false} config={{ debug: true }}>
          <TestComponent eventToTrack={testEvent} />
        </GTMProvider>
      );

      // Event should not be pushed
      expect(window.dataLayer.find((item: any) => item.event === 'disabled_test')).toBeUndefined();
      
      consoleSpy.mockRestore();
    });

    it('should validate required event properties', async () => {
      let contextValue: any;

      render(
        <GTMProvider enabled={true}>
          <TestComponent onContextReady={(ctx) => { contextValue = ctx; }} />
        </GTMProvider>
      );

      await waitFor(() => {
        expect(contextValue.isLoaded).toBe(true);
      });

      // Try to push event without required 'event' property
      act(() => {
        contextValue.pushEvent({ event_category: 'test' } as GTMEventData);
      });

      await waitFor(() => {
        expect(contextValue.debug.errors.length).toBeGreaterThan(0);
        expect(contextValue.debug.errors[0]).toContain('Event data must include an "event" property');
      });
    });
  });

  describe('Data Pushing', () => {
        setupAntiHang();
      jest.setTimeout(10000);
    it('should push arbitrary data to dataLayer', async () => {
      let contextValue: any;

      render(
        <GTMProvider enabled={true}>
          <TestComponent onContextReady={(ctx) => { contextValue = ctx; }} />
        </GTMProvider>
      );

      await waitFor(() => {
        expect(contextValue.isLoaded).toBe(true);
      });

      const testData = { custom_property: 'test_value', user_id: '12345' };

      act(() => {
        contextValue.pushData(testData);
      });

      await waitFor(() => {
        const pushedData = window.dataLayer.find((item: any) => item.custom_property === 'test_value');
        expect(pushedData).toBeDefined();
        expect(pushedData.user_id).toBe('12345');
      });
    });
  });

  describe('Debug Functionality', () => {
        setupAntiHang();
      jest.setTimeout(10000);
    it('should track debug information', async () => {
      let contextValue: any;

      render(
        <GTMProvider enabled={true} config={{ debug: true }}>
          <TestComponent onContextReady={(ctx) => { contextValue = ctx; }} />
        </GTMProvider>
      );

      await waitFor(() => {
        expect(contextValue.isLoaded).toBe(true);
        expect(contextValue.debug).toBeDefined();
        expect(contextValue.debug.lastEvents).toEqual([]);
        expect(contextValue.debug.totalEvents).toBe(0);
        expect(contextValue.debug.errors).toEqual([]);
      });
    });

    it('should provide dataLayer access', async () => {
      let contextValue: any;

      render(
        <GTMProvider enabled={true}>
          <TestComponent onContextReady={(ctx) => { contextValue = ctx; }} />
        </GTMProvider>
      );

      await waitFor(() => {
        expect(contextValue.isLoaded).toBe(true);
      });

      const dataLayerCopy = contextValue.getDataLayer();
      expect(Array.isArray(dataLayerCopy)).toBe(true);
      expect(dataLayerCopy.length).toBeGreaterThanOrEqual(0);
    });
  });

  describe('Error Handling', () => {
        setupAntiHang();
      jest.setTimeout(10000);
    it('should handle dataLayer initialization errors', async () => {
      // Mock Object.defineProperty to throw an error
      const originalDefineProperty = Object.defineProperty;
      Object.defineProperty = jest.fn().mockImplementation(() => {
        throw new Error('Cannot define property');
      });

      let contextValue: any;

      render(
        <GTMProvider enabled={true}>
          <TestComponent onContextReady={(ctx) => { contextValue = ctx; }} />
        </GTMProvider>
      );

      await waitFor(() => {
        expect(contextValue.debug.errors.length).toBeGreaterThan(0);
      });

      // Restore original
      Object.defineProperty = originalDefineProperty;
    });

    it('should throw error when useGTMContext is used outside provider', () => {
      const consoleSpy = jest.spyOn(console, 'error').mockImplementation();

      expect(() => {
        render(<TestComponent />);
      }).toThrow('useGTMContext must be used within a GTMProvider');

      consoleSpy.mockRestore();
    });
  });

  describe('SSR Compatibility', () => {
        setupAntiHang();
      jest.setTimeout(10000);
    it('should handle server-side rendering', () => {
      const originalWindow = global.window;
      // @ts-ignore
      delete global.window;

      expect(() => {
        render(
          <GTMProvider enabled={true}>
            <TestComponent />
          </GTMProvider>
        );
      }).not.toThrow();

      global.window = originalWindow;
    });
  });
});