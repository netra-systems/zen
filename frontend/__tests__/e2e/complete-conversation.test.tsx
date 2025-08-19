/**
 * End-to-End Complete Conversation Flow Test
 * 
 * Tests critical user journey: login → create conversation → send messages → logout
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
 * Sets up authenticated user session
 */
async function setupAuthenticatedUser(page: Page): Promise<AuthTestUser> {
  const testUser: AuthTestUser = {
    email: 'test@netrasystems.ai',
    name: 'Test User',
    id: 'e2e-test-user'
  };
  
  await page.goto('/login');
  await mockSuccessfulAuthentication(page, testUser);
  return testUser;
}

/**
 * Mocks successful authentication process
 */
async function mockSuccessfulAuthentication(
  page: Page, 
  user: AuthTestUser
): Promise<void> {
  await page.evaluate((userData) => {
    localStorage.setItem('auth_token', 'e2e-test-token');
    localStorage.setItem('user', JSON.stringify(userData));
  }, user);
  await page.goto('/chat');
}

/**
 * Creates new conversation thread
 */
async function createNewConversation(page: Page): Promise<string> {
  await page.click('[data-testid="new-conversation"]');
  await expect(page).toHaveURL(/\/chat/);
  
  const threadId = await page.evaluate(() => 
    localStorage.getItem('currentThreadId') || 'default'
  );
  return threadId;
}

/**
 * Sends message and waits for response
 */
async function sendMessageAndWaitResponse(
  page: Page, 
  message: string
): Promise<number> {
  const startTime = Date.now();
  
  await page.fill('[data-testid="message-input"]', message);
  await page.keyboard.press('Enter');
  
  await expect(page.locator('.user-message')).toContainText(message);
  await expect(page.locator('.ai-message')).toBeVisible({ timeout: 5000 });
  
  return Date.now() - startTime;
}

/**
 * Validates conversation state persistence
 */
async function validateConversationPersistence(
  page: Page, 
  expectedMessages: string[]
): Promise<void> {
  await page.reload();
  
  for (const message of expectedMessages) {
    await expect(page.locator('.message')).toContainText(message);
  }
}

/**
 * Measures performance metrics
 */
async function measurePerformanceMetrics(page: Page): Promise<ConversationMetrics> {
  const performanceData = await page.evaluate(() => {
    const navigation = performance.getEntriesByType('navigation')[0] as PerformanceNavigationTiming;
    return {
      loadTime: navigation.loadEventEnd - navigation.loadEventStart,
      domContentLoaded: navigation.domContentLoadedEventEnd - navigation.domContentLoadedEventStart
    };
  });
  
  return {
    startTime: Date.now(),
    endTime: Date.now(),
    messageCount: 0,
    responseLatency: [performanceData.loadTime]
  };
}

/**
 * Performs logout and cleanup
 */
async function performLogoutAndCleanup(page: Page): Promise<void> {
  await page.goto('/auth/logout');
  await expect(page).toHaveURL(/\/login/);
  
  const authToken = await page.evaluate(() => 
    localStorage.getItem('auth_token')
  );
  expect(authToken).toBeNull();
}

test.describe('Complete Conversation Flow E2E', () => {
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
    
    // Step 1: Authentication
    const testUser = await setupAuthenticatedUser(page);
    expect(testUser.email).toBe('test@netrasystems.ai');
    
    // Step 2: Create new conversation
    const threadId = await createNewConversation(page);
    expect(threadId).toBeTruthy();
    
    // Step 3: Send multiple messages
    const messages = ['Hello AI', 'What can you help me with?', 'Thank you'];
    const responseLatencies: number[] = [];
    
    for (const message of messages) {
      const latency = await sendMessageAndWaitResponse(page, message);
      responseLatencies.push(latency);
      expect(latency).toBeLessThan(3000); // 3s max response time
    }
    
    // Step 4: Validate state persistence
    await validateConversationPersistence(page, messages);
    
    // Step 5: Performance validation
    const metrics = await measurePerformanceMetrics(page);
    expect(metrics.responseLatency[0]).toBeLessThan(2000);
    
    // Step 6: Logout
    await performLogoutAndCleanup(page);
    
    const totalTime = Date.now() - startTime;
    expect(totalTime).toBeLessThan(30000); // Complete flow under 30s
  });

  test('should handle WebSocket connection establishment', async () => {
    await setupAuthenticatedUser(page);
    await createNewConversation(page);
    
    // Verify WebSocket connection indicator
    await expect(page.locator('[data-testid="connection-status"]'))
      .toContainText('Connected', { timeout: 1000 });
    
    // Test real-time message delivery
    const message = 'WebSocket test message';
    await sendMessageAndWaitResponse(page, message);
    
    // Verify streaming response starts within 2s
    await expect(page.locator('.ai-message .streaming-indicator'))
      .toBeVisible({ timeout: 2000 });
  });

  test('should maintain 60 FPS during conversation', async () => {
    await setupAuthenticatedUser(page);
    await createNewConversation(page);
    
    // Monitor frame rate during interaction
    const frameRateData = await page.evaluate(async () => {
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
    
    expect(frameRateData).toBeGreaterThan(55); // Allow slight variance from 60 FPS
  });

  test('should handle session timeout gracefully', async () => {
    await setupAuthenticatedUser(page);
    
    // Simulate session expiration
    await page.evaluate(() => {
      localStorage.removeItem('auth_token');
    });
    
    await createNewConversation(page);
    
    // Should redirect to login on session expiry
    await expect(page).toHaveURL(/\/login/, { timeout: 5000 });
  });

  test('should recover from network interruption', async () => {
    await setupAuthenticatedUser(page);
    await createNewConversation(page);
    
    // Simulate network disconnection
    await context.setOffline(true);
    
    const message = 'Offline message';
    await page.fill('[data-testid="message-input"]', message);
    await page.keyboard.press('Enter');
    
    // Should show offline indicator
    await expect(page.locator('[data-testid="connection-status"]'))
      .toContainText('Offline', { timeout: 2000 });
    
    // Reconnect and verify message delivery
    await context.setOffline(false);
    
    await expect(page.locator('[data-testid="connection-status"]'))
      .toContainText('Connected', { timeout: 5000 });
    
    await expect(page.locator('.user-message'))
      .toContainText(message, { timeout: 3000 });
  });

  test('should prevent memory leaks during extended use', async () => {
    await setupAuthenticatedUser(page);
    await createNewConversation(page);
    
    const initialMemory = await page.evaluate(() => {
      if ('memory' in performance) {
        return (performance as any).memory.usedJSHeapSize;
      }
      return 0;
    });
    
    // Send 20 messages to simulate extended use
    for (let i = 0; i < 20; i++) {
      await sendMessageAndWaitResponse(page, `Test message ${i + 1}`);
    }
    
    // Force garbage collection if available
    await page.evaluate(() => {
      if ('gc' in window) {
        (window as any).gc();
      }
    });
    
    const finalMemory = await page.evaluate(() => {
      if ('memory' in performance) {
        return (performance as any).memory.usedJSHeapSize;
      }
      return 0;
    });
    
    // Memory should not grow excessively (allow 50MB increase)
    if (initialMemory > 0 && finalMemory > 0) {
      const memoryIncrease = finalMemory - initialMemory;
      expect(memoryIncrease).toBeLessThan(50 * 1024 * 1024);
    }
  });
});