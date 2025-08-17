/// <reference types="cypress" />

import {
  setupStateTests,
  cleanupState,
  TEST_CONFIG,
  getStore,
  verifyStoreAndGetState,
  createTestThread,
  createTestMessage
} from './utils/state-test-utilities';

describe('CRITICAL: Thread Management State', () => {
  beforeEach(() => {
    setupStateTests();
  });

  it('CRITICAL: Should handle concurrent thread creation without conflicts', () => {
    const threadCount = 10;
    const threads = createMultipleTestThreads(threadCount);
    
    // Create multiple threads rapidly
    createThreadsConcurrently(threads);
    
    cy.wait(TEST_CONFIG.DELAYS.LONG);
    
    // Verify all threads created
    verifyAllThreadsCreated(threads, threadCount);
  });

  it('CRITICAL: Should prevent message crossover between threads', () => {
    // Create two threads
    const thread1 = createTestThread('thread1', 'Thread 1');
    const thread2 = createTestThread('thread2', 'Thread 2');
    
    createThreadPair(thread1, thread2);
    
    // Add messages to thread1
    addMessageToThread(thread1.id, 'msg1_thread1', 'Message for thread 1');
    
    // Switch to thread2 and add messages
    addMessageToThread(thread2.id, 'msg1_thread2', 'Message for thread 2');
    
    // Verify messages are in correct threads
    verifyMessageIsolation(thread1, thread2);
  });

  afterEach(() => {
    cleanupState();
  });
});

/**
 * Creates multiple test threads for concurrent testing
 */
function createMultipleTestThreads(count: number): any[] {
  const threads: any[] = [];
  for (let i = 0; i < count; i++) {
    threads.push({
      id: `thread_${Date.now()}_${i}`,
      title: `Thread ${i}`,
      createdAt: Date.now() + i
    });
  }
  return threads;
}

/**
 * Creates threads concurrently to test race conditions
 */
function createThreadsConcurrently(threads: any[]): void {
  threads.forEach((thread, index) => {
    cy.window().then((win) => {
      const store = getStore(win);
      if (store) {
        store.getState().createThread(thread);
      }
    });
  });
}

/**
 * Verifies all threads were created without conflicts
 */
function verifyAllThreadsCreated(threads: any[], expectedCount: number): void {
  cy.window().then((win) => {
    const store = getStore(win);
    if (store) {
      const state = store.getState();
      const threadMap = state.threads;
      
      expect(threadMap.size).to.equal(expectedCount);
      
      threads.forEach(thread => {
        expect(threadMap.has(thread.id)).to.be.true;
        const stored = threadMap.get(thread.id);
        expect(stored.title).to.equal(thread.title);
      });
    }
  });
}

/**
 * Creates a pair of threads for isolation testing
 */
function createThreadPair(thread1: any, thread2: any): void {
  cy.window().then((win) => {
    const store = getStore(win);
    if (store) {
      store.getState().createThread(thread1);
      store.getState().createThread(thread2);
    }
  });
}

/**
 * Adds a message to a specific thread
 */
function addMessageToThread(threadId: string, messageId: string, content: string): void {
  cy.window().then((win) => {
    const store = getStore(win);
    if (store) {
      store.getState().setActiveThread(threadId);
      store.getState().addMessage({
        id: messageId,
        content,
        threadId
      });
    }
  });
}

/**
 * Verifies messages are properly isolated between threads
 */
function verifyMessageIsolation(thread1: any, thread2: any): void {
  cy.window().then((win) => {
    const store = getStore(win);
    if (store) {
      const state = store.getState();
      const messages = state.messages;
      
      const thread1Messages = filterMessagesByThread(messages, thread1.id);
      const thread2Messages = filterMessagesByThread(messages, thread2.id);
      
      expect(thread1Messages).to.have.length(1);
      expect(thread2Messages).to.have.length(1);
      
      expect(thread1Messages[0].content).to.include('thread 1');
      expect(thread2Messages[0].content).to.include('thread 2');
    }
  });
}

/**
 * Filters messages by thread ID
 */
function filterMessagesByThread(messages: any[], threadId: string): any[] {
  return messages.filter((m: any) => m.threadId === threadId);
}