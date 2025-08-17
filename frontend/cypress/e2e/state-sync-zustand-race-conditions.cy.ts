/// <reference types="cypress" />

import {
  setupStateTests,
  cleanupState,
  TEST_CONFIG,
  getStore,
  verifyStoreAndGetState,
  verifyMessageInStore,
  verifyNoDuplicateMessages,
  createConcurrentTestData,
  executeConcurrentUpdates
} from './utils/state-test-utilities';

describe('CRITICAL: Zustand Store Race Conditions', () => {
  beforeEach(() => {
    setupStateTests();
  });

  it('CRITICAL: Should handle concurrent state updates without data loss', () => {
    // Generate concurrent update events
    const updates = createConcurrentTestData(TEST_CONFIG.MAX_CONCURRENT_UPDATES);
    
    // Trigger all updates simultaneously
    cy.window().then((win) => {
      const store = getStore(win);
      
      if (store) {
        const updatePromise = executeConcurrentUpdates(updates, (update) => {
          store.getState().addMessage({
            id: update.id,
            content: update.content,
            role: 'user',
            timestamp: update.timestamp
          });
        });
        
        return updatePromise;
      }
    });
    
    // Wait for all updates to process
    cy.wait(TEST_CONFIG.DELAYS.EXTRA_LONG);
    
    // Verify all messages were added
    verifyAllConcurrentUpdates(updates);
    verifyNoDuplicateMessages();
  });

  it('CRITICAL: Should prevent update loops in cross-component sync', () => {
    let updateCount = 0;
    let lastUpdateTime = 0;
    
    // Monitor state updates
    setupUpdateMonitoring((count, time) => {
      updateCount = count;
      lastUpdateTime = time;
    });
    
    // Trigger circular update scenario
    triggerCircularUpdateScenario();
    
    // Wait for updates to settle
    cy.wait(TEST_CONFIG.DELAYS.EXTRA_LONG);
    
    // Verify no runaway updates
    verifyNoUpdateLoops(updateCount, lastUpdateTime);
  });

  afterEach(() => {
    cleanupState();
  });
});

/**
 * Verifies all concurrent updates were processed correctly
 */
function verifyAllConcurrentUpdates(updates: any[]): void {
  cy.window().then((win) => {
    const store = getStore(win);
    if (store) {
      const state = store.getState();
      const messages = state.messages || [];
      
      // Check that all updates were preserved
      updates.forEach(update => {
        const found = messages.find((m: any) => m.id === update.id);
        expect(found).to.not.be.undefined;
        if (found) {
          expect(found.content).to.equal(update.content);
        }
      });
    }
  });
}

/**
 * Sets up monitoring for state updates
 */
function setupUpdateMonitoring(callback: (count: number, time: number) => void): void {
  cy.window().then((win) => {
    const store = getStore(win);
    if (store) {
      let count = 0;
      
      // Subscribe to state changes
      store.subscribe(() => {
        count++;
        const time = Date.now();
        callback(count, time);
      });
    }
  });
}

/**
 * Triggers circular update scenario to test for loops
 */
function triggerCircularUpdateScenario(): void {
  cy.window().then((win) => {
    // Simulate component A updating state
    win.dispatchEvent(new CustomEvent('netra:state:update', {
      detail: { source: 'componentA', data: { value: 1 } }
    }));
    
    // Simulate component B reacting to A's update
    win.dispatchEvent(new CustomEvent('netra:state:update', {
      detail: { source: 'componentB', data: { value: 2 } }
    }));
    
    // Simulate component A reacting to B's update (potential loop)
    win.dispatchEvent(new CustomEvent('netra:state:update', {
      detail: { source: 'componentA', data: { value: 3 } }
    }));
  });
}

/**
 * Verifies no update loops occurred
 */
function verifyNoUpdateLoops(updateCount: number, lastUpdateTime: number): void {
  cy.wrap(null).then(() => {
    expect(updateCount).to.be.lessThan(
      20,
      'Should not have excessive updates (indicates update loop)'
    );
    
    const timeSinceLastUpdate = Date.now() - lastUpdateTime;
    expect(timeSinceLastUpdate).to.be.greaterThan(
      500,
      'Updates should have stopped (no ongoing loop)'
    );
  });
}