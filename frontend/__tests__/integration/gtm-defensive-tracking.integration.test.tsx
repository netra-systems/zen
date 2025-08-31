/**
 * GTM Defensive Tracking Integration Tests
 * 
 * Integration tests to verify that GTM event tracking handles
 * undefined properties gracefully and prevents runtime errors.
 */

import React from 'react';
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
import '@testing-library/jest-dom';
import { GTMProvider } from '../../providers/GTMProvider';
import { useGTMEvent } from '../../hooks/useGTMEvent';
import { useGTM } from '../../hooks/useGTM';
import { setupAntiHang, cleanupAntiHang } from '@/__tests__/utils/anti-hanging-test-utilities';

// Mock logger to prevent console noise during tests
jest.mock('../../lib/logger', () => ({
  logger: {
    debug: jest.fn(),
    info: jest.fn(),
    warn: jest.fn(),
    error: jest.fn()
  }
}));

// Mock circuit breaker
jest.mock('../../lib/gtm-circuit-breaker', () => ({
  getGTMCircuitBreaker: () => ({
    canSendEvent: jest.fn().mockReturnValue(true),
    recordEventSent: jest.fn(),
    recordEventFailure: jest.fn(),
    isOpen: jest.fn().mockReturnValue(false),
    getState: jest.fn().mockReturnValue({}),
    reset: jest.fn(),
    destroy: jest.fn()
  })
}));

// Test component that uses GTM hooks
const TestComponent = ({ 
  onEventPushed,
  testScenario 
}: { 
  onEventPushed?: (data: any) => void;
  testScenario?: string;
}) => {
  const gtmEvent = useGTMEvent();
  const gtm = useGTM();

  const handleTestScenario = () => {
    switch (testScenario) {
      case 'undefined-message':
        // Track message with undefined properties
        gtmEvent.trackMessageSent(undefined, undefined, undefined);
        break;
      
      case 'null-properties':
        // Track with null values
        gtmEvent.trackMessageSent(null as any, null as any, null as any);
        break;
      
      case 'nested-undefined':
        // Track custom event with nested undefined
        gtm.pushEvent({
          event: 'custom_test',
          custom_parameters: {
            level1: {
              level2: {
                value: undefined
              }
            }
          }
        } as any);
        break;
      
      case 'missing-message-id':
        // Direct push without message_id
        gtm.pushEvent({
          event: 'message_sent',
          event_category: 'engagement',
          thread_id: 'thread123'
          // message_id is missing
        } as any);
        break;
      
      case 'valid-message':
        // Track with valid data
        gtmEvent.trackMessageSent('thread123', 100, 'assistant', 'msg456');
        break;
      
      default:
        gtmEvent.trackChatStarted();
    }
  };

  return (
    <div>
      <button onClick={handleTestScenario}>Trigger Event</button>
      <div data-testid="gtm-status">
        {gtm.isEnabled ? 'GTM Enabled' : 'GTM Disabled'}
      </div>
    </div>
  );
};

describe('GTM Defensive Tracking Integration', () => {
  setupAntiHang();
    jest.setTimeout(10000);
  let originalDataLayer: any;
  let mockDataLayer: any[] = [];

  beforeEach(() => {
    // Save original dataLayer
    originalDataLayer = (global as any).window?.dataLayer;
    
    // Create mock dataLayer
    mockDataLayer = [];
    Object.defineProperty(window, 'dataLayer', {
      writable: true,
      value: mockDataLayer
    });

    // Mock window.location
    Object.defineProperty(window, 'location', {
      writable: true,
      value: {
        pathname: '/test',
        href: 'http://localhost/test'
      }
    });
  });

  afterEach(() => {
    // Restore original dataLayer
    if (originalDataLayer !== undefined) {
      (global as any).window.dataLayer = originalDataLayer;
    }
    
    jest.clearAllMocks();
      // Clean up timers to prevent hanging
      jest.clearAllTimers();
      jest.useFakeTimers();
      jest.runOnlyPendingTimers();
      jest.useRealTimers();
      cleanupAntiHang();
  });

  describe('Undefined Property Handling', () => {
        setupAntiHang();
      jest.setTimeout(10000);
    it('should handle message events with all undefined properties', async () => {
      render(
        <GTMProvider enabled={true}>
          <TestComponent testScenario="undefined-message" />
        </GTMProvider>
      );

      const button = screen.getByText('Trigger Event');
      
      act(() => {
        fireEvent.click(button);
      });

      await waitFor(() => {
        expect(mockDataLayer.length).toBeGreaterThan(0);
      });

      // Find the message_sent event
      const messageEvent = mockDataLayer.find(item => item.event === 'message_sent');
      
      expect(messageEvent).toBeDefined();
      expect(messageEvent.thread_id).toBe('no-thread');
      expect(messageEvent.message_id).toBeTruthy(); // Should have generated ID
      expect(messageEvent.message_length).toBe(0);
      
      // Should not throw any errors
      expect(() => messageEvent.message_id.toString()).not.toThrow();
    });

    it('should handle null properties gracefully', async () => {
      render(
        <GTMProvider enabled={true}>
          <TestComponent testScenario="null-properties" />
        </GTMProvider>
      );

      const button = screen.getByText('Trigger Event');
      
      act(() => {
        fireEvent.click(button);
      });

      await waitFor(() => {
        expect(mockDataLayer.length).toBeGreaterThan(0);
      });

      const messageEvent = mockDataLayer.find(item => item.event === 'message_sent');
      
      expect(messageEvent).toBeDefined();
      expect(messageEvent.thread_id).toBe('no-thread');
      expect(messageEvent.message_id).toBeTruthy();
      expect(typeof messageEvent.message_id).toBe('string');
    });

    it('should sanitize nested undefined values', async () => {
      render(
        <GTMProvider enabled={true}>
          <TestComponent testScenario="nested-undefined" />
        </GTMProvider>
      );

      const button = screen.getByText('Trigger Event');
      
      act(() => {
        fireEvent.click(button);
      });

      await waitFor(() => {
        expect(mockDataLayer.length).toBeGreaterThan(0);
      });

      const customEvent = mockDataLayer.find(item => item.event === 'custom_test');
      
      expect(customEvent).toBeDefined();
      expect(customEvent.custom_parameters).toBeDefined();
      expect(customEvent.custom_parameters.level1).toBeDefined();
      expect(customEvent.custom_parameters.level1.level2).toBeDefined();
      expect(customEvent.custom_parameters.level1.level2.value).toBe('');
    });

    it('should add message_id to message events automatically', async () => {
      render(
        <GTMProvider enabled={true}>
          <TestComponent testScenario="missing-message-id" />
        </GTMProvider>
      );

      const button = screen.getByText('Trigger Event');
      
      act(() => {
        fireEvent.click(button);
      });

      await waitFor(() => {
        expect(mockDataLayer.length).toBeGreaterThan(0);
      });

      const messageEvent = mockDataLayer.find(item => item.event === 'message_sent');
      
      expect(messageEvent).toBeDefined();
      expect(messageEvent.message_id).toBeDefined();
      expect(messageEvent.message_id).toBe('no-message-id');
      expect(messageEvent.thread_id).toBe('thread123');
    });
  });

  describe('Valid Data Preservation', () => {
        setupAntiHang();
      jest.setTimeout(10000);
    it('should preserve valid data while sanitizing undefined', async () => {
      render(
        <GTMProvider enabled={true}>
          <TestComponent testScenario="valid-message" />
        </GTMProvider>
      );

      const button = screen.getByText('Trigger Event');
      
      act(() => {
        fireEvent.click(button);
      });

      await waitFor(() => {
        expect(mockDataLayer.length).toBeGreaterThan(0);
      });

      const messageEvent = mockDataLayer.find(item => item.event === 'message_sent');
      
      expect(messageEvent).toBeDefined();
      expect(messageEvent.thread_id).toBe('thread123');
      expect(messageEvent.message_length).toBe(100);
      expect(messageEvent.agent_type).toBe('assistant');
      expect(messageEvent.message_id).toContain('msg-'); // Should have timestamp suffix
    });
  });

  describe('Error Prevention', () => {
        setupAntiHang();
      jest.setTimeout(10000);
    it('should not throw errors when GTM tries to access undefined properties', async () => {
      const consoleErrorSpy = jest.spyOn(console, 'error').mockImplementation();
      
      render(
        <GTMProvider enabled={true}>
          <TestComponent testScenario="undefined-message" />
        </GTMProvider>
      );

      const button = screen.getByText('Trigger Event');
      
      act(() => {
        fireEvent.click(button);
      });

      await waitFor(() => {
        expect(mockDataLayer.length).toBeGreaterThan(0);
      });

      // Simulate GTM internal script accessing properties
      const messageEvent = mockDataLayer.find(item => item.event === 'message_sent');
      
      // These operations should not throw
      expect(() => {
        const id = messageEvent?.message_id;
        const threadId = messageEvent?.thread_id;
        const userId = messageEvent?.user_id || 'anonymous';
        const nested = messageEvent?.custom_parameters?.nested?.value;
      }).not.toThrow();

      // No console errors should have been logged
      expect(consoleErrorSpy).not.toHaveBeenCalled();
      
      consoleErrorSpy.mockRestore();
    });

    it('should handle rapid successive events without errors', async () => {
      const { rerender } = render(
        <GTMProvider enabled={true}>
          <TestComponent testScenario="undefined-message" />
        </GTMProvider>
      );

      const button = screen.getByText('Trigger Event');
      
      // Fire multiple events rapidly
      act(() => {
        for (let i = 0; i < 10; i++) {
          fireEvent.click(button);
        }
      });

      await waitFor(() => {
        expect(mockDataLayer.length).toBeGreaterThanOrEqual(10);
      });

      // All events should have required properties
      const messageEvents = mockDataLayer.filter(item => item.event === 'message_sent');
      
      messageEvents.forEach(event => {
        expect(event.message_id).toBeDefined();
        expect(event.thread_id).toBeDefined();
        expect(typeof event.message_id).toBe('string');
        expect(typeof event.thread_id).toBe('string');
      });
    });
  });

  describe('GTM State Management', () => {
        setupAntiHang();
      jest.setTimeout(10000);
    it('should maintain debug state with sanitized events', async () => {
      const TestDebugComponent = () => {
        const gtm = useGTM();
        
        return (
          <div>
            <div data-testid="total-events">{gtm.debug.totalEvents}</div>
            <div data-testid="last-events">{gtm.debug.lastEvents.length}</div>
          </div>
        );
      };

      render(
        <GTMProvider enabled={true} config={{ debug: true }}>
          <TestComponent testScenario="undefined-message" />
          <TestDebugComponent />
        </GTMProvider>
      );

      const button = screen.getByText('Trigger Event');
      
      act(() => {
        fireEvent.click(button);
      });

      await waitFor(() => {
        const totalEvents = screen.getByTestId('total-events');
        expect(totalEvents.textContent).toBe('1');
      });

      const lastEvents = screen.getByTestId('last-events');
      expect(parseInt(lastEvents.textContent || '0')).toBeGreaterThan(0);
    });
  });

  describe('Authentication Events', () => {
        setupAntiHang();
      jest.setTimeout(10000);
    it('should handle auth events with undefined user properties', async () => {
      const TestAuthComponent = () => {
        const gtmEvent = useGTMEvent();
        
        const handleLogin = () => {
          gtmEvent.trackLogin(undefined, undefined);
        };
        
        return <button onClick={handleLogin}>Login</button>;
      };

      render(
        <GTMProvider enabled={true}>
          <TestAuthComponent />
        </GTMProvider>
      );

      const button = screen.getByText('Login');
      
      act(() => {
        fireEvent.click(button);
      });

      await waitFor(() => {
        expect(mockDataLayer.length).toBeGreaterThan(0);
      });

      const loginEvent = mockDataLayer.find(item => item.event === 'user_login');
      
      expect(loginEvent).toBeDefined();
      expect(loginEvent.event_category).toBe('authentication');
      // Undefined values should be handled gracefully
      expect(() => loginEvent.is_new_user?.toString()).not.toThrow();
    });
  });

  describe('Conversion Events', () => {
        setupAntiHang();
      jest.setTimeout(10000);
    it('should preserve numeric values while sanitizing undefined', async () => {
      const TestConversionComponent = () => {
        const gtmEvent = useGTMEvent();
        
        const handlePayment = () => {
          gtmEvent.trackPaymentCompleted(99.99, 'TXN123', undefined);
        };
        
        return <button onClick={handlePayment}>Complete Payment</button>;
      };

      render(
        <GTMProvider enabled={true}>
          <TestConversionComponent />
        </GTMProvider>
      );

      const button = screen.getByText('Complete Payment');
      
      act(() => {
        fireEvent.click(button);
      });

      await waitFor(() => {
        expect(mockDataLayer.length).toBeGreaterThan(0);
      });

      const paymentEvent = mockDataLayer.find(item => item.event === 'payment_completed');
      
      expect(paymentEvent).toBeDefined();
      expect(paymentEvent.transaction_value).toBe(99.99);
      expect(paymentEvent.transaction_id).toBe('TXN123');
      expect(typeof paymentEvent.transaction_value).toBe('number');
      // Plan type should be sanitized but not break the event
      expect(paymentEvent.plan_type).toBeDefined();
    });
  });
});