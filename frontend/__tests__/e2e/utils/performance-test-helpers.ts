/**
 * Performance Test Helper Utilities
 * 
 * Specialized helpers for performance and load testing scenarios
 * Supports bulk operations and performance measurement
 * 
 * @compliance conventions.xml - Max 8 lines per function, under 300 lines
 * @compliance type_safety.xml - Full TypeScript typing
 */

import { Page, expect } from '@playwright/test';

export interface PerformanceMetrics {
  renderTime: number;
  threadSwitchTime: number;
  scrollPerformance: number;
  memoryUsage: number;
  frameRate: number;
}

export interface LoadTestData {
  threadsCreated: number;
  messagesCreated: number;
  totalTime: number;
  errors: string[];
}

/**
 * Creates bulk threads for load testing
 */
export async function createBulkThreads(
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
 * Populates thread with many messages
 */
export async function populateThreadWithMessages(
  page: Page, 
  messageCount: number
): Promise<number> {
  const startTime = Date.now();
  
  for (let i = 0; i < messageCount; i++) {
    const message = `Load test message ${i + 1}`;
    
    await page.fill('[data-testid="message-input"]', message);
    await page.keyboard.press('Enter');
    
    await expect(page.locator('.user-message').last())
      .toContainText(message, { timeout: 1000 });
    
    if (i > 0 && i % 100 === 0) {
      await page.waitForTimeout(50);
    }
  }
  
  return Date.now() - startTime;
}

/**
 * Measures thread switching performance
 */
export async function measureThreadSwitchPerformance(
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
export async function testScrollPerformance(page: Page): Promise<number> {
  const startTime = performance.now();
  
  for (let i = 0; i < 50; i++) {
    await page.keyboard.press('PageDown');
    await page.waitForTimeout(16);
  }
  
  await page.keyboard.press('Home');
  return performance.now() - startTime;
}

/**
 * Monitors frame rate during operations
 */
export async function monitorFrameRate(page: Page): Promise<number> {
  const frameRate = await page.evaluate(async () => {
    const frames: number[] = [];
    let lastFrame = performance.now();
    
    for (let i = 0; i < 120; i++) {
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
export async function validateUIResponsiveness(page: Page): Promise<boolean> {
  const startTime = Date.now();
  
  await page.click('[data-testid="new-conversation"]');
  await page.fill('[data-testid="message-input"]', 'Responsiveness test');
  await page.keyboard.press('Enter');
  
  const responseTime = Date.now() - startTime;
  return responseTime < 500;
}

/**
 * Performs rapid interaction sequence
 */
export async function performRapidInteractions(
  page: Page,
  count: number
): Promise<number> {
  const interactions = [
    () => page.click('[data-testid="new-conversation"]'),
    () => page.fill('[data-testid="message-input"]', 'Quick message'),
    () => page.keyboard.press('Enter'),
    () => page.click('.thread-item:nth-child(1)'),
    () => page.keyboard.press('PageDown'),
  ];
  
  const startTime = Date.now();
  
  for (let i = 0; i < count; i++) {
    const interaction = interactions[i % interactions.length];
    await interaction();
    await page.waitForTimeout(10);
  }
  
  return Date.now() - startTime;
}

export default {
  createBulkThreads,
  populateThreadWithMessages,
  measureThreadSwitchPerformance,
  testScrollPerformance,
  monitorFrameRate,
  validateUIResponsiveness,
  performRapidInteractions
};