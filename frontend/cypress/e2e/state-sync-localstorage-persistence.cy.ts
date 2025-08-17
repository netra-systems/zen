/// <reference types="cypress" />

import {
  setupStateTests,
  cleanupState,
  TEST_CONFIG,
  getStore,
  verifyStoreAndGetState,
  triggerStorageEvent,
  navigateToChat
} from './utils/state-test-utilities';

describe('CRITICAL: LocalStorage Persistence & Recovery', () => {
  beforeEach(() => {
    setupStateTests();
  });

  it('CRITICAL: Should recover from corrupted localStorage data', () => {
    // Corrupt localStorage deliberately
    corruptLocalStorageData();
    
    // Reload the page
    cy.reload();
    
    // Navigate back to chat
    navigateToChat();
    
    // Verify app recovered and is functional
    const testMessage = `Recovery test ${Date.now()}`;
    testAppFunctionality(testMessage);
    
    // Verify clean state was initialized
    verifyCleanStateInitialized();
  });

  it('CRITICAL: Should maintain state consistency across tabs', () => {
    const sharedMessage = `Shared message ${Date.now()}`;
    
    // Send message in current tab
    sendMessageInCurrentTab(sharedMessage);
    
    // Simulate state change from another tab
    simulateOtherTabMessage();
    
    // Wait for sync
    cy.wait(TEST_CONFIG.DELAYS.LONG);
    
    // Verify both messages are visible
    verifyBothMessagesVisible(sharedMessage);
    
    // Verify state consistency
    verifyStateConsistency();
  });

  afterEach(() => {
    cleanupState();
  });
});

/**
 * Corrupts localStorage with invalid JSON
 */
function corruptLocalStorageData(): void {
  cy.window().then((win) => {
    win.localStorage.setItem('unified-chat-storage', '{{invalid json}}');
    win.localStorage.setItem('chat_state', 'null{broken}');
  });
}

/**
 * Tests basic app functionality after recovery
 */
function testAppFunctionality(testMessage: string): void {
  cy.get('textarea').type(testMessage);
  cy.get('button[aria-label="Send message"]').click();
  cy.contains(testMessage).should('be.visible');
}

/**
 * Verifies clean state was properly initialized
 */
function verifyCleanStateInitialized(): void {
  cy.window().then((win) => {
    const store = getStore(win);
    if (store) {
      const state = store.getState();
      expect(state).to.not.be.null;
      expect(state.messages).to.be.an('array');
    }
  });
}

/**
 * Sends a message in the current tab
 */
function sendMessageInCurrentTab(message: string): void {
  cy.get('textarea').type(message);
  cy.get('button[aria-label="Send message"]').click();
  cy.contains(message).should('be.visible');
}

/**
 * Simulates a message being added from another tab
 */
function simulateOtherTabMessage(): void {
  cy.window().then((win) => {
    const otherTabMessage = {
      id: `other_tab_${Date.now()}`,
      content: 'Message from another tab',
      role: 'user',
      timestamp: Date.now()
    };
    
    // Update localStorage as if from another tab
    const currentState = win.localStorage.getItem('chat_state');
    const state = parseStateWithFallback(currentState);
    
    state.messages = state.messages || [];
    state.messages.push(otherTabMessage);
    
    const newValue = JSON.stringify(state);
    win.localStorage.setItem('chat_state', newValue);
    
    // Trigger storage event
    triggerStorageEvent('chat_state', newValue, currentState);
  });
}

/**
 * Parses state with fallback for corruption
 */
function parseStateWithFallback(stateString: string | null): any {
  try {
    return stateString ? JSON.parse(stateString) : { messages: [] };
  } catch {
    return { messages: [] };
  }
}

/**
 * Verifies both messages are visible after cross-tab sync
 */
function verifyBothMessagesVisible(sharedMessage: string): void {
  cy.contains(sharedMessage).should('be.visible');
  cy.contains('Message from another tab').should('be.visible');
}

/**
 * Verifies state consistency after cross-tab operations
 */
function verifyStateConsistency(): void {
  cy.window().then((win) => {
    const store = getStore(win);
    if (store) {
      const messages = store.getState().messages;
      expect(messages.length).to.be.at.least(2);
    }
  });
}