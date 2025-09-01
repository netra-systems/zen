import { defineConfig } from 'cypress';

// Get worker ID from environment (set by parallel runner)
const WORKER_ID = process.env.CYPRESS_WORKER_ID || '0';
const IS_PARALLEL = process.env.CYPRESS_PARALLEL === 'true';

// Timeout configurations for parallel execution
const TIMEOUTS = {
  // Individual test timeouts
  defaultCommandTimeout: 60000,     // 60 seconds for commands
  requestTimeout: 60000,            // 60 seconds for requests
  responseTimeout: 60000,           // 60 seconds for responses
  pageLoadTimeout: 180000,          // 3 minutes for page loads
  execTimeout: 120000,              // 2 minutes for cy.exec()
  taskTimeout: 120000,              // 2 minutes for cy.task()
  
  // Test-level timeout (via environment)
  testTimeout: parseInt(process.env.CYPRESS_TEST_TIMEOUT || '300000'), // 5 minutes default
};

export default defineConfig({
  e2e: {
    // Memory management for parallel execution
    experimentalMemoryManagement: true,
    numTestsKeptInMemory: IS_PARALLEL ? 0 : 1, // Keep minimal in memory for parallel
    
    // Session and state management
    experimentalSessionAndOrigin: true,
    
    // Parallel execution optimization
    videoUploadOnPasses: false,
    video: false, // Disable video to save resources
    screenshotOnRunFailure: true,
    
    // Unique folders per worker to avoid conflicts
    screenshotsFolder: `cypress/screenshots/worker-${WORKER_ID}`,
    videosFolder: `cypress/videos/worker-${WORKER_ID}`,
    downloadsFolder: `cypress/downloads/worker-${WORKER_ID}`,
    
    // Test isolation for parallel execution
    testIsolation: true,
    
    setupNodeEvents(on, config) {
      // WebSocket mock tasks
      on('task', {
        log(message) {
          console.log(`[Worker ${WORKER_ID}]`, message);
          return null;
        },
        setupWebSocketMock() {
          return null;
        },
        teardownWebSocketMock() {
          return null;
        },
        sendWebSocketMessage(message: any) {
          return null;
        },
        disconnectWebSocket() {
          return null;
        },
        reconnectWebSocket() {
          return null;
        },
        
        // Parallel execution helpers
        getWorkerId() {
          return WORKER_ID;
        },
        
        // Test timing helpers
        recordTestStart({ testName }: { testName: string }) {
          const startTime = Date.now();
          console.log(`[Worker ${WORKER_ID}] Starting: ${testName}`);
          return startTime;
        },
        
        recordTestEnd({ testName, startTime }: { testName: string, startTime: number }) {
          const duration = Date.now() - startTime;
          console.log(`[Worker ${WORKER_ID}] Completed: ${testName} (${duration}ms)`);
          return duration;
        }
      });
      
      // Apply timeout configurations
      config = {
        ...config,
        ...TIMEOUTS,
        env: {
          ...config.env,
          WORKER_ID,
          IS_PARALLEL,
          BACKEND_URL: process.env.BACKEND_URL || 'http://localhost:8000',
          AUTH_URL: process.env.AUTH_URL || 'http://localhost:8081',
          FRONTEND_URL: process.env.FRONTEND_URL || 'http://localhost:3000',
          REAL_LLM: process.env.REAL_LLM || 'true',
          TEST_TIMEOUT: TIMEOUTS.testTimeout,
        }
      };
      
      // Parallel-specific optimizations
      if (IS_PARALLEL) {
        // Disable features that can cause conflicts
        config.watchForFileChanges = false;
        config.chromeWebSecurity = false;
        
        // Use unique ports per worker for any local services
        const workerNum = parseInt(WORKER_ID);
        if (!isNaN(workerNum)) {
          // Offset ports to avoid conflicts
          const portOffset = workerNum * 10;
          config.env.WORKER_PORT_OFFSET = portOffset;
        }
      }
      
      return config;
    },
    
    baseUrl: process.env.CYPRESS_BASE_URL || 'http://localhost:3000',
    supportFile: 'cypress/support/e2e.ts',
    specPattern: 'cypress/e2e/**/*.{js,jsx,ts,tsx}',
    excludeSpecPattern: [
      '**/examples/**',
      '**/*.hot-update.js'
    ],
    
    // Timeouts
    ...TIMEOUTS,
    
    // Retry configuration for flaky tests
    retries: {
      runMode: IS_PARALLEL ? 1 : 2,  // Less retries in parallel to save time
      openMode: 0
    },
    
    // Viewport for consistency
    viewportWidth: 1280,
    viewportHeight: 720,
    
    // Browser launch options
    chromeWebSecurity: false,
    modifyObstructiveCode: false,
    
    // Reporter configuration
    reporter: IS_PARALLEL ? 'json' : 'spec',
    reporterOptions: IS_PARALLEL ? {
      output: `cypress/results/worker-${WORKER_ID}.json`
    } : {}
  },
  
  component: {
    devServer: {
      framework: 'next',
      bundler: 'webpack',
    },
    specPattern: 'cypress/component/**/*.{js,jsx,ts,tsx}',
  },
});