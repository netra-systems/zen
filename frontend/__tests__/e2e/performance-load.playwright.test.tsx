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
import {
  authenticateUser,
  createThread,
  sendMessage,
  measurePagePerformance,
  validatePerformance,
  cleanupTestSession
} from './utils/e2e-test-helpers';
import {
  createBulkThreads,
  populateThreadWithMessages,
  measureThreadSwitchPerformance,
  testScrollPerformance,
  monitorFrameRate,
  validateUIResponsiveness,
  performRapidInteractions,
  type PerformanceMetrics,
  type LoadTestData
} from './utils/performance-test-helpers';

/**
 * Sets up load testing environment
 */
async function setupLoadTestEnvironment(page: Page): Promise<void> {
  await authenticateUser(page);
  await page.waitForLoadState('networkidle');
}

/**
 * Validates performance metrics against thresholds
 */
function validateLoadTestMetrics(
  data: LoadTestData,
  count: number,
  timeLimit: number
): void {
  expect(data.threadsCreated).toBeGreaterThan(count * 0.9);
  expect(data.totalTime).toBeLessThan(timeLimit);
  expect(data.errors.length).toBeLessThan(count * 0.1);
}

/**
 * Tests mixed load conditions
 */
async function testMixedLoadConditions(page: Page): Promise<PerformanceMetrics[]> {
  const threads = [100, 500, 1000, 2000, 5000];
  const performanceData: PerformanceMetrics[] = [];
  
  for (let i = 0; i < threads.length; i++) {
    await createThread(page);
    
    const startTime = Date.now();
    await populateThreadWithMessages(page, threads[i]);
    const renderTime = Date.now() - startTime;
    
    const switchTime = await measureThreadSwitchPerformance(page, 5);
    const scrollTime = await testScrollPerformance(page);
    const pageMetrics = await measurePagePerformance(page);
    const frameRate = await monitorFrameRate(page);
    
    performanceData.push({
      renderTime,
      threadSwitchTime: switchTime,
      scrollPerformance: scrollTime,
      memoryUsage: pageMetrics.maxMemoryMB,
      frameRate
    });
  }
  
  return performanceData;
}

test.describe('Performance Load E2E', () => {
  let context: BrowserContext;
  let page: Page;

  test.beforeEach(async ({ browser }) => {
    context = await browser.newContext();
    page = await context.newPage();
    await setupLoadTestEnvironment(page);
  });

  test.afterEach(async () => {
    await cleanupTestSession(page);
    await context.close();
  });

  test('should handle 1000+ threads without performance degradation', async () => {
    const threadCount = 1000;
    
    const loadData = await createBulkThreads(page, threadCount);
    validateLoadTestMetrics(loadData, threadCount, 300000);
    
    const avgSwitchTime = await measureThreadSwitchPerformance(page, 20);
    expect(avgSwitchTime).toBeLessThan(500);
    
    const memoryMetrics = await measurePagePerformance(page);
    expect(memoryMetrics.maxMemoryMB).toBeLessThan(500);
  });

  test('should handle 10000+ messages with smooth scrolling', async () => {
    const messageCount = 10000;
    
    await createThread(page);
    const populationTime = await populateThreadWithMessages(page, messageCount);
    expect(populationTime).toBeLessThan(600000);
    
    const scrollTime = await testScrollPerformance(page);
    expect(scrollTime).toBeLessThan(5000);
    
    const frameRate = await monitorFrameRate(page);
    expect(frameRate).toBeGreaterThan(55);
    
    const isResponsive = await validateUIResponsiveness(page);
    expect(isResponsive).toBe(true);
  });

  test('should maintain performance with mixed load conditions', async () => {
    const performanceData = await testMixedLoadConditions(page);
    
    const avgRenderTime = performanceData.reduce((sum, p) => sum + p.renderTime, 0) / performanceData.length;
    const avgFrameRate = performanceData.reduce((sum, p) => sum + p.frameRate, 0) / performanceData.length;
    const maxMemory = Math.max(...performanceData.map(p => p.memoryUsage));
    
    expect(avgRenderTime).toBeLessThan(60000);
    expect(avgFrameRate).toBeGreaterThan(50);
    expect(maxMemory).toBeLessThan(500);
  });

  test('should handle rapid user interactions under load', async () => {
    await createBulkThreads(page, 100);
    
    const totalTime = await performRapidInteractions(page, 100);
    expect(totalTime).toBeLessThan(30000);
    
    const isResponsive = await validateUIResponsiveness(page);
    expect(isResponsive).toBe(true);
  });

  test('should recover gracefully from performance bottlenecks', async () => {
    await createBulkThreads(page, 500);
    await createThread(page);
    
    // Add very large message content
    const largeContent = 'A'.repeat(100000);
    await sendMessage(page, largeContent);
    
    await expect(page.locator('.user-message'))
      .toContainText('AAAA', { timeout: 10000 });
    
    // Test recovery
    await sendMessage(page, 'Recovery test');
    await expect(page.locator('.user-message').last())
      .toContainText('Recovery test', { timeout: 5000 });
    
    const frameRate = await monitorFrameRate(page);
    expect(frameRate).toBeGreaterThan(45);
  });

  test('should maintain data integrity under concurrent load', async () => {
    const threadCount = 100;
    const expectedThreads: string[] = [];
    
    for (let i = 0; i < threadCount; i++) {
      await createThread(page);
      
      const threadName = `Load Test Thread ${i + 1}`;
      expectedThreads.push(threadName);
      
      await sendMessage(page, `Message for thread ${i + 1}`);
    }
    
    // Verify threads exist
    for (let i = 0; i < Math.min(threadCount, 20); i++) {
      const threadIndex = i + 1;
      await expect(page.locator('.thread-item'))
        .toContainText(`thread ${threadIndex}`, { timeout: 1000 });
    }
    
    // Random sampling verification
    const sampleIndices = [0, 25, 50, 75, 99].filter(i => i < threadCount);
    for (const index of sampleIndices) {
      await page.click(`.thread-item:nth-child(${index + 1})`);
      await expect(page.locator('.user-message'))
        .toContainText(`Message for thread ${index + 1}`, { timeout: 2000 });
    }
  });

  test('should validate performance regression prevention', async () => {
    // Baseline measurement
    const baselineMetrics = await measurePagePerformance(page);
    
    // Apply load
    await createBulkThreads(page, 200);
    await populateThreadWithMessages(page, 1000);
    
    // Measure under load
    const loadMetrics = await measurePagePerformance(page);
    const frameRate = await monitorFrameRate(page);
    
    // Validate no significant degradation
    const memoryIncrease = loadMetrics.maxMemoryMB - baselineMetrics.maxMemoryMB;
    expect(memoryIncrease).toBeLessThan(200); // Allow reasonable increase
    expect(frameRate).toBeGreaterThan(50); // Maintain good performance
    
    const responsiveness = await validateUIResponsiveness(page);
    expect(responsiveness).toBe(true);
  });
});