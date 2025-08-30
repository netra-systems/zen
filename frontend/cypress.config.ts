
import { defineConfig } from 'cypress';
import * as fs from 'fs';
import * as path from 'path';

export default defineConfig({
  e2e: {
    setupNodeEvents(on, config) {
      // implement node event listeners here
      on('task', {
        log(message) {
          // console output removed: console.log(message);
          return null;
        },
      });
      
      // Load dynamic port configuration if available
      const portConfigPath = path.join(__dirname, '..', '.netra', 'cypress-ports.json');
      if (fs.existsSync(portConfigPath)) {
        try {
          const portConfig = JSON.parse(fs.readFileSync(portConfigPath, 'utf-8'));
          
          // Override baseUrl with discovered frontend port
          if (portConfig.baseUrl) {
            config.baseUrl = portConfig.baseUrl;
          }
          
          // Merge environment variables with discovered service URLs
          if (portConfig.env) {
            config.env = { ...config.env, ...portConfig.env };
          }
        } catch (error) {
          // Fallback to defaults if config read fails
        }
      }
      
      return config;
    },
    baseUrl: 'http://localhost:3000',
    supportFile: 'cypress/support/e2e.ts',
    specPattern: 'cypress/e2e/**/*.{js,jsx,ts,tsx}',
    watchForFileChanges: false,
    video: false,
    screenshotOnRunFailure: false,
    // Run in headless mode by default
    chromeWebSecurity: false,
    defaultCommandTimeout: 10000,
    requestTimeout: 10000,
    responseTimeout: 10000,
  },
  component: {
    devServer: {
      framework: 'next',
      bundler: 'webpack',
    },
    specPattern: 'cypress/component/**/*.{js,jsx,ts,tsx}',
  },
});
