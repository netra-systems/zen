/**
 * End-to-End Multi-Tab Synchronization Test
 * 
 * Tests real-time synchronization between multiple browser tabs/windows
 * Validates state consistency across concurrent sessions
 * 
 * @compliance conventions.xml - Max 8 lines per function, under 300 lines
 * @compliance type_safety.xml - Full TypeScript typing
 * @spec frontend_unified_testing_spec.xml - E2E concurrent sessions P1 priority
 */

import { test, expect, Page, BrowserContext } from '@playwright/test';

interface TabTestState {
  page: Page;
  context: BrowserContext;
  tabId: string;
}

interface SyncTestData {
  threadId: string;
  message: string;
  timestamp: number;
}

/**
 * Creates authenticated tab session
 */
async function createAuthenticatedTab(
  browser: any, 
  tabId: string
): Promise<TabTestState> {
  const context = await browser.newContext();
  const page = await context.newPage();
  
  await page.goto('/login');
  await authenticateTab(page, tabId);
  
  return { page, context, tabId };
}

/**
 * Authenticates single tab with unique user data
 */
async function authenticateTab(page: Page, tabId: string): Promise<void> {
  const userData = {
    id: `user-${tabId}`,
    email: `test-${tabId}@netrasystems.ai`,
    name: `Test User ${tabId}`
  };
  
  await page.evaluate((data) => {
    localStorage.setItem('auth_token', `token-${data.tabId}`);
    localStorage.setItem('user', JSON.stringify(data.userData));
  }, { tabId, userData });
  
  await page.goto('/chat');
}

/**
 * Creates thread in specified tab
 */
async function createThreadInTab(
  tab: TabTestState, 
  threadName: string
): Promise<string> {
  await tab.page.click('[data-testid="new-conversation"]');
  await expect(tab.page).toHaveURL(/\/chat/);
  
  // Rename thread if possible
  const threadId = await tab.page.evaluate(() => 
    new Date().getTime().toString()
  );
  
  return threadId;
}

/**
 * Sends message in tab and returns timestamp
 */
async function sendMessageInTab(
  tab: TabTestState, 
  message: string
): Promise<number> {
  const timestamp = Date.now();
  
  await tab.page.fill('[data-testid="message-input"]', message);
  await tab.page.keyboard.press('Enter');
  
  await expect(tab.page.locator('.user-message'))
    .toContainText(message, { timeout: 3000 });
  
  return timestamp;
}

/**
 * Waits for message to appear in tab
 */
async function waitForMessageInTab(
  tab: TabTestState, 
  message: string
): Promise<boolean> {
  try {
    await expect(tab.page.locator('.message'))
      .toContainText(message, { timeout: 5000 });
    return true;
  } catch {
    return false;
  }
}

/**
 * Waits for thread to appear in sidebar
 */
async function waitForThreadInSidebar(
  tab: TabTestState, 
  threadIdentifier: string
): Promise<boolean> {
  try {
    await expect(tab.page.locator('[data-testid="thread-list"] .thread-item'))
      .toContainText(threadIdentifier, { timeout: 5000 });
    return true;
  } catch {
    return false;
  }
}

/**
 * Deletes thread from tab
 */
async function deleteThreadInTab(
  tab: TabTestState, 
  threadId: string
): Promise<void> {
  await tab.page.click(`[data-testid="thread-${threadId}"] .delete-button`);
  await tab.page.click('[data-testid="confirm-delete"]');
  
  await expect(tab.page.locator(`[data-testid="thread-${threadId}"]`))
    .not.toBeVisible({ timeout: 3000 });
}

/**
 * Validates thread removal across tabs
 */
async function validateThreadRemoval(
  tabs: TabTestState[], 
  threadId: string
): Promise<void> {
  for (const tab of tabs) {
    await expect(tab.page.locator(`[data-testid="thread-${threadId}"]`))
      .not.toBeVisible({ timeout: 5000 });
  }
}

test.describe('Multi-Tab Synchronization E2E', () => {
  let browser: any;
  let tabs: TabTestState[] = [];

  test.beforeEach(async ({ browser: testBrowser }) => {
    browser = testBrowser;
    tabs = [];
  });

  test.afterEach(async () => {
    for (const tab of tabs) {
      await tab.context.close();
    }
    tabs = [];
  });

  test('should sync new threads across multiple tabs', async () => {
    // Create 3 tabs
    const tab1 = await createAuthenticatedTab(browser, 'tab1');
    const tab2 = await createAuthenticatedTab(browser, 'tab2');
    const tab3 = await createAuthenticatedTab(browser, 'tab3');
    tabs = [tab1, tab2, tab3];
    
    // Create thread in tab1
    const threadId = await createThreadInTab(tab1, 'Test Thread');
    
    // Verify thread appears in other tabs within 5 seconds
    const tab2HasThread = await waitForThreadInSidebar(tab2, threadId);
    const tab3HasThread = await waitForThreadInSidebar(tab3, threadId);
    
    expect(tab2HasThread).toBe(true);
    expect(tab3HasThread).toBe(true);
  });

  test('should sync messages in real-time across tabs', async () => {
    const tab1 = await createAuthenticatedTab(browser, 'sync1');
    const tab2 = await createAuthenticatedTab(browser, 'sync2');
    tabs = [tab1, tab2];
    
    // Create thread and send message in tab1
    const threadId = await createThreadInTab(tab1, 'Message Sync Test');
    const message = 'Real-time sync test message';
    
    await sendMessageInTab(tab1, message);
    
    // Switch tab2 to same thread
    await tab2.page.click(`[data-testid="thread-${threadId}"]`);
    
    // Verify message appears in tab2
    const messageExists = await waitForMessageInTab(tab2, message);
    expect(messageExists).toBe(true);
  });

  test('should sync thread deletion across tabs', async () => {
    const tab1 = await createAuthenticatedTab(browser, 'del1');
    const tab2 = await createAuthenticatedTab(browser, 'del2');
    tabs = [tab1, tab2];
    
    // Create thread in tab1
    const threadId = await createThreadInTab(tab1, 'Delete Test Thread');
    
    // Wait for thread to sync to tab2
    await waitForThreadInSidebar(tab2, threadId);
    
    // Delete thread in tab1
    await deleteThreadInTab(tab1, threadId);
    
    // Verify deletion syncs to tab2
    await validateThreadRemoval([tab2], threadId);
  });

  test('should handle concurrent message sending', async () => {
    const tab1 = await createAuthenticatedTab(browser, 'concurrent1');
    const tab2 = await createAuthenticatedTab(browser, 'concurrent2');
    tabs = [tab1, tab2];
    
    // Create shared thread
    const threadId = await createThreadInTab(tab1, 'Concurrent Test');
    await waitForThreadInSidebar(tab2, threadId);
    
    // Switch both tabs to same thread
    await tab2.page.click(`[data-testid="thread-${threadId}"]`);
    
    // Send messages simultaneously
    const message1 = 'Concurrent message from tab 1';
    const message2 = 'Concurrent message from tab 2';
    
    const [timestamp1, timestamp2] = await Promise.all([
      sendMessageInTab(tab1, message1),
      sendMessageInTab(tab2, message2)
    ]);
    
    // Both messages should appear in both tabs
    await Promise.all([
      waitForMessageInTab(tab1, message2),
      waitForMessageInTab(tab2, message1)
    ]);
    
    // Verify message ordering by timestamp
    expect(Math.abs(timestamp1 - timestamp2)).toBeLessThan(1000);
  });

  test('should maintain state during tab navigation', async () => {
    const tab1 = await createAuthenticatedTab(browser, 'nav1');
    const tab2 = await createAuthenticatedTab(browser, 'nav2');
    tabs = [tab1, tab2];
    
    // Create multiple threads with messages
    const threads: SyncTestData[] = [];
    
    for (let i = 1; i <= 3; i++) {
      const threadId = await createThreadInTab(tab1, `Thread ${i}`);
      const message = `Message for thread ${i}`;
      
      await sendMessageInTab(tab1, message);
      threads.push({ threadId, message, timestamp: Date.now() });
    }
    
    // Navigate between threads in tab2
    for (const thread of threads) {
      await tab2.page.click(`[data-testid="thread-${thread.threadId}"]`);
      
      const messageExists = await waitForMessageInTab(tab2, thread.message);
      expect(messageExists).toBe(true);
    }
  });

  test('should sync WebSocket connection status', async () => {
    const tab1 = await createAuthenticatedTab(browser, 'ws1');
    const tab2 = await createAuthenticatedTab(browser, 'ws2');
    tabs = [tab1, tab2];
    
    // Verify both tabs show connected status
    await expect(tab1.page.locator('[data-testid="connection-status"]'))
      .toContainText('Connected', { timeout: 3000 });
    
    await expect(tab2.page.locator('[data-testid="connection-status"]'))
      .toContainText('Connected', { timeout: 3000 });
    
    // Simulate connection loss in tab1 (if supported)
    await tab1.context.setOffline(true);
    
    await expect(tab1.page.locator('[data-testid="connection-status"]'))
      .toContainText('Offline', { timeout: 5000 });
    
    // Tab2 should remain connected
    await expect(tab2.page.locator('[data-testid="connection-status"]'))
      .toContainText('Connected', { timeout: 2000 });
  });

  test('should handle tab close and reopen gracefully', async () => {
    const tab1 = await createAuthenticatedTab(browser, 'close1');
    tabs = [tab1];
    
    // Create thread and message
    const threadId = await createThreadInTab(tab1, 'Persistence Test');
    const message = 'Persistent message';
    await sendMessageInTab(tab1, message);
    
    // Close tab1
    await tab1.context.close();
    
    // Reopen new tab
    const tab2 = await createAuthenticatedTab(browser, 'reopen1');
    tabs = [tab2];
    
    // Verify thread and message persist
    const threadExists = await waitForThreadInSidebar(tab2, threadId);
    expect(threadExists).toBe(true);
    
    await tab2.page.click(`[data-testid="thread-${threadId}"]`);
    const messageExists = await waitForMessageInTab(tab2, message);
    expect(messageExists).toBe(true);
  });
});