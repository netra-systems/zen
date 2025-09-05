describe('Debug Chat Hanging Issue', () => {
  let consoleErrors: string[] = [];
  let consoleWarnings: string[] = [];
  let networkErrors: any[] = [];

  beforeEach(() => {
    // Capture console errors and warnings
    cy.on('window:before:load', (win) => {
      const originalError = win.console.error;
      const originalWarn = win.console.warn;
      
      win.console.error = (...args) => {
        consoleErrors.push(args.map(arg => String(arg)).join(' '));
        originalError.apply(win.console, args);
      };
      
      win.console.warn = (...args) => {
        consoleWarnings.push(args.map(arg => String(arg)).join(' '));
        originalWarn.apply(win.console, args);
      };
    });

    // Intercept all network requests
    cy.intercept('**/*', (req) => {
      req.on('response', (res) => {
        if (res.statusCode >= 400) {
          networkErrors.push({
            url: req.url,
            method: req.method,
            status: res.statusCode,
            body: res.body
          });
        }
      });
    }).as('allRequests');

    // Visit the staging site
    cy.visit('https://netra-frontend-staging-pnovr5vsba-uc.a.run.app', {
      failOnStatusCode: false,
      timeout: 30000
    });
  });

  it('should identify chat interface issues', () => {
    // Wait for page to load
    cy.wait(3000);

    // Check if chat interface elements exist
    cy.get('body').then($body => {
      cy.log('=== PAGE LOADED ===');
      
      // Look for chat-related elements
      const chatSelectors = [
        '[data-testid="chat-container"]',
        '[class*="chat"]',
        '[id*="chat"]',
        'textarea',
        'input[type="text"]',
        '[placeholder*="message"]',
        '[placeholder*="Message"]',
        'button[type="submit"]'
      ];

      chatSelectors.forEach(selector => {
        if ($body.find(selector).length > 0) {
          cy.log(`Found element: ${selector}`);
        }
      });
    });

    // Try to find and interact with message input
    cy.get('body').then($body => {
      // Look for any input field that might be for messages
      const $input = $body.find('textarea, input[type="text"]').filter((i, el) => {
        const placeholder = el.getAttribute('placeholder') || '';
        return placeholder.toLowerCase().includes('message') || 
               placeholder.toLowerCase().includes('type') ||
               placeholder.toLowerCase().includes('ask');
      });

      if ($input.length > 0) {
        cy.log('Found message input field');
        cy.wrap($input.first()).type('Test message from Cypress');
        
        // Look for send button
        const $button = $body.find('button').filter((i, el) => {
          const text = el.textContent || '';
          const ariaLabel = el.getAttribute('aria-label') || '';
          return text.toLowerCase().includes('send') || 
                 ariaLabel.toLowerCase().includes('send');
        });

        if ($button.length > 0) {
          cy.log('Found send button');
          cy.wrap($button.first()).click();
          
          // Wait to see what happens
          cy.wait(5000);
        }
      }
    });

    // Check WebSocket connection
    cy.window().then((win) => {
      cy.log('=== CHECKING WEBSOCKET ===');
      
      // Check if WebSocket exists in window
      if ((win as any).ws) {
        const ws = (win as any).ws;
        cy.log(`WebSocket state: ${ws.readyState}`);
        cy.log(`WebSocket URL: ${ws.url}`);
      } else {
        cy.log('No WebSocket found in window.ws');
      }

      // Check localStorage for auth tokens
      const token = win.localStorage.getItem('access_token');
      const userId = win.localStorage.getItem('user_id');
      cy.log(`Auth token exists: ${!!token}`);
      cy.log(`User ID: ${userId || 'not found'}`);
    });

    // Wait and then report all errors
    cy.wait(5000).then(() => {
      cy.log('=== CONSOLE ERRORS ===');
      consoleErrors.forEach(error => cy.log(`ERROR: ${error}`));
      
      cy.log('=== CONSOLE WARNINGS ===');
      consoleWarnings.forEach(warning => cy.log(`WARNING: ${warning}`));
      
      cy.log('=== NETWORK ERRORS ===');
      networkErrors.forEach(error => {
        cy.log(`${error.method} ${error.url} - Status: ${error.status}`);
        if (error.body) {
          cy.log(`Response: ${JSON.stringify(error.body).substring(0, 200)}`);
        }
      });

      // Check if any critical errors exist
      const criticalErrors = consoleErrors.filter(error => 
        error.includes('WebSocket') || 
        error.includes('Connection') ||
        error.includes('Failed to fetch') ||
        error.includes('NetworkError')
      );

      if (criticalErrors.length > 0) {
        cy.log('=== CRITICAL ERRORS FOUND ===');
        criticalErrors.forEach(error => cy.log(`CRITICAL: ${error}`));
      }
    });
  });

  it('should check API endpoints directly', () => {
    // Test backend health
    cy.request({
      url: 'https://netra-backend-staging-pnovr5vsba-uc.a.run.app/health',
      failOnStatusCode: false
    }).then((response) => {
      cy.log(`Backend health status: ${response.status}`);
      cy.log(`Backend response: ${JSON.stringify(response.body)}`);
    });

    // Test auth service health
    cy.request({
      url: 'https://auth.staging.netrasystems.ai/health',
      failOnStatusCode: false
    }).then((response) => {
      cy.log(`Auth service health status: ${response.status}`);
      cy.log(`Auth response: ${JSON.stringify(response.body)}`);
    });

    // Check WebSocket endpoint
    cy.request({
      url: 'https://netra-backend-staging-pnovr5vsba-uc.a.run.app/ws',
      failOnStatusCode: false,
      headers: {
        'Upgrade': 'websocket',
        'Connection': 'Upgrade'
      }
    }).then((response) => {
      cy.log(`WebSocket endpoint status: ${response.status}`);
    });
  });
});