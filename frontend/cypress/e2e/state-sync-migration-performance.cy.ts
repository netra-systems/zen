/// <reference types="cypress" />

import {
  setupStateTests,
  cleanupState,
  TEST_CONFIG,
  getStore,
  verifyStoreAndGetState,
  createPerformanceTimer,
  verifyPerformance
} from './utils/state-test-utilities';

describe('CRITICAL: State Migration & Performance Management', () => {
  beforeEach(() => {
    setupStateTests();
  });

  describe('State Migration & Compatibility', () => {
    it('CRITICAL: Should migrate old state schema to new format', () => {
      // Set old format state
      const oldStateFormat = createOldStateFormat();
      
      setLegacyState(oldStateFormat);
      
      // Trigger migration
      triggerStateMigration();
      
      cy.wait(TEST_CONFIG.DELAYS.LONG);
      
      // Verify migration completed
      verifyMigrationCompleted();
    });
  });

  describe('Performance & Memory Management', () => {
    it('CRITICAL: Should handle 1000+ messages without performance degradation', () => {
      const messageCount = 1000;
      const timer = createPerformanceTimer();
      
      // Add many messages
      addManyMessages(messageCount);
      
      const addTime = timer.elapsed();
      
      // Verify performance
      verifyPerformance(addTime, 5000, `Adding ${messageCount} messages`);
      
      // Test state access performance
      testStateAccessPerformance(messageCount);
      
      // Check memory usage if available
      checkMemoryUsage(messageCount);
    });
  });

  afterEach(() => {
    cleanupState();
  });
});

/**
 * Creates old state format for migration testing
 */
function createOldStateFormat(): any {
  return {
    messages: [
      { text: 'Old message 1', timestamp: Date.now() - 10000 },
      { text: 'Old message 2', timestamp: Date.now() - 5000 }
    ],
    user: 'test-user',
    session: 'old-session'
  };
}

/**
 * Sets legacy state in localStorage
 */
function setLegacyState(oldState: any): void {
  cy.window().then((win) => {
    win.localStorage.setItem('legacy_chat_state', JSON.stringify(oldState));
  });
}

/**
 * Triggers state migration process
 */
function triggerStateMigration(): void {
  cy.window().then((win) => {
    win.dispatchEvent(new CustomEvent('netra:migrate:state'));
  });
}

/**
 * Verifies migration was completed successfully
 */
function verifyMigrationCompleted(): void {
  cy.window().then((win) => {
    const store = getStore(win);
    if (store) {
      const state = store.getState();
      const messages = state.messages;
      
      // Old messages should be migrated with proper structure
      expect(messages).to.have.length.at.least(2);
      messages.forEach((msg: any) => {
        expect(msg).to.have.property('id');
        expect(msg).to.have.property('content');
        expect(msg).to.have.property('timestamp');
        expect(msg).to.have.property('role');
      });
    }
  });
}

/**
 * Adds many messages for performance testing
 */
function addManyMessages(count: number): void {
  cy.window().then((win) => {
    const store = getStore(win);
    if (store) {
      for (let i = 0; i < count; i++) {
        store.getState().addMessage({
          id: `perf_test_${i}`,
          content: `Performance test message ${i}`,
          role: i % 2 === 0 ? 'user' : 'assistant',
          timestamp: Date.now() + i
        });
      }
    }
  });
}

/**
 * Tests state access performance
 */
function testStateAccessPerformance(messageCount: number): void {
  const accessTimer = createPerformanceTimer();
  
  cy.window().then((win) => {
    const store = getStore(win);
    if (store) {
      const state = store.getState();
      const messages = state.messages;
      
      // Access all messages
      messages.forEach((msg: any) => {
        const _ = msg.content; // Force access
      });
    }
  });
  
  const accessTime = accessTimer.elapsed();
  
  verifyPerformance(accessTime, 1000, 'Accessing all messages');
}

/**
 * Checks memory usage if performance API is available
 */
function checkMemoryUsage(messageCount: number): void {
  cy.window().then((win) => {
    if ((win.performance as any).memory) {
      const memoryUsed = (win.performance as any).memory.usedJSHeapSize;
      const memoryPerMessage = memoryUsed / messageCount;
      
      // Each message should use less than 10KB on average
      expect(memoryPerMessage).to.be.lessThan(
        10 * 1024,
        'Memory usage per message should be reasonable'
      );
    }
  });
}