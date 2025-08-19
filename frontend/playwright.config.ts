/**
 * Playwright Configuration for Netra Apex E2E Tests
 * 
 * Production-ready configuration following business-critical requirements
 * Optimized for 30-second test completion and reliable CI/CD execution
 * 
 * @compliance conventions.xml - Configuration under 300 lines
 * @compliance type_safety.xml - Full TypeScript configuration
 * @spec frontend_unified_testing_spec.xml - E2E test requirements
 */

import { defineConfig, devices } from '@playwright/test';

/**
 * Base URL configuration
 */
const getBaseURL = (): string => {
  return process.env.BASE_URL || 'http://localhost:3000';
};

/**
 * Test timeout configuration
 */
const getTestTimeout = (): number => {
  return process.env.CI ? 45000 : 30000; // Slightly longer for CI
};

/**
 * Worker configuration for parallel execution
 */
const getWorkerConfig = (): number => {
  return process.env.CI ? 2 : 4; // Fewer workers in CI to avoid resource issues
};

/**
 * Retry configuration based on environment
 */
const getRetryConfig = (): number => {
  return process.env.CI ? 2 : 1; // More retries in CI
};

export default defineConfig({
  testDir: './__tests__/e2e',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: getRetryConfig(),
  workers: getWorkerConfig(),
  
  reporter: [
    ['html'],
    ['json', { outputFile: 'test-results/e2e-results.json' }],
    ['junit', { outputFile: 'test-results/e2e-junit.xml' }]
  ],
  
  use: {
    baseURL: getBaseURL(),
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
    
    // Global test timeout
    actionTimeout: 10000,
    navigationTimeout: 15000,
  },
  
  timeout: getTestTimeout(),
  
  expect: {
    timeout: 5000,
  },
  
  projects: [
    {
      name: 'chromium',
      use: { 
        ...devices['Desktop Chrome'],
        viewport: { width: 1280, height: 720 },
      },
    },
    
    {
      name: 'firefox',
      use: { 
        ...devices['Desktop Firefox'],
        viewport: { width: 1280, height: 720 },
      },
    },
    
    {
      name: 'webkit',
      use: { 
        ...devices['Desktop Safari'],
        viewport: { width: 1280, height: 720 },
      },
    },
    
    // Mobile testing
    {
      name: 'Mobile Chrome',
      use: { ...devices['Pixel 5'] },
    },
    
    {
      name: 'Mobile Safari',
      use: { ...devices['iPhone 12'] },
    },
  ],
  
  webServer: {
    command: 'npm run dev',
    url: getBaseURL(),
    reuseExistingServer: !process.env.CI,
    timeout: 120000,
  },
  
  outputDir: 'test-results/',
  
  // Global setup for test environment
  globalSetup: undefined, // Can be added later for auth setup
  globalTeardown: undefined, // Can be added later for cleanup
});