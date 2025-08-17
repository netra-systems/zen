import {
  setupThreadTestEnvironment,
  openThreadSidebar,
  mockPaginatedMessages,
  generateMockMessages,
  waitForThreadOperation,
  verifyMessageVisible
} from './thread-test-helpers';

/**
 * Thread Message Operations Tests
 * Tests for message pagination and loading operations
 * Business Value: Growth segment - validates efficient message browsing workflows
 */

describe('Thread Message Operations', () => {
  beforeEach(() => {
    setupThreadTestEnvironment();
  });

  it('should load more messages on scroll', () => {
    setupInitialMessages();
    loadThreadWithMessages();
    setupOlderMessages();
    triggerMessageLoading();
    verifyAllMessagesLoaded();
  });

  // Initial message loading helpers
  function setupInitialMessages(): void {
    const initialMessages = generateMockMessages('thread-1', 20, 0);
    mockPaginatedMessages('thread-1', 20, 0, initialMessages);
  }

  function loadThreadWithMessages(): void {
    openThreadSidebar();
    cy.contains('LLM Optimization Discussion').click();
    waitForThreadOperation('getMessagesInitial');
  }

  function setupOlderMessages(): void {
    const olderMessages = generateMockMessages('thread-1', 20, 20);
    mockPaginatedMessages('thread-1', 20, 20, olderMessages);
  }

  function triggerMessageLoading(): void {
    cy.get('.overflow-y-auto').scrollTo('top');
    waitForThreadOperation('getMessagesOlder');
  }

  function verifyAllMessagesLoaded(): void {
    verifyOlderMessagesVisible();
    verifyOriginalMessagesVisible();
  }

  function verifyOlderMessagesVisible(): void {
    verifyMessageVisible('Older Message 20');
    verifyMessageVisible('Older Message 39');
  }

  function verifyOriginalMessagesVisible(): void {
    verifyMessageVisible('Message 0');
  }
});