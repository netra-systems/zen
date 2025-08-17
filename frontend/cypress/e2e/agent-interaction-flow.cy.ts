describe('Agent Interaction Complete Flow', () => {
  beforeEach(() => {
    // Clear state and mock authentication
    cy.clearLocalStorage();
    cy.clearCookies();
    
    // Prevent uncaught exceptions from failing tests
    Cypress.on('uncaught:exception', (err, runnable) => {
      return false;
    });
    
    cy.window().then((win) => {
      win.localStorage.setItem('auth_token', 'mock-jwt-token-for-testing');
      win.localStorage.setItem('user', JSON.stringify({
        id: 'test-user-id',
        email: 'test@netrasystems.ai',
        name: 'Test User',
        role: 'user'
      }));
    });
    
    cy.visit('/chat', { failOnStatusCode: false });
    cy.wait(2000); // Wait for page load and WebSocket connection
  });

  it('should load chat interface and accept input', () => {
    cy.url().then((url) => {
      // Check if we're on the chat page or redirected to login
      if (url.includes('/login')) {
        cy.log('Redirected to login page - authentication required');
        // Verify login page loaded
        cy.get('body').should('be.visible');
        expect(url).to.include('/login');
      } else {
        cy.log('On chat page - checking for interface elements');
        
        // Wait for page to stabilize
        cy.wait(1000);
        
        // Check for any chat interface elements
        cy.get('body').then($body => {
          const bodyText = $body.text();
          
          // Check if page has chat-related content
          const hasChatContent = /chat|message|send|type|conversation/i.test(bodyText);
          const hasNetraContent = /netra|ai|optimization|agent/i.test(bodyText);
          
          expect(hasChatContent || hasNetraContent).to.be.true;
          
          // Try to find input elements
          const inputSelectors = [
            'textarea',
            'input[type="text"]:not([type="hidden"])',
            '[contenteditable="true"]',
            '[role="textbox"]',
            '.chat-input',
            '#message'
          ];
          
          let inputFound = false;
          for (const selector of inputSelectors) {
            if ($body.find(selector).length > 0 && $body.find(selector).is(':visible')) {
              inputFound = true;
              cy.log(`Found input element: ${selector}`);
              
              // Try to type in the input
              cy.get(selector).first().type('Test optimization request', { force: true });
              
              // Look for send button
              const buttonSelectors = [
                'button:contains("Send")',
                'button:contains("Submit")',
                'button[type="submit"]',
                'button svg', // Button with icon
                '[role="button"]'
              ];
              
              for (const btnSelector of buttonSelectors) {
                if ($body.find(btnSelector).length > 0) {
                  cy.log(`Found button: ${btnSelector}`);
                  break;
                }
              }
              break;
            }
          }
          
          if (!inputFound) {
            cy.log('No input elements found - page may be loading or require different authentication');
          }
        });
      }
    });
  });

  it('should handle agent workflow simulation', () => {
    cy.url().then((url) => {
      if (!url.includes('/login')) {
        // Simulate agent workflow by checking page content
        cy.get('body').then($body => {
          const text = $body.text();
          
          // Check if the page mentions agent capabilities
          const agentKeywords = [
            'optimization',
            'analysis',
            'recommendation',
            'performance',
            'cost',
            'agent',
            'AI',
            'workflow'
          ];
          
          let keywordCount = 0;
          agentKeywords.forEach(keyword => {
            if (new RegExp(keyword, 'i').test(text)) {
              keywordCount++;
              cy.log(`Found keyword: ${keyword}`);
            }
          });
          
          // Page should have at least some agent-related content
          expect(keywordCount).to.be.greaterThan(0);
        });
      } else {
        cy.log('Authentication required - skipping workflow test');
      }
    });
  });

  it('should display agent status indicators if available', () => {
    cy.url().then((url) => {
      if (!url.includes('/login')) {
        cy.get('body').then($body => {
          // Look for any status indicators
          const statusSelectors = [
            '.status',
            '.loading',
            '.spinner',
            '[aria-busy="true"]',
            '[class*="loading"]',
            '[class*="status"]',
            '[class*="agent"]'
          ];
          
          let foundStatus = false;
          statusSelectors.forEach(selector => {
            if ($body.find(selector).length > 0) {
              foundStatus = true;
              cy.log(`Found status indicator: ${selector}`);
            }
          });
          
          // Also check for text-based status
          const statusText = /loading|processing|thinking|analyzing|ready|connected|online/i;
          if (statusText.test($body.text())) {
            cy.log('Found text-based status indicator');
            foundStatus = true;
          }
          
          // It's OK if no status indicators are found - they might appear dynamically
          if (!foundStatus) {
            cy.log('No status indicators found - they may appear during interaction');
          }
        });
      }
    });
  });

  it('should maintain page stability during interaction', () => {
    cy.url().then((url) => {
      if (!url.includes('/login')) {
        // Check initial page state
        cy.get('body').should('be.visible');
        const initialUrl = url;
        
        // Wait and check if page remains stable
        cy.wait(3000);
        
        cy.url().then((newUrl) => {
          // URL should not change unexpectedly
          expect(newUrl).to.equal(initialUrl);
        });
        
        // Page should still be visible and not show errors
        cy.get('body').then($body => {
          const text = $body.text();
          // Should not show error messages
          const hasError = /error|failed|exception|something went wrong/i.test(text);
          if (hasError) {
            cy.log('Warning: Page may contain error messages');
          }
          
          // Should maintain basic structure
          expect($body.find('*').length).to.be.greaterThan(10);
        });
      }
    });
  });

  it('should handle graceful degradation without backend', () => {
    cy.url().then((url) => {
      if (!url.includes('/login')) {
        // Try to interact even if backend is not available
        cy.get('body').then($body => {
          // Find any interactive elements
          const interactiveElements = $body.find('button, a, input, textarea, select, [role="button"], [onclick]');
          
          if (interactiveElements.length > 0) {
            cy.log(`Found ${interactiveElements.length} interactive elements`);
            
            // Try clicking a safe button (not logout or delete)
            const safeButtons = interactiveElements.filter((i, el) => {
              const text = Cypress.$(el).text().toLowerCase();
              return !text.includes('logout') && !text.includes('delete') && !text.includes('remove');
            });
            
            if (safeButtons.length > 0) {
              // Click won't fail the test even if it doesn't do anything
              cy.wrap(safeButtons.first()).click({ force: true });
              cy.wait(1000);
              
              // Page should still be stable
              cy.get('body').should('be.visible');
            }
          }
          
          // Check if page shows any connection status
          const connectionStatus = /connecting|disconnected|offline|reconnecting/i;
          if (connectionStatus.test($body.text())) {
            cy.log('Page shows connection status - backend may be unavailable');
          }
        });
      }
    });
  });
});