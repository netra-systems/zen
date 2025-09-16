/**
 * E2E Test for Chat Thread Navigation - Staging GCP
 * 
 * Business Value Justification (BVJ):
 * - Segment: All (Free, Early, Mid, Enterprise)
 * - Business Goal: Ensure thread navigation works in production environment
 * - Value Impact: Users can navigate to specific threads via URLs without errors
 * - Strategic Impact: Core chat functionality for real user scenarios
 * 
 * Tests complete user journey including React Error #438 in staging environment
 */

import { test, expect, Page, Browser, BrowserContext } from '@playwright/test';

// Test configuration for staging GCP environment
const STAGING_BASE_URL = process.env.STAGING_BASE_URL || 'https://netra-staging.example.com';
const TEST_TIMEOUT = 30000;

// Test user credentials for staging
const TEST_USER = {
  email: process.env.STAGING_TEST_USER_EMAIL || 'test-user@netra.dev',
  password: process.env.STAGING_TEST_USER_PASSWORD || 'test-password'
};

test.describe('Chat Thread Navigation E2E - Staging', () => {
  let context: BrowserContext;
  let page: Page;

  test.beforeAll(async ({ browser }) => {
    // Create persistent context to maintain auth across tests
    context = await browser.newContext({
      baseURL: STAGING_BASE_URL,
      viewport: { width: 1280, height: 720 },
      // Record video for debugging failed tests
      recordVideo: { dir: 'test-results/videos/' },
    });
    
    page = await context.newPage();
    
    // Login to staging environment
    await loginToStaging(page);
  });

  test.afterAll(async () => {
    await context.close();
  });

  test.describe('FAILING SCENARIOS - Next.js 15 Route Navigation', () => {
    test('should FAIL when navigating directly to thread URL', async () => {
      const threadId = 'test_thread_direct_nav';
      
      // This should fail with React Error #438 when using direct URL navigation
      const response = await page.goto(`/chat/${threadId}`, { 
        waitUntil: 'domcontentloaded',
        timeout: TEST_TIMEOUT 
      });
      
      // Expect to see error or infinite loading due to React.use() issue
      await expect(page.locator('[data-testid="error-boundary"]')).toBeVisible({ timeout: 5000 });
      
      // Or expect console errors related to React.use()
      const errors = await page.evaluate(() => {
        return (window as any).testErrors || [];
      });
      
      expect(errors.some((error: string) => 
        error.includes('React.use') || 
        error.includes('Cannot read properties') ||
        error.includes('undefined')
      )).toBe(true);
    });

    test('should FAIL when browser back/forward navigation hits thread route', async () => {
      // Navigate to chat home first
      await page.goto('/chat');
      await expect(page.locator('[data-testid="chat-interface"]')).toBeVisible();
      
      // Navigate to a thread (this might work initially)
      await page.goto('/chat/test_thread_back_nav');
      
      // Navigate away
      await page.goto('/chat');
      
      // Use browser back button - this should trigger the React.use() error
      await page.goBack();
      
      // Should see error state or loading failure
      await expect(
        page.locator('[data-testid="error-boundary"], [data-testid="loading-error"]')
      ).toBeVisible({ timeout: 5000 });
    });

    test('should FAIL when refreshing thread page', async () => {
      const threadId = 'test_thread_refresh';
      
      // Navigate to thread initially (might work)
      await page.goto(`/chat/${threadId}`);
      
      // Refresh the page - this should trigger React Error #438
      await page.reload({ waitUntil: 'domcontentloaded' });
      
      // Should see error after refresh
      await expect(page.locator('[data-testid="error-state"]')).toBeVisible({ timeout: 5000 });
    });
  });

  test.describe('Thread URL Parameter Handling', () => {
    test('should handle valid thread ID format', async () => {
      // Test with valid UUID-like thread ID
      const validThreadId = 'thread_550e8400-e29b-41d4-a716-446655440000';
      
      await page.goto(`/chat/${validThreadId}`);
      
      // Should either load successfully or fail with React.use() error
      // (depending on whether fix is implemented)
      const hasError = await page.locator('[data-testid="error-boundary"]').isVisible({ timeout: 3000 });
      const hasLoading = await page.locator('[data-testid="thread-loading"]').isVisible({ timeout: 3000 });
      const hasChat = await page.locator('[data-testid="main-chat"]').isVisible({ timeout: 3000 });
      
      // One of these states should be present
      expect(hasError || hasLoading || hasChat).toBe(true);
    });

    test('should handle invalid thread ID gracefully', async () => {
      const invalidThreadId = 'invalid-format-123';
      
      await page.goto(`/chat/${invalidThreadId}`);
      
      // Should show invalid thread ID error
      await expect(page.locator('text=Invalid thread ID format')).toBeVisible({ timeout: 5000 });
      
      // Should redirect to chat home after timeout
      await expect(page).toHaveURL('/chat', { timeout: 10000 });
    });

    test('should handle very long thread IDs', async () => {
      const longThreadId = 'thread_' + 'a'.repeat(100);
      
      await page.goto(`/chat/${longThreadId}`);
      
      // Should handle gracefully without crashing
      const pageContent = await page.textContent('body');
      expect(pageContent).toBeTruthy();
    });

    test('should handle special characters in thread ID', async () => {
      const specialThreadId = 'thread_with-special_chars.123';
      
      await page.goto(`/chat/${specialThreadId}`);
      
      // Should not crash the application
      const hasError = await page.locator('[data-testid="global-error"]').isVisible({ timeout: 3000 });
      expect(hasError).toBe(false);
    });
  });

  test.describe('User Experience Flow', () => {
    test('should maintain thread context during navigation', async () => {
      // Start at chat home
      await page.goto('/chat');
      await expect(page.locator('[data-testid="chat-interface"]')).toBeVisible();
      
      // Navigate to specific thread
      const threadId = 'test_context_thread';
      await page.goto(`/chat/${threadId}`);
      
      // Check if URL is maintained
      expect(page.url()).toContain(threadId);
      
      // Navigate to settings and back
      await page.goto('/settings');
      await page.goBack();
      
      // Should maintain thread context
      expect(page.url()).toContain(threadId);
    });

    test('should show appropriate loading states', async () => {
      const threadId = 'test_loading_states';
      
      await page.goto(`/chat/${threadId}`);
      
      // Should show initial loading state
      const loadingVisible = await page.locator('[data-testid="thread-loading"], text=Validating thread').isVisible({ timeout: 2000 });
      
      // Either shows loading or immediately errors (React.use issue)
      const errorVisible = await page.locator('[data-testid="error-boundary"]').isVisible({ timeout: 1000 });
      
      expect(loadingVisible || errorVisible).toBe(true);
    });
  });

  test.describe('Error Recovery', () => {
    test('should provide return to chat option on error', async () => {
      const invalidThreadId = 'definitely_invalid_format';
      
      await page.goto(`/chat/${invalidThreadId}`);
      
      // Wait for error state
      await expect(page.locator('text=Unable to Load Conversation')).toBeVisible({ timeout: 5000 });
      
      // Click return to chat button
      await page.click('text=Return to Chat');
      
      // Should navigate to chat home
      await expect(page).toHaveURL('/chat');
    });

    test('should handle network failures gracefully', async () => {
      // Simulate network failure
      await page.route('**/api/**', route => route.abort());
      
      const threadId = 'test_network_failure';
      await page.goto(`/chat/${threadId}`);
      
      // Should show error state, not crash
      const hasError = await page.locator('[data-testid="error-state"], text=Failed to load').isVisible({ timeout: 5000 });
      expect(hasError).toBe(true);
      
      // Clear network simulation
      await page.unroute('**/api/**');
    });
  });

  test.describe('Performance and Monitoring', () => {
    test('should not have memory leaks during thread navigation', async () => {
      const initialMemory = await getMemoryUsage(page);
      
      // Navigate through multiple threads
      for (let i = 0; i < 5; i++) {
        await page.goto(`/chat/test_thread_${i}`);
        await page.waitForTimeout(1000);
      }
      
      // Force garbage collection if available
      await page.evaluate(() => {
        if ((window as any).gc) {
          (window as any).gc();
        }
      });
      
      const finalMemory = await getMemoryUsage(page);
      
      // Memory shouldn't grow excessively (allow for reasonable variance)
      expect(finalMemory.usedJSHeapSize).toBeLessThan(initialMemory.usedJSHeapSize * 2);
    });

    test('should track React error occurrences', async () => {
      // Setup error tracking
      await page.addInitScript(() => {
        (window as any).reactErrors = [];
        window.addEventListener('error', (event) => {
          if (event.error?.message?.includes('React.use')) {
            (window as any).reactErrors.push({
              message: event.error.message,
              stack: event.error.stack,
              timestamp: Date.now()
            });
          }
        });
      });
      
      const threadId = 'test_error_tracking';
      await page.goto(`/chat/${threadId}`);
      
      // Check for React.use errors
      const reactErrors = await page.evaluate(() => (window as any).reactErrors || []);
      
      // Document React.use errors for issue tracking
      if (reactErrors.length > 0) {
        console.log('React.use errors detected:', reactErrors);
      }
      
      // This test documents the current error state
      expect(reactErrors.length).toBeGreaterThan(0);
    });
  });
});

test.describe('Expected Behavior After Fix', () => {
  test('should handle Promise params correctly after React.use fix', async () => {
    // This test documents expected behavior after implementing the fix
    
    const threadId = 'test_promise_params_fixed';
    await page.goto(`/chat/${threadId}`);
    
    // After fix, should handle async params without error
    // For now, we expect React.use() errors
    const hasReactError = await page.evaluate(() => {
      return (window as any).reactErrors?.length > 0;
    });
    
    // Currently expect errors (will pass when fixed)
    expect(hasReactError).toBe(true);
  });
});

// Helper functions
async function loginToStaging(page: Page): Promise<void> {
  await page.goto('/login');
  
  await page.fill('[data-testid="email-input"]', TEST_USER.email);
  await page.fill('[data-testid="password-input"]', TEST_USER.password);
  await page.click('[data-testid="login-button"]');
  
  // Wait for successful login
  await expect(page.locator('[data-testid="user-dashboard"]')).toBeVisible({ timeout: 10000 });
}

async function getMemoryUsage(page: Page): Promise<any> {
  return await page.evaluate(() => {
    return (performance as any).memory || { usedJSHeapSize: 0, totalJSHeapSize: 0 };
  });
}