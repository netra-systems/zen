import { defineConfig } from 'cypress';

export default defineConfig({
  e2e: {
    experimentalMemoryManagement: true,
    numTestsKeptInMemory: 1,
    setupNodeEvents(on, config) {
      // WebSocket mock tasks for testing
      on('task', {
        log(message) {
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
        }
      });
      
      // Force correct configuration for real services
      config.baseUrl = 'http://localhost:3000';
      config.env = {
        ...config.env,
        BACKEND_URL: 'http://localhost:8000',
        AUTH_URL: 'http://localhost:8081',
        FRONTEND_URL: 'http://localhost:3000',
        REAL_LLM: 'true'
      };
      
      return config;
    },
    baseUrl: 'http://localhost:3000',
    supportFile: 'cypress/support/e2e.ts',
    specPattern: 'cypress/e2e/**/*.{js,jsx,ts,tsx}',
    watchForFileChanges: false,
    video: false,
    screenshotOnRunFailure: false,
    chromeWebSecurity: false,
    defaultCommandTimeout: 45000,
    requestTimeout: 45000,
    responseTimeout: 45000,
    pageLoadTimeout: 120000,
  },
  component: {
    devServer: {
      framework: 'next',
      bundler: 'webpack',
    },
    specPattern: 'cypress/component/**/*.{js,jsx,ts,tsx}',
  },
});
