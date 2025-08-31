import { test, expect } from '@playwright/test';
import {
import { setupAntiHang, cleanupAntiHang } from '@/__tests__/utils/anti-hanging-test-utilities';
sts real-time synchronization between multiple browser tabs/windows
 * Validates state consistency across concurrent sessions
 * 
 * @compliance conventions.xml - Max 8 lines per function, under 300 lines
 * @compliance type_safety.xml - Full TypeScript typing
 * @spec frontend_unified_testing_spec.xml - E2E concurrent sessions P1 priority
 * 
 * NOTE: This is a Playwright test - run with `npm run e2e:test`
 * DO NOT run with Jest - will cause import errors
 */

import { test, expect } from '@playwright/test';
import {
  createAuthenticatedTab,
  createThreadInTab,
  sendMessageInTab,
  waitForMessageInTab,
  waitForThreadInSidebar,
  deleteThreadInTab,
  validateThreadRemoval,
  switchTabToThread,
  validateConnectionStatus,
  closeAllTabs,
  testConcurrentMessages,
  validateCrossTabSync,
  type TabTestState,
  type SyncTestData
} from './utils/multi-tab-helpers';

/**
 * Creates test environment with multiple tabs
 */
async function setupMultiTabEnvironment(
  browser: any,
  tabCount: number
): Promise<TabTestState[]> {
  const tabs: TabTestState[] = [];
  
  for (let i = 0; i < tabCount; i++) {
    const tab = await createAuthenticatedTab(browser, `tab${i + 1}`);
    tabs.push(tab);
  }
  
  return tabs;
}

/**
 * Tests thread synchronization across tabs
 */
async function testThreadSynchronization(
  tabs: TabTestState[],
  threadName: string
): Promise<string> {
  const [primaryTab, ...otherTabs] = tabs;
  
  const threadId = await createThreadInTab(primaryTab, threadName);
  
  for (const tab of otherTabs) {
    const threadExists = await waitForThreadInSidebar(tab, threadId);
    expect(threadExists).toBe(true);
  }
  
  return threadId;
}

/**
 * Tests message synchronization workflow
 */
async function testMessageSyncWorkflow(
  tabs: TabTestState[],
  threadId: string,
  message: string
): Promise<void> {
  const [primaryTab, secondaryTab] = tabs;
  
  await sendMessageInTab(primaryTab, message);
  await switchTabToThread(secondaryTab, threadId);
  
  const messageExists = await waitForMessageInTab(secondaryTab, message);
  expect(messageExists).toBe(true);
}

test.describe('Multi-Tab Synchronization E2E', () => {
    jest.setTimeout(10000);
  let browser: any;
  let tabs: TabTestState[] = [];

  test.beforeEach(async ({ browser: testBrowser }) => {
    browser = testBrowser;
    tabs = [];
  });

  test.afterEach(async () => {
    await closeAllTabs(tabs);
    tabs = [];
  });

  test('should sync new threads across multiple tabs', async () => {
    tabs = await setupMultiTabEnvironment(browser, 3);
    
    const threadId = await testThreadSynchronization(tabs, 'Test Thread');
    expect(threadId).toBeTruthy();
  });

  test('should sync messages in real-time across tabs', async () => {
    tabs = await setupMultiTabEnvironment(browser, 2);
    
    const threadId = await createThreadInTab(tabs[0], 'Message Sync Test');
    const message = 'Real-time sync test message';
    
    await testMessageSyncWorkflow(tabs, threadId, message);
  });

  test('should sync thread deletion across tabs', async () => {
    tabs = await setupMultiTabEnvironment(browser, 2);
    
    const threadId = await createThreadInTab(tabs[0], 'Delete Test Thread');
    await waitForThreadInSidebar(tabs[1], threadId);
    
    await deleteThreadInTab(tabs[0], threadId);
    await validateThreadRemoval([tabs[1]], threadId);
  });

  test('should handle concurrent message sending', async () => {
    tabs = await setupMultiTabEnvironment(browser, 2);
    
    const threadId = await createThreadInTab(tabs[0], 'Concurrent Test');
    await waitForThreadInSidebar(tabs[1], threadId);
    
    // Switch both tabs to same thread
    for (const tab of tabs) {
      await switchTabToThread(tab, threadId);
    }
    
    // Send messages simultaneously
    const timestamps = await testConcurrentMessages(tabs, 'Concurrent message');
    
    // Verify all messages appear in all tabs
    const messages = tabs.map((_, i) => `Concurrent message from tab ${i + 1}`);
    const allSynced = await validateCrossTabSync(tabs, messages);
    expect(allSynced).toBe(true);
    
    // Verify timing
    expect(Math.abs(timestamps[0] - timestamps[1])).toBeLessThan(1000);
  });

  test('should maintain state during tab navigation', async () => {
    tabs = await setupMultiTabEnvironment(browser, 2);
    
    // Create multiple threads with messages
    const threads: SyncTestData[] = [];
    
    for (let i = 1; i <= 3; i++) {
      const threadId = await createThreadInTab(tabs[0], `Thread ${i}`);
      const message = `Message for thread ${i}`;
      
      await sendMessageInTab(tabs[0], message);
      threads.push({ threadId, message, timestamp: Date.now() });
    }
    
    // Navigate between threads in second tab
    for (const thread of threads) {
      await switchTabToThread(tabs[1], thread.threadId);
      
      const messageExists = await waitForMessageInTab(tabs[1], thread.message);
      expect(messageExists).toBe(true);
    }
  });

  test('should sync WebSocket connection status', async () => {
    tabs = await setupMultiTabEnvironment(browser, 2);
    
    // Verify both tabs show connected status
    for (const tab of tabs) {
      await validateConnectionStatus(tab, 'Connected');
    }
    
    // Simulate connection loss in first tab
    await tabs[0].context.setOffline(true);
    await validateConnectionStatus(tabs[0], 'Offline');
    
    // Second tab should remain connected
    await validateConnectionStatus(tabs[1], 'Connected');
  });

  test('should handle tab close and reopen gracefully', async () => {
    tabs = await setupMultiTabEnvironment(browser, 1);
    
    // Create thread and message
    const threadId = await createThreadInTab(tabs[0], 'Persistence Test');
    const message = 'Persistent message';
    await sendMessageInTab(tabs[0], message);
    
    // Close first tab
    await tabs[0].context.close();
    
    // Create new tab
    const newTab = await createAuthenticatedTab(browser, 'reopen1');
    tabs = [newTab];
    
    // Verify thread and message persist
    const threadExists = await waitForThreadInSidebar(newTab, threadId);
    expect(threadExists).toBe(true);
    
    await switchTabToThread(newTab, threadId);
    const messageExists = await waitForMessageInTab(newTab, message);
    expect(messageExists).toBe(true);
  });

  test('should handle complex multi-tab workflows', async () => {
    tabs = await setupMultiTabEnvironment(browser, 3);
    
    // Create threads in different tabs
    const threadIds: string[] = [];
    for (let i = 0; i < tabs.length; i++) {
      const threadId = await createThreadInTab(tabs[i], `Multi Thread ${i + 1}`);
      threadIds.push(threadId);
    }
    
    // Verify all threads visible in all tabs
    for (const tab of tabs) {
      for (const threadId of threadIds) {
        const exists = await waitForThreadInSidebar(tab, threadId);
        expect(exists).toBe(true);
      }
    }
    
    // Send messages from different tabs to different threads
    for (let i = 0; i < tabs.length; i++) {
      const targetThreadIndex = (i + 1) % tabs.length;
      await switchTabToThread(tabs[i], threadIds[targetThreadIndex]);
      await sendMessageInTab(tabs[i], `Cross-tab message ${i + 1}`);
    }
    
    // Verify all messages synchronized
    const messages = tabs.map((_, i) => `Cross-tab message ${i + 1}`);
    const allSynced = await validateCrossTabSync(tabs, messages);
    expect(allSynced).toBe(true);
  });
});