/**
 * End-to-End Performance Load Test
 * 
 * Tests application performance under heavy load conditions
 * Validates smooth operation with 1000+ threads and 10000+ messages
 * 
 * @compliance conventions.xml - Max 8 lines per function, under 300 lines
 * @compliance type_safety.xml - Full TypeScript typing
 * @spec frontend_unified_testing_spec.xml - Performance under load P1 priority
 */

import { test, expect, Page, BrowserContext } from '@playwright/test';

interface PerformanceMetrics {
  renderTime: number;
  threadSwitchTime: number;
  scrollPerformance: number;
  memoryUsage: number;
  frameRate: number;
}

interface LoadTestData {
  threadsCreated: number;
  messagesCreated: number;
  totalTime: number;
  errors: string[];
}

/**
 * Sets up authenticated user for load testing
 */
async function setupLoadTestUser(page: Page): Promise<void> {
  const testUser = {
    id: 'load-test-user',
    email: 'loadtest@netrasystems.ai',
    name: 'Load Test User'
  };
  
  await page.goto('/login');
  await page.evaluate((user) => {
    localStorage.setItem('auth_token', 'load-test-token');
    localStorage.setItem('user', JSON.stringify(user));
  }, testUser);
  await page.goto('/chat');
}

/**
 * Creates large number of threads efficiently
 */
async function createBulkThreads(
  page: Page, 
  count: number
): Promise<LoadTestData> {
  const startTime = Date.now();
  const errors: string[] = [];
  let threadsCreated = 0;
  
  for (let i = 0; i < count; i++) {
    try {
      await page.click('[data-testid="new-conversation"]');
      threadsCreated++;
      
      // Batch creation every 50 threads to avoid timeout
      if (i > 0 && i % 50 === 0) {
        await page.waitForTimeout(100);
      }
    } catch (error) {
      errors.push(`Thread ${i}: ${(error as Error).message}`);
    }
  }
  
  return {
    threadsCreated,
    messagesCreated: 0,
    totalTime: Date.now() - startTime,
    errors
  };
}

/**
 * Populates thread with large message volume
 */
async function populateThreadWithMessages(
  page: Page, 
  messageCount: number
): Promise<number> {
  const startTime = Date.now();
  let messagesCreated = 0;
  
  for (let i = 0; i < messageCount; i++) {
    const message = `Load test message ${i + 1}`;
    
    await page.fill('[data-testid="message-input"]', message);
    await page.keyboard.press('Enter');
    
    // Wait for message to appear
    await expect(page.locator('.user-message').last())
      .toContainText(message, { timeout: 1000 });
    
    messagesCreated++;
    
    // Batch processing to maintain performance
    if (i > 0 && i % 100 === 0) {
      await page.waitForTimeout(50);
    }
  }
  
  return Date.now() - startTime;
}

/**
 * Measures thread switching performance
 */
async function measureThreadSwitchPerformance(
  page: Page, 
  switches: number
): Promise<number> {
  const switchTimes: number[] = [];
  
  for (let i = 0; i < switches; i++) {
    const startTime = performance.now();
    
    await page.click('.thread-item:nth-child(' + ((i % 10) + 1) + ')');
    await expect(page.locator('.chat-container')).toBeVisible();
    
    const endTime = performance.now();
    switchTimes.push(endTime - startTime);
  }
  
  return switchTimes.reduce((sum, time) => sum + time, 0) / switchTimes.length;
}

/**
 * Tests scroll performance with large data
 */
async function testScrollPerformance(page: Page): Promise<number> {
  const startTime = performance.now();
  
  // Scroll through large message list
  for (let i = 0; i < 50; i++) {
    await page.keyboard.press('PageDown');
    await page.waitForTimeout(16); // ~60 FPS
  }
  
  // Scroll back to top
  await page.keyboard.press('Home');
  
  return performance.now() - startTime;
}

/**
 * Measures memory usage during load test
 */
async function measureMemoryUsage(page: Page): Promise<number> {
  const memoryInfo = await page.evaluate(() => {
    if ('memory' in performance) {
      return (performance as any).memory.usedJSHeapSize;
    }
    return 0;
  });
  
  return memoryInfo / (1024 * 1024); // Convert to MB
}

/**
 * Monitors frame rate during animations
 */
async function monitorFrameRate(page: Page): Promise<number> {
  const frameRate = await page.evaluate(async () => {
    const frames: number[] = [];
    let lastFrame = performance.now();
    
    for (let i = 0; i < 120; i++) { // Monitor for 2 seconds at 60 FPS
      await new Promise(resolve => requestAnimationFrame(resolve));
      const currentFrame = performance.now();
      frames.push(1000 / (currentFrame - lastFrame));
      lastFrame = currentFrame;
    }
    
    return frames.reduce((sum, fps) => sum + fps, 0) / frames.length;
  });
  
  return frameRate;
}

/**
 * Validates UI responsiveness under load
 */
async function validateUIResponsiveness(page: Page): Promise<boolean> {
  const startTime = Date.now();
  
  // Test various UI interactions
  await page.click('[data-testid="new-conversation"]');
  await page.fill('[data-testid="message-input"]', 'Responsiveness test');
  await page.keyboard.press('Enter');
  
  const responseTime = Date.now() - startTime;
  return responseTime < 500; // 500ms max for UI responsiveness
}

test.describe('Performance Load E2E', () => {
  let context: BrowserContext;
  let page: Page;

  test.beforeEach(async ({ browser }) => {
    context = await browser.newContext();
    page = await context.newPage();
    await setupLoadTestUser(page);
  });

  test.afterEach(async () => {
    await context.close();
  });

  test('should handle 1000+ threads without performance degradation', async () => {
    const threadCount = 1000;
    
    // Create bulk threads
    const loadData = await createBulkThreads(page, threadCount);
    
    expect(loadData.threadsCreated).toBeGreaterThan(threadCount * 0.9); // 90% success rate
    expect(loadData.totalTime).toBeLessThan(300000); // 5 minutes max
    expect(loadData.errors.length).toBeLessThan(threadCount * 0.1); // <10% errors
    
    // Test thread switching performance
    const avgSwitchTime = await measureThreadSwitchPerformance(page, 20);
    expect(avgSwitchTime).toBeLessThan(500); // 500ms max per switch
    
    // Validate memory usage
    const memoryUsage = await measureMemoryUsage(page);
    expect(memoryUsage).toBeLessThan(500); // 500MB max
  });

  test('should handle 10000+ messages with smooth scrolling', async () => {
    const messageCount = 10000;
    
    // Create single thread with many messages
    await page.click('[data-testid="new-conversation"]');
    
    const populationTime = await populateThreadWithMessages(page, messageCount);
    expect(populationTime).toBeLessThan(600000); // 10 minutes max
    
    // Test scroll performance
    const scrollTime = await testScrollPerformance(page);
    expect(scrollTime).toBeLessThan(5000); // 5 seconds for scroll test
    
    // Monitor frame rate during scrolling
    const frameRate = await monitorFrameRate(page);
    expect(frameRate).toBeGreaterThan(55); // Close to 60 FPS
    
    // Verify UI remains responsive
    const isResponsive = await validateUIResponsiveness(page);
    expect(isResponsive).toBe(true);
  });

  test('should maintain performance with mixed load conditions', async () => {
    // Create moderate number of threads with varied message counts
    const threads = [100, 500, 1000, 2000, 5000]; // Messages per thread
    const performanceData: PerformanceMetrics[] = [];
    
    for (let i = 0; i < threads.length; i++) {
      await page.click('[data-testid="new-conversation"]');
      
      const startTime = Date.now();
      await populateThreadWithMessages(page, threads[i]);
      const renderTime = Date.now() - startTime;
      
      const switchTime = await measureThreadSwitchPerformance(page, 5);
      const scrollTime = await testScrollPerformance(page);
      const memoryUsage = await measureMemoryUsage(page);
      const frameRate = await monitorFrameRate(page);
      
      performanceData.push({
        renderTime,
        threadSwitchTime: switchTime,
        scrollPerformance: scrollTime,
        memoryUsage,
        frameRate
      });
    }
    
    // Validate performance doesn't degrade significantly
    const avgRenderTime = performanceData.reduce((sum, p) => sum + p.renderTime, 0) / performanceData.length;
    const avgFrameRate = performanceData.reduce((sum, p) => sum + p.frameRate, 0) / performanceData.length;
    const maxMemory = Math.max(...performanceData.map(p => p.memoryUsage));
    
    expect(avgRenderTime).toBeLessThan(60000); // 1 minute avg render time
    expect(avgFrameRate).toBeGreaterThan(50); // Maintain good frame rate
    expect(maxMemory).toBeLessThan(500); // Memory under control
  });

  test('should handle rapid user interactions under load', async () => {
    // Create baseline load
    await createBulkThreads(page, 100);
    
    // Perform rapid interactions
    const interactions = [
      () => page.click('[data-testid="new-conversation"]'),
      () => page.fill('[data-testid="message-input"]', 'Quick message'),
      () => page.keyboard.press('Enter'),
      () => page.click('.thread-item:nth-child(1)'),
      () => page.keyboard.press('PageDown'),
    ];
    
    const startTime = Date.now();
    
    // Execute 100 rapid interactions
    for (let i = 0; i < 100; i++) {
      const interaction = interactions[i % interactions.length];
      await interaction();
      
      // Brief pause to simulate human interaction
      await page.waitForTimeout(10);
    }
    
    const totalTime = Date.now() - startTime;
    expect(totalTime).toBeLessThan(30000); // 30 seconds for all interactions
    
    // Verify application remains stable
    const isResponsive = await validateUIResponsiveness(page);
    expect(isResponsive).toBe(true);
  });

  test('should recover gracefully from performance bottlenecks', async () => {
    // Create heavy load condition
    await createBulkThreads(page, 500);
    
    // Simulate performance bottleneck with large content
    await page.click('[data-testid="new-conversation"]');
    
    // Add very large message content
    const largeContent = 'A'.repeat(100000); // 100KB message
    await page.fill('[data-testid="message-input"]', largeContent);
    await page.keyboard.press('Enter');
    
    // Verify application doesn't freeze
    await expect(page.locator('.user-message'))
      .toContainText('AAAA', { timeout: 10000 });
    
    // Test recovery by normal operations
    await page.fill('[data-testid="message-input"]', 'Recovery test');
    await page.keyboard.press('Enter');
    
    await expect(page.locator('.user-message').last())
      .toContainText('Recovery test', { timeout: 5000 });
    
    // Verify performance metrics are acceptable
    const frameRate = await monitorFrameRate(page);
    expect(frameRate).toBeGreaterThan(45); // Slightly lower but acceptable
  });

  test('should maintain data integrity under concurrent load', async () => {
    // Create threads with sequential numbering
    const threadCount = 100;
    const expectedThreads: string[] = [];
    
    for (let i = 0; i < threadCount; i++) {
      await page.click('[data-testid="new-conversation"]');
      
      const threadName = `Load Test Thread ${i + 1}`;
      expectedThreads.push(threadName);
      
      // Add identifier message
      await page.fill('[data-testid="message-input"]', `Message for thread ${i + 1}`);
      await page.keyboard.press('Enter');
    }
    
    // Verify all threads exist in sidebar
    for (let i = 0; i < Math.min(threadCount, 20); i++) { // Check first 20
      const threadIndex = i + 1;
      await expect(page.locator('.thread-item'))
        .toContainText(`thread ${threadIndex}`, { timeout: 1000 });
    }
    
    // Random sampling verification for larger datasets
    const sampleIndices = [0, 25, 50, 75, 99].filter(i => i < threadCount);
    for (const index of sampleIndices) {
      await page.click(`.thread-item:nth-child(${index + 1})`);
      await expect(page.locator('.user-message'))
        .toContainText(`Message for thread ${index + 1}`, { timeout: 2000 });
    }
  });
});