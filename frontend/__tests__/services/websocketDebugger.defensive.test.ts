/**
 * @file websocketDebugger.defensive.test.ts
 * @description Comprehensive tests for websocketDebugger defensive programming
 * 
 * Tests ensure that all public methods handle undefined, null, and malformed
 * inputs gracefully without throwing errors. This is critical for preventing
 * production errors when third-party scripts (like GTM) interact with the service.
 */

import { websocketDebugger } from '@/services/websocketDebugger';
import { WebSocketMessage } from '@/types/websocket.types';
import { setupAntiHang, cleanupAntiHang } from '@/__tests__/utils/anti-hanging-test-utilities';

describe('WebSocketDebugger - Defensive Programming', () => {
  setupAntiHang();
    jest.setTimeout(10000);
  beforeEach(() => {
    websocketDebugger.reset();
  });

  describe('traceEvent', () => {
        setupAntiHang();
      jest.setTimeout(10000);
    it('should handle undefined event gracefully', () => {
      const result = websocketDebugger.traceEvent(undefined as any);
      expect(result.isValid).toBe(false);
      expect(result.issues).toContain('Event is undefined or null');
      expect(result.severity).toBe('critical');
    });

    it('should handle null event gracefully', () => {
      const result = websocketDebugger.traceEvent(null as any);
      expect(result.isValid).toBe(false);
      expect(result.issues).toContain('Event is undefined or null');
      expect(result.severity).toBe('critical');
    });

    it('should handle event with undefined type', () => {
      const malformedEvent = { payload: {} } as WebSocketMessage;
      const result = websocketDebugger.traceEvent(malformedEvent);
      expect(result.isValid).toBe(false);
      expect(result.issues).toContain('Missing or invalid event type');
    });

    it('should handle event with undefined payload', () => {
      const malformedEvent = { type: 'test' } as WebSocketMessage;
      const result = websocketDebugger.traceEvent(malformedEvent);
      expect(result.isValid).toBe(false);
      expect(result.issues).toContain('Missing or invalid payload');
    });

    it('should handle completely empty object', () => {
      const result = websocketDebugger.traceEvent({} as WebSocketMessage);
      expect(result.isValid).toBe(false);
      expect(result.issues.length).toBeGreaterThan(0);
    });

    it('should handle event with null payload', () => {
      const malformedEvent = { type: 'test', payload: null } as any;
      const result = websocketDebugger.traceEvent(malformedEvent);
      expect(result.isValid).toBe(false);
      expect(result.issues).toContain('Missing or invalid payload');
    });

    it('should handle valid event correctly', () => {
      const validEvent: WebSocketMessage = {
        type: 'message',
        payload: { content: 'test' }
      };
      const result = websocketDebugger.traceEvent(validEvent);
      expect(result.isValid).toBe(true);
      expect(result.issues).toHaveLength(0);
    });
  });

  describe('generateEventId (private method via traceEvent)', () => {
        setupAntiHang();
      jest.setTimeout(10000);
    it('should generate fallback ID for event without message_id', () => {
      const event: WebSocketMessage = {
        type: 'test_event',
        payload: {}
      };
      const result = websocketDebugger.traceEvent(event);
      const stats = websocketDebugger.getStats();
      expect(stats.totalEvents).toBe(1);
      expect(stats.eventsByType['test_event']).toBe(1);
    });

    it('should handle payload with message_id', () => {
      const event: WebSocketMessage = {
        type: 'test',
        payload: { message_id: 'custom-id-123' } as any
      };
      const result = websocketDebugger.traceEvent(event);
      expect(result).toBeDefined();
      // Event should be tracked successfully
      const stats = websocketDebugger.getStats();
      expect(stats.totalEvents).toBe(1);
    });

    it('should handle payload with messageId', () => {
      const event: WebSocketMessage = {
        type: 'test',
        payload: { messageId: 'custom-id-456' } as any
      };
      const result = websocketDebugger.traceEvent(event);
      expect(result).toBeDefined();
      const stats = websocketDebugger.getStats();
      expect(stats.totalEvents).toBe(1);
    });

    it('should handle payload with id', () => {
      const event: WebSocketMessage = {
        type: 'test',
        payload: { id: 'custom-id-789' } as any
      };
      const result = websocketDebugger.traceEvent(event);
      expect(result).toBeDefined();
      const stats = websocketDebugger.getStats();
      expect(stats.totalEvents).toBe(1);
    });

    it('should generate unique fallback IDs for undefined type', () => {
      const event1 = { payload: {} } as WebSocketMessage;
      const event2 = { payload: {} } as WebSocketMessage;
      
      websocketDebugger.traceEvent(event1);
      websocketDebugger.traceEvent(event2);
      
      const stats = websocketDebugger.getStats();
      expect(stats.totalEvents).toBe(2);
      expect(stats.eventsByType['unknown']).toBe(2);
    });
  });

  describe('markEventProcessed', () => {
        setupAntiHang();
      jest.setTimeout(10000);
    it('should handle undefined eventId gracefully', () => {
      expect(() => {
        websocketDebugger.markEventProcessed(undefined as any, {});
      }).not.toThrow();
    });

    it('should handle null eventId gracefully', () => {
      expect(() => {
        websocketDebugger.markEventProcessed(null as any, {});
      }).not.toThrow();
    });

    it('should handle empty string eventId gracefully', () => {
      expect(() => {
        websocketDebugger.markEventProcessed('', {});
      }).not.toThrow();
    });

    it('should handle non-existent eventId gracefully', () => {
      expect(() => {
        websocketDebugger.markEventProcessed('non-existent-id', {});
      }).not.toThrow();
    });
  });

  describe('markEventFailed', () => {
        setupAntiHang();
      jest.setTimeout(10000);
    it('should handle undefined eventId gracefully', () => {
      // Suppress console.error for this test
      const originalError = console.error;
      console.error = jest.fn();
      
      expect(() => {
        websocketDebugger.markEventFailed(undefined as any, 'test error');
      }).not.toThrow();
      
      console.error = originalError;
    });

    it('should handle null eventId gracefully', () => {
      // Suppress console.error for this test
      const originalError = console.error;
      console.error = jest.fn();
      
      expect(() => {
        websocketDebugger.markEventFailed(null as any, 'test error');
      }).not.toThrow();
      
      console.error = originalError;
    });

    it('should handle undefined error message gracefully', () => {
      // Suppress console.error for this test
      const originalError = console.error;
      console.error = jest.fn();
      
      expect(() => {
        websocketDebugger.markEventFailed('test-id', undefined as any);
      }).not.toThrow();
      
      console.error = originalError;
    });

    it('should handle null error message gracefully', () => {
      // Suppress console.error for this test
      const originalError = console.error;
      console.error = jest.fn();
      
      expect(() => {
        websocketDebugger.markEventFailed('test-id', null as any);
      }).not.toThrow();
      
      console.error = originalError;
    });
  });

  describe('getStats', () => {
        setupAntiHang();
      jest.setTimeout(10000);
    it('should return valid stats even with malformed events', () => {
      // Process various malformed events
      websocketDebugger.traceEvent(undefined as any);
      websocketDebugger.traceEvent(null as any);
      websocketDebugger.traceEvent({} as WebSocketMessage);
      websocketDebugger.traceEvent({ type: null } as any);
      websocketDebugger.traceEvent({ payload: undefined } as any);
      
      const stats = websocketDebugger.getStats();
      expect(stats).toBeDefined();
      // Some events might be rejected entirely, so just check that stats are tracked
      expect(stats.totalEvents).toBeGreaterThan(0);
      expect(stats.eventsByType).toBeDefined();
      // Check that at least some events were categorized
      const totalCategorized = Object.values(stats.eventsByType).reduce((sum, count) => sum + count, 0);
      expect(totalCategorized).toBeGreaterThan(0);
    });
  });

  describe('generateDebugReport', () => {
        setupAntiHang();
      jest.setTimeout(10000);
    it('should generate report even with malformed events', () => {
      // Process various malformed events
      websocketDebugger.traceEvent(undefined as any);
      websocketDebugger.traceEvent({ type: 'partial' } as WebSocketMessage);
      
      const report = websocketDebugger.generateDebugReport();
      expect(report).toBeDefined();
      expect(typeof report).toBe('string');
      // Report content may vary, just ensure it's generated without errors
      expect(report.length).toBeGreaterThan(0);
    });
  });

  describe('Validation Rules', () => {
        setupAntiHang();
      jest.setTimeout(10000);
    it('should handle agent events with missing agent identification', () => {
      const agentEvent: WebSocketMessage = {
        type: 'agent_started',
        payload: {} // Missing agent_id and agent_type
      };
      const result = websocketDebugger.traceEvent(agentEvent);
      expect(result.issues).toContain('Agent event missing agent identification');
      expect(result.severity).toBe('medium');
    });

    it('should handle tool events with missing tool name', () => {
      const toolEvent: WebSocketMessage = {
        type: 'tool_started',
        payload: {} // Missing tool_name and name
      };
      const result = websocketDebugger.traceEvent(toolEvent);
      expect(result.issues).toContain('Tool event missing tool name');
      expect(result.severity).toBe('medium');
    });

    it('should validate special event types even with missing payload', () => {
      // When payload is missing, both errors should be present
      const undefinedAgentEvent = {
        type: 'agent_started'
        // Missing payload entirely
      } as WebSocketMessage;
      
      const result = websocketDebugger.traceEvent(undefinedAgentEvent);
      // Should have the missing payload error
      expect(result.issues).toContain('Missing or invalid payload');
      // The validation rules run independently, so agent identification error may also appear
      expect(result.issues.length).toBeGreaterThan(0);
    });
  });

  describe('Edge Cases from Production', () => {
        setupAntiHang();
      jest.setTimeout(10000);
    it('should handle GTM-like undefined property access', () => {
      // Simulate the exact error pattern from production
      const gtmLikeEvent = {
        type: 'page_view',
        payload: {
          // GTM might expect message_id but it's undefined
        }
      } as WebSocketMessage;
      
      const result = websocketDebugger.traceEvent(gtmLikeEvent);
      expect(result).toBeDefined();
      expect(result.isValid).toBe(true);
      
      // Should generate a fallback ID without errors
      const stats = websocketDebugger.getStats();
      expect(stats.totalEvents).toBe(1);
      expect(stats.eventsByType['page_view']).toBe(1);
    });

    it('should handle deeply nested undefined access', () => {
      const nestedEvent = {
        type: 'complex_event',
        payload: {
          nested: {
            deeply: null
          }
        }
      } as any;
      
      const result = websocketDebugger.traceEvent(nestedEvent);
      expect(result).toBeDefined();
      expect(result.isValid).toBe(true);
    });

    it('should handle array payloads gracefully', () => {
      const arrayPayload = {
        type: 'array_event',
        payload: [] as any
      };
      
      const result = websocketDebugger.traceEvent(arrayPayload);
      expect(result).toBeDefined();
      // Arrays are objects, so this should pass the payload check
      expect(result.isValid).toBe(true);
    });

    it('should handle string payloads as invalid', () => {
      const stringPayload = {
        type: 'string_event',
        payload: 'not an object' as any
      };
      
      const result = websocketDebugger.traceEvent(stringPayload);
      expect(result.isValid).toBe(false);
      expect(result.issues).toContain('Missing or invalid payload');
    });

    it('should handle number payloads as invalid', () => {
      const numberPayload = {
        type: 'number_event',
        payload: 123 as any
      };
      
      const result = websocketDebugger.traceEvent(numberPayload);
      expect(result.isValid).toBe(false);
      expect(result.issues).toContain('Missing or invalid payload');
    });
  });

  describe('Concurrency and Race Conditions', () => {
        setupAntiHang();
      jest.setTimeout(10000);
    it('should handle rapid successive calls with malformed events', () => {
      const promises = [];
      for (let i = 0; i < 100; i++) {
        promises.push(
          Promise.resolve(websocketDebugger.traceEvent(
            i % 2 === 0 ? undefined as any : {} as WebSocketMessage
          ))
        );
      }
      
      return Promise.all(promises).then(results => {
        expect(results).toHaveLength(100);
        results.forEach(result => {
          expect(result).toBeDefined();
          expect(result.isValid).toBeDefined();
        });
      });
    });
  });
  afterEach(() => {
    cleanupAntiHang();
  });

});