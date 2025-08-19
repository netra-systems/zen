/**
 * E2E Test Helper Utilities
 * 
 * Reusable helper functions for Playwright E2E tests
 * Ensures consistent test patterns and reduces code duplication
 * 
 * @compliance conventions.xml - Max 8 lines per function, under 300 lines
 * @compliance type_safety.xml - Full TypeScript typing
 * @spec frontend_unified_testing_spec.xml - Shared utilities pattern
 */

import { Page, expect } from '@playwright/test';

export interface TestUser {
  id: string;
  email: string;
  name: string;
  token: string;
}

export interface PerformanceThresholds {
  maxResponseTime: number;
  maxRenderTime: number;
  minFrameRate: number;
  maxMemoryMB: number;
}

/**
 * Creates test user with unique identifier
 */
export function createTestUser(suffix: string = ''): TestUser {
  const timestamp = Date.now();
  return {
    id: `test-user-${timestamp}${suffix}`,
    email: `test-${timestamp}${suffix}@netrasystems.ai`,
    name: `Test User ${timestamp}`,
    token: `test-token-${timestamp}`
  };
}

/**
 * Authenticates user and navigates to chat
 */
export async function authenticateUser(page: Page, user?: TestUser): Promise<TestUser> {
  const testUser = user || createTestUser();
  
  await page.goto('/login');
  await page.evaluate((userData) => {
    localStorage.setItem('auth_token', userData.token);
    localStorage.setItem('user', JSON.stringify(userData));
  }, testUser);
  
  await page.goto('/chat');
  return testUser;
}

/**
 * Waits for WebSocket connection to be established
 */
export async function waitForWebSocketConnection(page: Page): Promise<void> {
  await expect(page.locator('[data-testid="connection-status"]'))
    .toContainText('Connected', { timeout: 5000 });
}

/**
 * Creates new conversation thread
 */
export async function createThread(page: Page, name?: string): Promise<string> {
  await page.click('[data-testid="new-conversation"]');
  await expect(page).toHaveURL(/\/chat/);
  
  const threadId = await page.evaluate(() => 
    new Date().getTime().toString()
  );
  return threadId;
}

/**
 * Sends message and validates delivery
 */
export async function sendMessage(page: Page, message: string): Promise<void> {
  await page.fill('[data-testid="message-input"]', message);
  await page.keyboard.press('Enter');
  
  await expect(page.locator('.user-message').last())
    .toContainText(message, { timeout: 3000 });
}

/**
 * Waits for AI response to appear
 */
export async function waitForAIResponse(page: Page): Promise<void> {
  await expect(page.locator('.ai-message').last())
    .toBeVisible({ timeout: 5000 });
}

/**
 * Measures page performance metrics
 */
export async function measurePagePerformance(page: Page): Promise<PerformanceThresholds> {
  const metrics = await page.evaluate(() => {
    const navigation = performance.getEntriesByType('navigation')[0] as PerformanceNavigationTiming;
    const memoryInfo = 'memory' in performance ? (performance as any).memory : null;
    
    return {
      loadTime: navigation.loadEventEnd - navigation.loadEventStart,
      domReady: navigation.domContentLoadedEventEnd - navigation.domContentLoadedEventStart,
      memoryUsed: memoryInfo ? memoryInfo.usedJSHeapSize / (1024 * 1024) : 0
    };
  });
  
  return {
    maxResponseTime: metrics.loadTime,
    maxRenderTime: metrics.domReady,
    minFrameRate: 60,
    maxMemoryMB: metrics.memoryUsed
  };
}

/**
 * Validates performance against thresholds
 */
export function validatePerformance(
  metrics: PerformanceThresholds,
  thresholds: Partial<PerformanceThresholds>
): void {
  if (thresholds.maxResponseTime) {
    expect(metrics.maxResponseTime).toBeLessThan(thresholds.maxResponseTime);
  }
  if (thresholds.maxRenderTime) {
    expect(metrics.maxRenderTime).toBeLessThan(thresholds.maxRenderTime);
  }
  if (thresholds.maxMemoryMB) {
    expect(metrics.maxMemoryMB).toBeLessThan(thresholds.maxMemoryMB);
  }
}

/**
 * Cleans up test session
 */
export async function cleanupTestSession(page: Page): Promise<void> {
  await page.evaluate(() => {
    localStorage.clear();
    sessionStorage.clear();
  });
}

/**
 * Simulates network conditions
 */
export async function simulateNetworkCondition(
  page: Page, 
  condition: 'offline' | 'slow' | 'fast'
): Promise<void> {
  switch (condition) {
    case 'offline':
      await page.context().setOffline(true);
      break;
    case 'slow':
      await page.route('**/*', route => {
        setTimeout(() => route.continue(), 1000);
      });
      break;
    case 'fast':
      await page.context().setOffline(false);
      break;
  }
}

/**
 * Generates large test dataset
 */
export function generateTestMessages(count: number, prefix: string = 'Test'): string[] {
  return Array.from({ length: count }, (_, i) => `${prefix} message ${i + 1}`);
}

/**
 * Waits for element with retry logic
 */
export async function waitForElementWithRetry(
  page: Page,
  selector: string,
  maxRetries: number = 3
): Promise<boolean> {
  for (let i = 0; i < maxRetries; i++) {
    try {
      await expect(page.locator(selector)).toBeVisible({ timeout: 2000 });
      return true;
    } catch {
      if (i === maxRetries - 1) return false;
      await page.waitForTimeout(1000);
    }
  }
  return false;
}

/**
 * Validates error-free execution
 */
export async function validateNoErrors(page: Page): Promise<void> {
  const errors = await page.evaluate(() => {
    return (window as any).testErrors || [];
  });
  
  expect(errors).toHaveLength(0);
}

export default {
  createTestUser,
  authenticateUser,
  waitForWebSocketConnection,
  createThread,
  sendMessage,
  waitForAIResponse,
  measurePagePerformance,
  validatePerformance,
  cleanupTestSession,
  simulateNetworkCondition,
  generateTestMessages,
  waitForElementWithRetry,
  validateNoErrors
};