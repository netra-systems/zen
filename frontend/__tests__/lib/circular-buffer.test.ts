import { CircularBuffer, WebSocketEventBuffer, WSEvent } from '@/lib/circular-buffer';

describe('CircularBuffer', () => {
      setupAntiHang();
    jest.setTimeout(10000);
  describe('Basic operations', () => {
        setupAntiHang();
      jest.setTimeout(10000);
    it('should create a buffer with specified size', () => {
      const buffer = new CircularBuffer<number>(5);
      expect(buffer.size()).toBe(0);
      expect(buffer.isEmpty()).toBe(true);
      expect(buffer.isFull()).toBe(false);
    });

    it('should throw error for invalid size', () => {
      expect(() => new CircularBuffer(0)).toThrow('CircularBuffer maxSize must be greater than 0');
      expect(() => new CircularBuffer(-1)).toThrow('CircularBuffer maxSize must be greater than 0');
    });

    it('should add items to buffer', () => {
      const buffer = new CircularBuffer<number>(3);
      
      buffer.push(1);
      expect(buffer.size()).toBe(1);
      expect(buffer.getAll()).toEqual([1]);
      
      buffer.push(2);
      expect(buffer.size()).toBe(2);
      expect(buffer.getAll()).toEqual([1, 2]);
      
      buffer.push(3);
      expect(buffer.size()).toBe(3);
      expect(buffer.getAll()).toEqual([1, 2, 3]);
      expect(buffer.isFull()).toBe(true);
    });

    it('should overwrite oldest items when full', () => {
      const buffer = new CircularBuffer<number>(3);
      
      buffer.push(1);
      buffer.push(2);
      buffer.push(3);
      buffer.push(4); // Overwrites 1
      
      expect(buffer.size()).toBe(3);
      expect(buffer.getAll()).toEqual([2, 3, 4]);
      
      buffer.push(5); // Overwrites 2
      expect(buffer.getAll()).toEqual([3, 4, 5]);
    });

    it('should get last N items', () => {
      const buffer = new CircularBuffer<number>(5);
      
      buffer.push(1);
      buffer.push(2);
      buffer.push(3);
      buffer.push(4);
      buffer.push(5);
      
      expect(buffer.getLast(2)).toEqual([4, 5]);
      expect(buffer.getLast(3)).toEqual([3, 4, 5]);
      expect(buffer.getLast(10)).toEqual([1, 2, 3, 4, 5]);
      expect(buffer.getLast(0)).toEqual([]);
      expect(buffer.getLast(-1)).toEqual([]);
    });

    it('should filter items', () => {
      const buffer = new CircularBuffer<number>(5);
      
      buffer.push(1);
      buffer.push(2);
      buffer.push(3);
      buffer.push(4);
      buffer.push(5);
      
      expect(buffer.filter(n => n % 2 === 0)).toEqual([2, 4]);
      expect(buffer.filter(n => n > 3)).toEqual([4, 5]);
      expect(buffer.filter(n => n < 0)).toEqual([]);
    });

    it('should clear buffer', () => {
      const buffer = new CircularBuffer<number>(3);
      
      buffer.push(1);
      buffer.push(2);
      buffer.push(3);
      
      expect(buffer.size()).toBe(3);
      
      buffer.clear();
      
      expect(buffer.size()).toBe(0);
      expect(buffer.isEmpty()).toBe(true);
      expect(buffer.getAll()).toEqual([]);
    });

    it('should provide statistics', () => {
      const buffer = new CircularBuffer<number>(4);
      
      buffer.push(1);
      buffer.push(2);
      
      const stats = buffer.getStats();
      
      expect(stats.size).toBe(2);
      expect(stats.maxSize).toBe(4);
      expect(stats.utilization).toBe(50);
      expect(stats.isFull).toBe(false);
      
      buffer.push(3);
      buffer.push(4);
      
      const fullStats = buffer.getStats();
      expect(fullStats.utilization).toBe(100);
      expect(fullStats.isFull).toBe(true);
    });
  });

  describe('Edge cases', () => {
        setupAntiHang();
      jest.setTimeout(10000);
    it('should handle single item buffer', () => {
      const buffer = new CircularBuffer<string>(1);
      
      buffer.push('a');
      expect(buffer.getAll()).toEqual(['a']);
      
      buffer.push('b');
      expect(buffer.getAll()).toEqual(['b']);
      
      buffer.push('c');
      expect(buffer.getAll()).toEqual(['c']);
    });

    it('should handle complex objects', () => {
      interface User {
        id: number;
        name: string;
        data?: any;
      }
      
      const buffer = new CircularBuffer<User>(3);
      
      buffer.push({ id: 1, name: 'Alice' });
      buffer.push({ id: 2, name: 'Bob', data: { age: 30 } });
      buffer.push({ id: 3, name: 'Charlie' });
      
      const all = buffer.getAll();
      expect(all).toHaveLength(3);
      expect(all[0].name).toBe('Alice');
      expect(all[1].data?.age).toBe(30);
    });

    it('should maintain order after wrapping', () => {
      const buffer = new CircularBuffer<number>(3);
      
      // Fill and wrap
      for (let i = 1; i <= 10; i++) {
        buffer.push(i);
      }
      
      // Should have last 3 items in order
      expect(buffer.getAll()).toEqual([8, 9, 10]);
    });

    it('should handle rapid push operations', () => {
      const buffer = new CircularBuffer<number>(100);
      
      for (let i = 0; i < 1000; i++) {
        buffer.push(i);
      }
      
      expect(buffer.size()).toBe(100);
      expect(buffer.isFull()).toBe(true);
      
      const all = buffer.getAll();
      expect(all).toHaveLength(100);
      expect(all[0]).toBe(900);
      expect(all[99]).toBe(999);
    });

    it('should handle getLast with empty buffer', () => {
      const buffer = new CircularBuffer<number>(5);
      
      expect(buffer.getLast(3)).toEqual([]);
    });

    it('should handle filter with empty buffer', () => {
      const buffer = new CircularBuffer<number>(5);
      
      expect(buffer.filter(n => n > 0)).toEqual([]);
    });

    it('should correctly report empty and full states', () => {
      const buffer = new CircularBuffer<string>(2);
      
      expect(buffer.isEmpty()).toBe(true);
      expect(buffer.isFull()).toBe(false);
      
      buffer.push('a');
      expect(buffer.isEmpty()).toBe(false);
      expect(buffer.isFull()).toBe(false);
      
      buffer.push('b');
      expect(buffer.isEmpty()).toBe(false);
      expect(buffer.isFull()).toBe(true);
      
      buffer.clear();
      expect(buffer.isEmpty()).toBe(true);
      expect(buffer.isFull()).toBe(false);
    });
  });

  describe('Performance', () => {
        setupAntiHang();
      jest.setTimeout(10000);
    it('should handle large buffers efficiently', () => {
      const buffer = new CircularBuffer<number>(10000);
      const startTime = performance.now();
      
      for (let i = 0; i < 100000; i++) {
        buffer.push(i);
      }
      
      const endTime = performance.now();
      const duration = endTime - startTime;
      
      // Should complete in reasonable time (< 100ms)
      expect(duration).toBeLessThan(100);
      expect(buffer.size()).toBe(10000);
    });

    it('should filter large buffers efficiently', () => {
      const buffer = new CircularBuffer<number>(1000);
      
      for (let i = 0; i < 1000; i++) {
        buffer.push(i);
      }
      
      const startTime = performance.now();
      const evens = buffer.filter(n => n % 2 === 0);
      const endTime = performance.now();
      
      expect(evens).toHaveLength(500);
      expect(endTime - startTime).toBeLessThan(10);
    });
  });
});

describe('WebSocketEventBuffer', () => {
      setupAntiHang();
    jest.setTimeout(10000);
  const createMockEvent = (
    type: string,
    agentName?: string,
    timestamp?: number
  ): WSEvent => ({
    type,
    payload: { test: true },
    timestamp: timestamp || Date.now(),
    source: 'test',
    threadId: 'thread-1',
    runId: 'run-1',
    agentName
  });

  describe('Specialized WebSocket operations', () => {
        setupAntiHang();
      jest.setTimeout(10000);
    it('should filter events by type', () => {
      const buffer = new WebSocketEventBuffer(10);
      
      buffer.push(createMockEvent('connect'));
      buffer.push(createMockEvent('message'));
      buffer.push(createMockEvent('error'));
      buffer.push(createMockEvent('message'));
      buffer.push(createMockEvent('disconnect'));
      
      const messages = buffer.getByType('message');
      expect(messages).toHaveLength(2);
      expect(messages.every(e => e.type === 'message')).toBe(true);
    });

    it('should filter events by agent', () => {
      const buffer = new WebSocketEventBuffer(10);
      
      buffer.push(createMockEvent('message', 'agent1'));
      buffer.push(createMockEvent('message', 'agent2'));
      buffer.push(createMockEvent('message', 'agent1'));
      buffer.push(createMockEvent('message', 'agent3'));
      
      const agent1Events = buffer.getByAgent('agent1');
      expect(agent1Events).toHaveLength(2);
      expect(agent1Events.every(e => e.agentName === 'agent1')).toBe(true);
    });

    it('should filter events by time range', () => {
      const buffer = new WebSocketEventBuffer(10);
      const now = Date.now();
      
      buffer.push(createMockEvent('event1', undefined, now - 5000));
      buffer.push(createMockEvent('event2', undefined, now - 3000));
      buffer.push(createMockEvent('event3', undefined, now - 1000));
      buffer.push(createMockEvent('event4', undefined, now));
      
      const recentEvents = buffer.getByTimeRange(now - 2000, now);
      expect(recentEvents).toHaveLength(2);
      expect(recentEvents[0].type).toBe('event3');
      expect(recentEvents[1].type).toBe('event4');
    });

    it('should calculate type statistics', () => {
      const buffer = new WebSocketEventBuffer(10);
      
      buffer.push(createMockEvent('connect'));
      buffer.push(createMockEvent('message'));
      buffer.push(createMockEvent('message'));
      buffer.push(createMockEvent('error'));
      buffer.push(createMockEvent('message'));
      buffer.push(createMockEvent('disconnect'));
      
      const stats = buffer.getTypeStats();
      
      expect(stats.get('connect')).toBe(1);
      expect(stats.get('message')).toBe(3);
      expect(stats.get('error')).toBe(1);
      expect(stats.get('disconnect')).toBe(1);
    });

    it('should export as JSON', () => {
      const buffer = new WebSocketEventBuffer(5);
      
      buffer.push(createMockEvent('connect'));
      buffer.push(createMockEvent('message', 'agent1'));
      buffer.push(createMockEvent('error'));
      
      const json = buffer.exportAsJSON();
      const exported = JSON.parse(json);
      
      expect(exported.events).toHaveLength(3);
      expect(exported.stats.size).toBe(3);
      expect(exported.stats.maxSize).toBe(5);
      expect(exported.typeStats).toHaveLength(3);
      expect(exported.exportedAt).toBeDefined();
    });

    it('should handle empty buffer export', () => {
      const buffer = new WebSocketEventBuffer(5);
      
      const json = buffer.exportAsJSON();
      const exported = JSON.parse(json);
      
      expect(exported.events).toHaveLength(0);
      expect(exported.stats.size).toBe(0);
      expect(exported.typeStats).toHaveLength(0);
    });

    it('should maintain WebSocket event order', () => {
      const buffer = new WebSocketEventBuffer(3);
      const now = Date.now();
      
      for (let i = 0; i < 10; i++) {
        buffer.push(createMockEvent(`event${i}`, undefined, now + i * 1000));
      }
      
      const all = buffer.getAll();
      expect(all).toHaveLength(3);
      expect(all[0].type).toBe('event7');
      expect(all[1].type).toBe('event8');
      expect(all[2].type).toBe('event9');
    });

    it('should handle complex event filtering', () => {
      const buffer = new WebSocketEventBuffer(20);
      const now = Date.now();
      
      // Add various events
      for (let i = 0; i < 20; i++) {
        buffer.push(createMockEvent(
          i % 3 === 0 ? 'error' : 'message',
          `agent${i % 4}`,
          now + i * 100
        ));
      }
      
      // Complex filter: recent errors from specific agent
      const recentErrors = buffer.getByTimeRange(now + 1000, now + 2000)
        .filter(e => e.type === 'error' && e.agentName === 'agent0');
      
      expect(recentErrors.length).toBeGreaterThan(0);
      expect(recentErrors.every(e => 
        e.type === 'error' && 
        e.agentName === 'agent0' &&
        e.timestamp >= now + 1000 &&
        e.timestamp <= now + 2000
      )).toBe(true);
    });

    it('should handle high-frequency WebSocket events', () => {
      const buffer = new WebSocketEventBuffer(1000);
      const startTime = performance.now();
      
      // Simulate high-frequency events
      for (let i = 0; i < 10000; i++) {
        buffer.push(createMockEvent(
          ['connect', 'message', 'ping', 'pong', 'error'][i % 5],
          `agent${i % 10}`
        ));
      }
      
      const endTime = performance.now();
      
      // Should handle 10k events quickly
      expect(endTime - startTime).toBeLessThan(50);
      
      // Should maintain correct statistics
      const stats = buffer.getTypeStats();
      expect(stats.get('message')).toBe(200); // 1000 events, 20% are 'message'
      expect(stats.get('ping')).toBe(200);
      
      // Should filter efficiently
      const agent0Events = buffer.getByAgent('agent0');
      expect(agent0Events).toHaveLength(100); // 10% of 1000
    });
  });

  describe('Edge cases for WebSocketEventBuffer', () => {
        setupAntiHang();
      jest.setTimeout(10000);
    it('should handle events with missing optional fields', () => {
      const buffer = new WebSocketEventBuffer(5);
      
      const minimalEvent: WSEvent = {
        type: 'minimal',
        payload: null,
        timestamp: Date.now()
      };
      
      buffer.push(minimalEvent);
      expect(buffer.size()).toBe(1);
      
      const byAgent = buffer.getByAgent('nonexistent');
      expect(byAgent).toHaveLength(0);
    });

    it('should handle concurrent-like event additions', () => {
      const buffer = new WebSocketEventBuffer(100);
      const events: WSEvent[] = [];
      
      // Simulate concurrent-like additions
      for (let i = 0; i < 100; i++) {
        const event = createMockEvent(`event${i}`);
        events.push(event);
        buffer.push(event);
      }
      
      const allEvents = buffer.getAll();
      expect(allEvents).toHaveLength(100);
      
      // Verify order is maintained
      for (let i = 0; i < 100; i++) {
        expect(allEvents[i].type).toBe(`event${i}`);
      }
    });

    it('should handle export with special characters in payload', () => {
      const buffer = new WebSocketEventBuffer(5);
      
      buffer.push({
        type: 'special',
        payload: {
          text: 'Special "chars" & symbols: <>\n\t',
          unicode: '😀🎉',
          nested: { deep: { value: true } }
        },
        timestamp: Date.now()
      });
      
      const json = buffer.exportAsJSON();
      expect(() => JSON.parse(json)).not.toThrow();
      
      const exported = JSON.parse(json);
      expect(exported.events[0].payload.text).toContain('Special "chars"');
      expect(exported.events[0].payload.unicode).toBe('😀🎉');
    });
  });
  afterEach(() => {
    cleanupAntiHang();
  });

});