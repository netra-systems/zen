/**
 * E2E Test Helpers for Playwright Tests
 * 
 * Provides utilities for authentication, performance measurement,
 * and test user management for complete E2E workflows
 */

import { Page, BrowserContext } from '@playwright/test';

// Test user interface
export interface TestUser {
  id: string;
  email: string;
  name: string;
  token?: string;
}

// Performance thresholds interface
export interface PerformanceThresholds {
  loginTime: number;
  messageResponseTime: number;
  pageLoadTime: number;
  websocketConnectionTime: number;
}

// Default performance thresholds
export const DEFAULT_THRESHOLDS: PerformanceThresholds = {
  loginTime: 3000,
  messageResponseTime: 5000,
  pageLoadTime: 2000,
  websocketConnectionTime: 1000
};

/**
 * Creates a test user for E2E scenarios
 */
export async function createTestUser(): Promise<TestUser> {
  return {
    id: `test-user-${Date.now()}`,
    email: 'e2e.test@example.com',
    name: 'E2E Test User'
  };
}

/**
 * Authenticates user in browser context
 */
export async function authenticateUser(page: Page): Promise<TestUser> {
  const testUser = await createTestUser();
  
  // Navigate to login page
  await page.goto('/auth/login');
  
  // Wait for login form
  await page.waitForSelector('[data-testid="login-form"]', { timeout: 5000 });
  
  // Fill and submit login
  await page.fill('input[type="email"]', testUser.email);
  await page.fill('input[type="password"]', 'test-password');
  await page.click('button[type="submit"]');
  
  // Wait for redirect to chat
  await page.waitForURL('/chat', { timeout: 10000 });
  
  return testUser;
}

/**
 * Creates a new thread in the chat interface
 */
export async function createThread(page: Page, title?: string): Promise<string> {
  await page.click('[data-testid="new-thread-button"]');
  await page.waitForSelector('[data-testid="thread-list"]');
  
  // Return the active thread ID
  const threadElement = await page.waitForSelector('[data-testid="active-thread"]');
  const threadId = await threadElement.getAttribute('data-thread-id');
  
  return threadId || 'default-thread';
}

/**
 * Sends a message in the chat interface
 */
export async function sendMessage(page: Page, message: string): Promise<void> {
  await page.fill('[data-testid="message-input"]', message);
  await page.click('[data-testid="send-button"]');
}

/**
 * Waits for AI response in chat
 */
export async function waitForAIResponse(page: Page, timeout: number = 10000): Promise<void> {
  await page.waitForSelector('[data-testid="ai-message"]', { timeout });
}

/**
 * Waits for WebSocket connection to be established
 */
export async function waitForWebSocketConnection(page: Page, timeout: number = 5000): Promise<void> {
  // Wait for connection indicator
  await page.waitForSelector('[data-testid="websocket-connected"]', { timeout });
}

/**
 * Measures page performance metrics
 */
export async function measurePagePerformance(page: Page): Promise<{
  loadTime: number;
  domContentLoaded: number;
  firstContentfulPaint: number;
}> {
  const performanceMetrics = await page.evaluate(() => {
    const navigation = performance.getEntriesByType('navigation')[0] as PerformanceNavigationTiming;
    const paint = performance.getEntriesByType('paint');
    
    return {
      loadTime: navigation.loadEventEnd - navigation.navigationStart,
      domContentLoaded: navigation.domContentLoadedEventEnd - navigation.navigationStart,
      firstContentfulPaint: paint.find(p => p.name === 'first-contentful-paint')?.startTime || 0
    };
  });
  
  return performanceMetrics;
}

/**
 * Validates performance against thresholds
 */
export function validatePerformance(
  metrics: { loadTime: number },
  thresholds: Partial<PerformanceThresholds> = {}
): boolean {
  const finalThresholds = { ...DEFAULT_THRESHOLDS, ...thresholds };
  return metrics.loadTime <= finalThresholds.pageLoadTime;
}

/**
 * Cleans up test session
 */
export async function cleanupTestSession(page: Page): Promise<void> {
  try {
    // Clear local storage
    await page.evaluate(() => {
      localStorage.clear();
      sessionStorage.clear();
    });
    
    // Navigate to logout or home
    await page.goto('/');
  } catch (error) {
    // Ignore cleanup errors
  }
}

/**
 * Simulates network conditions for testing
 */
export async function simulateNetworkCondition(
  page: Page,
  condition: 'slow' | 'fast' | 'offline'
): Promise<void> {
  const conditions = {
    slow: { downloadThroughput: 500000, uploadThroughput: 500000, latency: 200 },
    fast: { downloadThroughput: 50000000, uploadThroughput: 50000000, latency: 10 },
    offline: { downloadThroughput: 0, uploadThroughput: 0, latency: 0 }
  };
  
  const context = page.context();
  await context.route('**/*', route => {
    if (condition === 'offline') {
      route.abort();
    } else {
      route.continue();
    }
  });
}

/**
 * Waits for element with retry logic
 */
export async function waitForElementWithRetry(
  page: Page,
  selector: string,
  timeout: number = 5000,
  retries: number = 3
): Promise<void> {
  for (let i = 0; i < retries; i++) {
    try {
      await page.waitForSelector(selector, { timeout });
      return;
    } catch (error) {
      if (i === retries - 1) throw error;
      await page.waitForTimeout(1000);
    }
  }
}

/**
 * Takes screenshot for debugging
 */
export async function takeDebugScreenshot(page: Page, name: string): Promise<void> {
  await page.screenshot({ 
    path: `__tests__/screenshots/${name}-${Date.now()}.png`,
    fullPage: true 
  });
}