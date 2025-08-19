/**
 * Multi-Tab Test Helper Utilities
 * 
 * Specialized helpers for multi-tab synchronization testing
 * Manages multiple browser tabs and state synchronization
 * 
 * @compliance conventions.xml - Max 8 lines per function, under 300 lines
 * @compliance type_safety.xml - Full TypeScript typing
 */

import { Page, BrowserContext, expect } from '@playwright/test';
import { authenticateUser, createThread, sendMessage, cleanupTestSession } from './e2e-test-helpers';

export interface TabTestState {
  page: Page;
  context: BrowserContext;
  tabId: string;
}

export interface SyncTestData {
  threadId: string;
  message: string;
  timestamp: number;
}

/**
 * Creates authenticated tab session
 */
export async function createAuthenticatedTab(
  browser: any, 
  tabId: string
): Promise<TabTestState> {
  const context = await browser.newContext();
  const page = await context.newPage();
  
  await authenticateUser(page);
  
  return { page, context, tabId };
}

/**
 * Creates thread in specified tab
 */
export async function createThreadInTab(
  tab: TabTestState, 
  threadName: string
): Promise<string> {
  const threadId = await createThread(tab.page, threadName);
  return threadId;
}

/**
 * Sends message in tab and returns timestamp
 */
export async function sendMessageInTab(
  tab: TabTestState, 
  message: string
): Promise<number> {
  const timestamp = Date.now();
  await sendMessage(tab.page, message);
  return timestamp;
}

/**
 * Waits for message to appear in tab
 */
export async function waitForMessageInTab(
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
export async function waitForThreadInSidebar(
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
export async function deleteThreadInTab(
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
export async function validateThreadRemoval(
  tabs: TabTestState[], 
  threadId: string
): Promise<void> {
  for (const tab of tabs) {
    await expect(tab.page.locator(`[data-testid="thread-${threadId}"]`))
      .not.toBeVisible({ timeout: 5000 });
  }
}

/**
 * Switches tab to specific thread
 */
export async function switchTabToThread(
  tab: TabTestState,
  threadId: string
): Promise<void> {
  await tab.page.click(`[data-testid="thread-${threadId}"]`);
  await expect(tab.page.locator('.chat-container')).toBeVisible();
}

/**
 * Validates connection status in tab
 */
export async function validateConnectionStatus(
  tab: TabTestState,
  expectedStatus: string
): Promise<void> {
  await expect(tab.page.locator('[data-testid="connection-status"]'))
    .toContainText(expectedStatus, { timeout: 3000 });
}

/**
 * Closes all test tabs
 */
export async function closeAllTabs(tabs: TabTestState[]): Promise<void> {
  for (const tab of tabs) {
    await cleanupTestSession(tab.page);
    await tab.context.close();
  }
}

/**
 * Tests concurrent message sending
 */
export async function testConcurrentMessages(
  tabs: TabTestState[],
  baseMessage: string
): Promise<number[]> {
  const timestamps: number[] = [];
  
  const promises = tabs.map(async (tab, index) => {
    const message = `${baseMessage} from tab ${index + 1}`;
    const timestamp = await sendMessageInTab(tab, message);
    timestamps.push(timestamp);
    return { tab, message, timestamp };
  });
  
  await Promise.all(promises);
  return timestamps;
}

/**
 * Validates cross-tab message synchronization
 */
export async function validateCrossTabSync(
  tabs: TabTestState[],
  messages: string[]
): Promise<boolean> {
  for (const tab of tabs) {
    for (const message of messages) {
      const messageExists = await waitForMessageInTab(tab, message);
      if (!messageExists) return false;
    }
  }
  return true;
}

export default {
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
  validateCrossTabSync
};