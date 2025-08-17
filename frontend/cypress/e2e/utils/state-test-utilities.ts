/// <reference types="cypress" />

/**
 * Shared utilities for state synchronization tests
 * Provides common setup, teardown, and assertion helpers
 */

// Test configuration constants
export const TEST_CONFIG = {
  LAYER_UPDATE_TIMEOUT: 5000,
  STATE_SYNC_DELAY: 1000,
  MAX_CONCURRENT_UPDATES: 10,
  VIEWPORT: { width: 1920, height: 1080 },
  DELAYS: {
    SHORT: 100,
    MEDIUM: 500,
    LONG: 1000,
    EXTRA_LONG: 2000
  }
} as const;

// Test user data
export const TEST_USER = {
  id: 'test-user',
  email: 'test@netrasystems.ai',
  name: 'Test User',
  token: 'test-token'
} as const;

/**
 * Sets up authentication and initial state
 */
export function setupAuthAndState(): void {
  cy.window().then((win) => {
    win.localStorage.setItem('auth_token', TEST_USER.token);
    win.localStorage.setItem('user', JSON.stringify({
      id: TEST_USER.id,
      email: TEST_USER.email,
      name: TEST_USER.name
    }));
  });
}

/**
 * Clears existing state from storage
 */
export function clearExistingState(): void {
  cy.window().then((win) => {
    win.localStorage.removeItem('unified-chat-storage');
    win.localStorage.removeItem('chat_state');
    win.sessionStorage.clear();
  });
}

/**
 * Navigates to chat interface
 */
export function navigateToChat(): void {
  cy.visit('/demo');
  cy.contains('Technology').click();
  cy.contains('AI Chat').click({ force: true });
  cy.wait(TEST_CONFIG.DELAYS.LONG);
}

/**
 * Complete setup for all state sync tests
 */
export function setupStateTests(): void {
  cy.viewport(TEST_CONFIG.VIEWPORT.width, TEST_CONFIG.VIEWPORT.height);
  setupAuthAndState();
  clearExistingState();
  navigateToChat();
}

/**
 * Gets the Zustand store from window
 */
export function getStore(win: Window): any {
  return (win as any).__NETRA_STORE || (win as any).unifiedChatStore;
}

/**
 * Waits for state updates to process
 */
export function waitForStateSync(): void {
  cy.wait(TEST_CONFIG.STATE_SYNC_DELAY);
}

/**
 * Verifies store exists and returns state
 */
export function verifyStoreAndGetState(): Cypress.Chainable<any> {
  return cy.window().then((win) => {
    const store = getStore(win);
    expect(store).to.not.be.undefined;
    return store.getState();
  });
}

/**
 * Creates test message data
 */
export function createTestMessage(id: string, content: string): any {
  return {
    id,
    content,
    role: 'user',
    timestamp: Date.now()
  };
}

/**
 * Creates test thread data
 */
export function createTestThread(id: string, title: string): any {
  return {
    id,
    title,
    createdAt: Date.now()
  };
}

/**
 * Cleans up state after tests
 */
export function cleanupState(): void {
  cy.window().then((win) => {
    win.localStorage.removeItem('unified-chat-storage');
    win.localStorage.removeItem('chat_state');
    win.localStorage.removeItem('legacy_chat_state');
    win.sessionStorage.clear();
    
    const store = getStore(win);
    if (store && store.getState().reset) {
      store.getState().reset();
    }
  });
}

/**
 * Verifies message exists in store
 */
export function verifyMessageInStore(messageId: string, expectedContent: string): void {
  verifyStoreAndGetState().then((state) => {
    const messages = state.messages || [];
    const found = messages.find((m: any) => m.id === messageId);
    expect(found).to.not.be.undefined;
    if (found) {
      expect(found.content).to.equal(expectedContent);
    }
  });
}

/**
 * Verifies no duplicate messages exist
 */
export function verifyNoDuplicateMessages(): void {
  verifyStoreAndGetState().then((state) => {
    const messages = state.messages || [];
    const uniqueIds = new Set(messages.map((m: any) => m.id));
    expect(uniqueIds.size).to.equal(messages.length);
  });
}

/**
 * Triggers storage event for cross-tab simulation
 */
export function triggerStorageEvent(key: string, newValue: string, oldValue: string | null): void {
  cy.window().then((win) => {
    win.dispatchEvent(new StorageEvent('storage', {
      key,
      newValue,
      oldValue,
      storageArea: win.localStorage
    }));
  });
}

/**
 * Creates performance timer
 */
export function createPerformanceTimer(): { start: number; elapsed: () => number } {
  const start = Date.now();
  return {
    start,
    elapsed: () => Date.now() - start
  };
}

/**
 * Verifies performance under threshold
 */
export function verifyPerformance(elapsed: number, threshold: number, operation: string): void {
  expect(elapsed).to.be.lessThan(
    threshold,
    `${operation} should take less than ${threshold}ms`
  );
}

/**
 * Creates multiple test messages for concurrent testing
 */
export function createConcurrentTestData(count: number): any[] {
  const updates: any[] = [];
  for (let i = 0; i < count; i++) {
    updates.push({
      type: 'message',
      id: `msg_${Date.now()}_${i}`,
      content: `Concurrent message ${i}`,
      timestamp: Date.now() + i
    });
  }
  return updates;
}

/**
 * Executes concurrent updates with random delays
 */
export function executeConcurrentUpdates(updates: any[], updateFn: (update: any) => void): Promise<void[]> {
  const promises = updates.map(update => {
    return new Promise<void>((resolve) => {
      setTimeout(() => {
        updateFn(update);
        resolve();
      }, Math.random() * 100);
    });
  });
  
  return Promise.all(promises);
}