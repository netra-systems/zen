import { setupAntiHang, cleanupAntiHang } from '@/__tests__/utils/anti-hanging-test-utilities';
import { test, expect, Page, BrowserContext } from '@playwright/test';
import { rney: login → create conversation → send messages → logout
 * Validates complete workflow performance and reliability
 * 
 * @compliance conventions.xml - Max 8 lines per function, under 300 lines
 * @compliance type_safety.xml - Full TypeScript typing
 * @spec frontend_unified_testing_spec.xml - E2E scenario P0 priority
 */

import { test, expect, Page, BrowserContext } from '@playwright/test';
import {
  authenticateUser,
  createThread,
  sendMessage,
  waitForAIResponse,
  waitForWebSocketConnection,
  measurePagePerformance,
  validatePerformance,
  cleanupTestSession,
  simulateNetworkCondition,
  createTestUser,
  type TestUser,
  type PerformanceThresholds
} from './utils/e2e-test-helpers';

interface ConversationMetrics {
  startTime: number;
  endTime: number;
  messageCount: number;
  responseLatency: number[];
}

/**
 * Sets up complete conversation workflow
 */
async function setupConversationWorkflow(page: Page): Promise<TestUser> {
  const testUser = await authenticateUser(page);
  await waitForWebSocketConnection(page);
  return testUser;
}

/**
 * Sends message and measures response time
 */
async function sendMessageWithTiming(page: Page, message: string): Promise<number> {
  const startTime = Date.now();
  await sendMessage(page, message);
  await waitForAIResponse(page);
  return Date.now() - startTime;
}

/**
 * Validates message persistence after reload
 */
async function validateMessagePersistence(
  page: Page, 
  messages: string[]
): Promise<void> {
  await page.reload();
  for (const message of messages) {
    await expect(page.locator('.message')).toContainText(message);
  }
}

/**
 * Performs logout and validates cleanup
 */
async function performLogoutFlow(page: Page): Promise<void> {
  await page.goto('/auth/logout');
  await expect(page).toHaveURL(/\/login/);
  await cleanupTestSession(page);
}

test.describe('Complete Conversation Flow E2E', () => {
    jest.setTimeout(10000);
  let context: BrowserContext;
  let page: Page;

  test.beforeEach(async ({ browser }) => {
    context = await browser.newContext();
    page = await context.newPage();
    await page.goto('/');
  });

  test.afterEach(async () => {
    await context.close();
  });

  test('should complete full conversation flow under 30 seconds', async () => {
    const startTime = Date.now();
    
    // Step 1: Setup authenticated workflow
    const testUser = await setupConversationWorkflow(page);
    expect(testUser.email).toContain('@netrasystems.ai');
    
    // Step 2: Create conversation and send messages
    const threadId = await createThread(page);
    const messages = ['Hello AI', 'What can you help me with?', 'Thank you'];
    
    for (const message of messages) {
      const latency = await sendMessageWithTiming(page, message);
      expect(latency).toBeLessThan(3000);
    }
    
    // Step 3: Validate persistence and performance
    await validateMessagePersistence(page, messages);
    const metrics = await measurePagePerformance(page);
    validatePerformance(metrics, { maxResponseTime: 2000 });
    
    // Step 4: Complete logout flow
    await performLogoutFlow(page);
    
    const totalTime = Date.now() - startTime;
    expect(totalTime).toBeLessThan(30000);
  });

  test('should handle WebSocket connection establishment', async () => {
    await setupConversationWorkflow(page);
    await createThread(page);
    
    // Test real-time message delivery
    const message = 'WebSocket test message';
    await sendMessage(page, message);
    await waitForAIResponse(page);
    
    // Verify streaming response appears
    await expect(page.locator('.ai-message .streaming-indicator'))
      .toBeVisible({ timeout: 2000 });
  });

  test('should maintain 60 FPS during conversation', async () => {
    await setupConversationWorkflow(page);
    await createThread(page);
    
    // Monitor frame rate during interaction
    const frameRate = await page.evaluate(async () => {
      const frames: number[] = [];
      let lastFrame = performance.now();
      
      for (let i = 0; i < 60; i++) {
        await new Promise(resolve => requestAnimationFrame(resolve));
        const currentFrame = performance.now();
        frames.push(1000 / (currentFrame - lastFrame));
        lastFrame = currentFrame;
      }
      
      return frames.reduce((sum, fps) => sum + fps, 0) / frames.length;
    });
    
    expect(frameRate).toBeGreaterThan(55);
  });

  test('should handle session timeout gracefully', async () => {
    await setupConversationWorkflow(page);
    
    // Simulate session expiration
    await page.evaluate(() => localStorage.removeItem('auth_token'));
    await createThread(page);
    
    // Should redirect to login on session expiry
    await expect(page).toHaveURL(/\/login/, { timeout: 5000 });
  });

  test('should recover from network interruption', async () => {
    await setupConversationWorkflow(page);
    await createThread(page);
    
    // Test offline mode
    await simulateNetworkCondition(page, 'offline');
    const message = 'Offline message';
    await sendMessage(page, message);
    
    // Reconnect and verify delivery
    await simulateNetworkCondition(page, 'fast');
    await waitForWebSocketConnection(page);
    await expect(page.locator('.user-message'))
      .toContainText(message, { timeout: 3000 });
  });

  test('should prevent memory leaks during extended use', async () => {
    await setupConversationWorkflow(page);
    await createThread(page);
    
    const initialMetrics = await measurePagePerformance(page);
    
    // Send 20 messages to simulate extended use
    for (let i = 0; i < 20; i++) {
      await sendMessage(page, `Test message ${i + 1}`);
    }
    
    const finalMetrics = await measurePagePerformance(page);
    const memoryIncrease = finalMetrics.maxMemoryMB - initialMetrics.maxMemoryMB;
    
    // Memory should not grow excessively (allow 50MB increase)
    expect(memoryIncrease).toBeLessThan(50);
  });
});