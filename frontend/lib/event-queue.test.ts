/**
 * Test suite for EventQueue rapid event processing
 * Validates race condition prevention and reliability
 */

import { EventQueue, ProcessableEvent } from './event-queue';

interface TestEvent extends ProcessableEvent {
  testData: string;
}

/**
 * Test rapid event processing scenarios
 */
export class EventQueueTestRunner {
  private processedEvents: TestEvent[] = [];
  private processingDelays: number[] = [];
  private errors: Error[] = [];

  /**
   * Test processor that tracks processed events
   */
  private testProcessor = async (event: TestEvent): Promise<void> => {
    const startTime = Date.now();
    
    // Simulate variable processing time
    const delay = Math.random() * 50; // 0-50ms
    await new Promise(resolve => setTimeout(resolve, delay));
    
    this.processedEvents.push(event);
    this.processingDelays.push(Date.now() - startTime);
  };

  /**
   * Test processor that randomly fails
   */
  private errorProneProcessor = async (event: TestEvent): Promise<void> => {
    // 20% chance of failure
    if (Math.random() < 0.2) {
      const error = new Error(`Random processing error for event ${event.id}`);
      this.errors.push(error);
      throw error;
    }
    
    await this.testProcessor(event);
  };

  /**
   * Generate rapid test events
   */
  private generateRapidEvents(count: number, duplicateRate: number = 0.1): TestEvent[] {
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
  }

  /**
   * Test 1: Rapid event burst
   */
  async testRapidEventBurst(): Promise<TestResult> {
    console.log('Testing rapid event burst...');
    this.reset();
    
    const eventQueue = new EventQueue(this.testProcessor, {
      maxQueueSize: 1000,
      duplicateWindowMs: 5000,
      processingTimeoutMs: 1000,
      enableDeduplication: true
    });
    
    // Generate 100 rapid events
    const events = this.generateRapidEvents(100, 0.1);
    const startTime = Date.now();
    
    // Enqueue all events rapidly
    const enqueuePromises = events.map(event => 
      Promise.resolve(eventQueue.enqueue(event))
    );
    
    await Promise.all(enqueuePromises);
    
    // Wait for processing to complete
    await this.waitForProcessing(eventQueue, 5000);
    
    const stats = eventQueue.getStats();
    const processingTime = Date.now() - startTime;
    
    eventQueue.destroy();
    
    return {
      testName: 'Rapid Event Burst',
      success: this.processedEvents.length > 0,
      details: {
        eventsGenerated: events.length,
        eventsProcessed: this.processedEvents.length,
        duplicatesDropped: stats.duplicatesDropped,
        errors: stats.totalErrors,
        processingTime,
        averageDelay: this.calculateAverageDelay(),
        stats
      }
    };
  }

  /**
   * Test 2: Duplicate event filtering
   */
  async testDuplicateFiltering(): Promise<TestResult> {
    console.log('Testing duplicate event filtering...');
    this.reset();
    
    const eventQueue = new EventQueue(this.testProcessor, {
      maxQueueSize: 100,
      duplicateWindowMs: 3000,
      processingTimeoutMs: 1000,
      enableDeduplication: true
    });
    
    // Create events with high duplicate rate
    const events = this.generateRapidEvents(50, 0.5);
    const uniqueIds = new Set(events.map(e => e.id));
    
    // Enqueue events
    for (const event of events) {
      eventQueue.enqueue(event);
    }
    
    await this.waitForProcessing(eventQueue, 3000);
    
    const stats = eventQueue.getStats();
    const processedIds = new Set(this.processedEvents.map(e => e.id));
    
    eventQueue.destroy();
    
    return {
      testName: 'Duplicate Event Filtering',
      success: processedIds.size === uniqueIds.size,
      details: {
        eventsGenerated: events.length,
        uniqueEvents: uniqueIds.size,
        eventsProcessed: this.processedEvents.length,
        uniqueProcessed: processedIds.size,
        duplicatesDropped: stats.duplicatesDropped,
        stats
      }
    };
  }

  /**
   * Test 3: Error recovery
   */
  async testErrorRecovery(): Promise<TestResult> {
    console.log('Testing error recovery...');
    this.reset();
    
    const eventQueue = new EventQueue(this.errorProneProcessor, {
      maxQueueSize: 100,
      duplicateWindowMs: 1000,
      processingTimeoutMs: 1000,
      enableDeduplication: false
    });
    
    // Generate events
    const events = this.generateRapidEvents(50, 0);
    
    // Enqueue events
    for (const event of events) {
      eventQueue.enqueue(event);
    }
    
    await this.waitForProcessing(eventQueue, 5000);
    
    const stats = eventQueue.getStats();
    
    eventQueue.destroy();
    
    return {
      testName: 'Error Recovery',
      success: this.processedEvents.length > 0 && this.errors.length > 0,
      details: {
        eventsGenerated: events.length,
        eventsProcessed: this.processedEvents.length,
        errorsEncountered: this.errors.length,
        queueErrors: stats.totalErrors,
        errorRecoveryStats: stats.errorHandler,
        stats
      }
    };
  }

  /**
   * Test 4: Queue overflow handling
   */
  async testQueueOverflow(): Promise<TestResult> {
    console.log('Testing queue overflow handling...');
    this.reset();
    
    const eventQueue = new EventQueue(this.testProcessor, {
      maxQueueSize: 10, // Small queue
      duplicateWindowMs: 1000,
      processingTimeoutMs: 100,
      enableDeduplication: false
    });
    
    // Generate more events than queue can handle
    const events = this.generateRapidEvents(50, 0);
    
    let successfulEnqueues = 0;
    for (const event of events) {
      if (eventQueue.enqueue(event)) {
        successfulEnqueues++;
      }
    }
    
    await this.waitForProcessing(eventQueue, 3000);
    
    const stats = eventQueue.getStats();
    
    eventQueue.destroy();
    
    return {
      testName: 'Queue Overflow Handling',
      success: stats.totalDropped > 0 && successfulEnqueues < events.length,
      details: {
        eventsGenerated: events.length,
        successfulEnqueues,
        eventsProcessed: this.processedEvents.length,
        eventsDropped: stats.totalDropped,
        stats
      }
    };
  }

  /**
   * Run all tests
   */
  async runAllTests(): Promise<TestSuite> {
    console.log('Starting EventQueue test suite...');
    
    const results: TestResult[] = [];
    
    try {
      results.push(await this.testRapidEventBurst());
      results.push(await this.testDuplicateFiltering());
      results.push(await this.testErrorRecovery());
      results.push(await this.testQueueOverflow());
    } catch (error) {
      console.error('Test suite failed:', error);
    }
    
    const passedTests = results.filter(r => r.success).length;
    const totalTests = results.length;
    
    return {
      name: 'EventQueue Test Suite',
      totalTests,
      passedTests,
      failedTests: totalTests - passedTests,
      results,
      success: passedTests === totalTests
    };
  }

  /**
   * Wait for queue processing to complete
   */
  private async waitForProcessing(queue: EventQueue<TestEvent>, timeoutMs: number): Promise<void> {
    const startTime = Date.now();
    
    while (Date.now() - startTime < timeoutMs) {
      const stats = queue.getStats();
      if (stats.queueSize === 0) {
        // Wait a bit more to ensure processing is complete
        await new Promise(resolve => setTimeout(resolve, 100));
        break;
      }
      await new Promise(resolve => setTimeout(resolve, 50));
    }
  }

  /**
   * Calculate average processing delay
   */
  private calculateAverageDelay(): number {
    if (this.processingDelays.length === 0) return 0;
    return this.processingDelays.reduce((sum, delay) => sum + delay, 0) / this.processingDelays.length;
  }

  /**
   * Reset test state
   */
  private reset(): void {
    this.processedEvents = [];
    this.processingDelays = [];
    this.errors = [];
  }
}

interface TestResult {
  testName: string;
  success: boolean;
  details: Record<string, any>;
}

interface TestSuite {
  name: string;
  totalTests: number;
  passedTests: number;
  failedTests: number;
  results: TestResult[];
  success: boolean;
}

/**
 * Utility function to run tests in development
 */
export async function runEventQueueTests(): Promise<TestSuite> {
  const runner = new EventQueueTestRunner();
  return runner.runAllTests();
}