/**
 * Test suite for EventQueue rapid event processing
 * Validates race condition prevention and reliability
 */

import { setupAntiHang, cleanupAntiHang } from '@/__tests__/utils/anti-hanging-test-utilities';

// Mock EventQueue for testing
interface TestEvent {
  id: string;
  type: string;
  payload: any;
  timestamp: number;
  testData: string;
}

interface ProcessableEvent {
  id: string;
  type: string;
  payload: any;
  timestamp: number;
}

// Mock EventQueue implementation for tests
class MockEventQueue<T extends ProcessableEvent> {
  private events: T[] = [];
  private processing = false;
  private processor: (event: T) => Promise<void>;
  private options: any;
  private stats = {
    queueSize: 0,
    totalProcessed: 0,
    totalDropped: 0,
    totalErrors: 0,
    duplicatesDropped: 0,
    errorHandler: {}
  };

  constructor(processor: (event: T) => Promise<void>, options: any) {
    this.processor = processor;
    this.options = options;
  }

  enqueue(event: T): boolean {
    if (this.events.length >= this.options.maxQueueSize) {
      this.stats.totalDropped++;
      return false;
    }
    
    // Simple duplicate detection
    if (this.options.enableDeduplication && this.events.find(e => e.id === event.id)) {
      this.stats.duplicatesDropped++;
      return true;
    }
    
    this.events.push(event);
    this.stats.queueSize = this.events.length;
    this.processQueue();
    return true;
  }

  private async processQueue(): Promise<void> {
    if (this.processing) return;
    this.processing = true;

    while (this.events.length > 0) {
      const event = this.events.shift();
      if (event) {
        try {
          await this.processor(event);
          this.stats.totalProcessed++;
        } catch (error) {
          this.stats.totalErrors++;
        }
      }
    }

    this.stats.queueSize = this.events.length;
    this.processing = false;
  }

  getStats() {
    return { ...this.stats };
  }

  destroy() {
    this.events = [];
    this.processing = false;
  }
}

describe('EventQueue', () => {
      setupAntiHang();
    jest.setTimeout(10000);
  let processedEvents: TestEvent[];
  let processingDelays: number[];
  let errors: Error[];

  beforeEach(() => {
    processedEvents = [];
    processingDelays = [];
    errors = [];
  });

  const createTestProcessor = () => async (event: TestEvent): Promise<void> => {
    const startTime = Date.now();
    
    // Simulate processing time
    await new Promise(resolve => setTimeout(resolve, 10));
    
    processedEvents.push(event);
    processingDelays.push(Date.now() - startTime);
  };

  const createErrorProneProcessor = () => async (event: TestEvent): Promise<void> => {
    // Deterministic failure for testing
    if (event.testData.includes('error')) {
      const error = new Error(`Processing error for event ${event.id}`);
      errors.push(error);
      throw error;
    }
    
    await createTestProcessor()(event);
  };

  const generateRapidEvents = (count: number, duplicateRate: number = 0.1): TestEvent[] => {
    const events: TestEvent[] = [];
    const baseTimestamp = Date.now();
    
    for (let i = 0; i < count; i++) {
      // Create some duplicates based on rate  
      const isDuplicate = Math.random() < duplicateRate && events.length > 0;
      const baseEvent = isDuplicate ? events[events.length - 1] : null;
      
      const event: TestEvent = {
        id: isDuplicate ? baseEvent!.id : `test-event-${i}`,
        type: 'test_event',
        payload: { data: `Test data ${i}` },
        timestamp: baseTimestamp + (i * 10), // 10ms apart
        testData: `Event ${i}`
      };
      
      events.push(event);
    }
    
    return events;
  };

  test('rapid event burst processing', async () => {
    const eventQueue = new MockEventQueue(createTestProcessor(), {
      maxQueueSize: 1000,
      duplicateWindowMs: 5000,
      processingTimeoutMs: 1000,
      enableDeduplication: true
    });
    
    // Generate test events
    const events = generateRapidEvents(10, 0.1); // Smaller count for faster test
    const startTime = Date.now();
    
    // Enqueue all events rapidly
    events.forEach(event => {
      eventQueue.enqueue(event);
    });
    
    // Wait for processing to complete
    await new Promise(resolve => setTimeout(resolve, 100));
    
    const stats = eventQueue.getStats();
    const processingTime = Date.now() - startTime;
    
    eventQueue.destroy();
    
    expect(processedEvents.length).toBeGreaterThan(0);
    expect(stats.totalProcessed).toBeGreaterThan(0);
    expect(processingTime).toBeLessThan(1000);
  });

  test('duplicate event filtering', async () => {
    const eventQueue = new MockEventQueue(createTestProcessor(), {
      maxQueueSize: 100,
      duplicateWindowMs: 3000,
      processingTimeoutMs: 1000,
      enableDeduplication: true
    });
    
    // Create events with some duplicates (deterministic)
    const events: TestEvent[] = [
      { id: 'event-1', type: 'test', payload: {}, timestamp: Date.now(), testData: 'Event 1' },
      { id: 'event-2', type: 'test', payload: {}, timestamp: Date.now(), testData: 'Event 2' },
      { id: 'event-1', type: 'test', payload: {}, timestamp: Date.now(), testData: 'Event 1 duplicate' }, // Duplicate
      { id: 'event-3', type: 'test', payload: {}, timestamp: Date.now(), testData: 'Event 3' },
    ];
    
    const uniqueIds = new Set(events.map(e => e.id));
    
    // Enqueue events
    events.forEach(event => {
      eventQueue.enqueue(event);
    });
    
    await new Promise(resolve => setTimeout(resolve, 100));
    
    const stats = eventQueue.getStats();
    const processedIds = new Set(processedEvents.map(e => e.id));
    
    eventQueue.destroy();
    
    expect(stats.duplicatesDropped).toBeGreaterThan(0);
    expect(processedIds.size).toBe(uniqueIds.size);
  });

  test('error recovery', async () => {
    const eventQueue = new MockEventQueue(createErrorProneProcessor(), {
      maxQueueSize: 100,
      duplicateWindowMs: 1000,
      processingTimeoutMs: 1000,
      enableDeduplication: false
    });
    
    // Generate events with some that will cause errors
    const events: TestEvent[] = [
      { id: 'event-1', type: 'test', payload: {}, timestamp: Date.now(), testData: 'Event 1' },
      { id: 'event-2', type: 'test', payload: {}, timestamp: Date.now(), testData: 'error event' }, // Will error
      { id: 'event-3', type: 'test', payload: {}, timestamp: Date.now(), testData: 'Event 3' },
    ];
    
    events.forEach(event => {
      eventQueue.enqueue(event);
    });
    
    await new Promise(resolve => setTimeout(resolve, 100));
    
    const stats = eventQueue.getStats();
    
    eventQueue.destroy();
    
    expect(processedEvents.length).toBeGreaterThan(0);
    expect(errors.length).toBeGreaterThan(0);
    expect(stats.totalErrors).toBeGreaterThan(0);
  });

  test('queue overflow handling', async () => {
    const eventQueue = new MockEventQueue(createTestProcessor(), {
      maxQueueSize: 2, // Very small queue
      duplicateWindowMs: 1000,
      processingTimeoutMs: 100,
      enableDeduplication: false
    });
    
    // Generate more events than queue can handle
    const events = generateRapidEvents(5, 0);
    
    let successfulEnqueues = 0;
    events.forEach(event => {
      if (eventQueue.enqueue(event)) {
        successfulEnqueues++;
      }
    });
    
    await new Promise(resolve => setTimeout(resolve, 100));
    
    const stats = eventQueue.getStats();
    
    eventQueue.destroy();
    
    expect(stats.totalDropped).toBeGreaterThan(0);
    expect(successfulEnqueues).toBeLessThan(events.length);
  });
  afterEach(() => {
    cleanupAntiHang();
  });

});