
import { defineConfig } from 'cypress';
import { API_BASE_URL } from './services/apiConfig';

export default defineConfig({
  e2e: {
    setupNodeEvents(on, config) {
      // implement node event listeners here
    },
    baseUrl: API_BASE_URL.replace('8000', '3000'),
  },
});
