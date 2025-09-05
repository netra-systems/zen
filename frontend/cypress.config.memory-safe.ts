import { defineConfig } from 'cypress';

export default defineConfig({
  e2e: {
    // Aggressive memory management to prevent crashes
    experimentalMemoryManagement: true,
    numTestsKeptInMemory: 0, // Don't keep ANY tests in memory
    
    setupNodeEvents(on, config) {
      // Minimal task setup to reduce memory overhead
      on('task', {
        log(message) {
          console.log(message);
          return null;
        }
      });
      
      // Reduce timeout values to fail faster and use less memory
      config.defaultCommandTimeout = 10000;
      config.requestTimeout = 10000;
      config.responseTimeout = 10000;
      config.pageLoadTimeout = 30000;
      
      return config;
    },
    
    baseUrl: 'http://localhost:3000',
    supportFile: false, // Disable support file to reduce memory
    specPattern: 'cypress/e2e/**/*.cy.ts',
    watchForFileChanges: false,
    video: false,
    screenshotOnRunFailure: false,
    chromeWebSecurity: false,
    
    // Reduced timeouts for memory efficiency
    defaultCommandTimeout: 10000,
    requestTimeout: 10000,
    responseTimeout: 10000,
    pageLoadTimeout: 30000,
    
    // Browser configuration for memory optimization
    browser: 'chrome',
    
    // Additional memory optimizations
    trashAssetsBeforeRuns: true, // Clean up before each run
    
    env: {
      // Minimal environment to reduce memory footprint
      BACKEND_URL: 'http://localhost:8000',
      AUTH_URL: 'http://localhost:8081',
      FRONTEND_URL: 'http://localhost:3000'
    }
  }
});