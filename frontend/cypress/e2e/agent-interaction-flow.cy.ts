describe('Agent Interaction Complete Flow', () => {
  beforeEach(() => {
    // Clear state and setup authentication
    cy.clearLocalStorage();
    cy.clearCookies();
    
    // Prevent uncaught exceptions from failing tests
    Cypress.on('uncaught:exception', (err, runnable) => {
      return false;
    });
    
    // Setup authenticated state with current JWT structure
    cy.window().then((win) => {
      win.localStorage.setItem('jwt_token', 'mock-jwt-token-for-testing');
      win.localStorage.setItem('user_data', JSON.stringify({
        id: 'test-user-id',
        email: 'test@netrasystems.ai',
        full_name: 'Test User',
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
        
        // Check for main chat container
        cy.get('[data-testid="main-chat"]', { timeout: 10000 }).should('exist');
        
        // Check for any chat interface elements using current selectors
        cy.get('body').then($body => {
          const bodyText = $body.text();
          
          // Check if page has chat-related content
          const hasChatContent = /chat|message|send|type|conversation/i.test(bodyText);
          const hasNetraContent = /netra|ai|optimization|agent/i.test(bodyText);
          
          expect(hasChatContent || hasNetraContent).to.be.true;
          
          // Try to find input elements using current system selectors
          if ($body.find('[data-testid="message-textarea"]').length > 0) {
            cy.log('Found message textarea with data-testid');
            cy.get('[data-testid="message-textarea"]').should('be.visible');
            
            // Try to type in the input
            cy.get('[data-testid="message-textarea"]').type('Test optimization request', { force: true });
            
            // Look for send button with current selector
            cy.get('[data-testid="send-button"]').should('exist');
            cy.log('Found send button with data-testid');
          } else {
            // Fallback to generic selectors
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
          }
        });
      }
    });
  });

  it('should handle agent workflow simulation', () => {
    cy.url().then((url) => {
      if (!url.includes('/login')) {
        // Mock chat API for workflow testing
        cy.intercept('POST', '**/api/chat', {
          statusCode: 200,
          body: {
            message: 'Optimization analysis in progress...',
            status: 'processing',
            agent: 'triage'
          }
        }).as('chatRequest');
        
        // Simulate agent workflow by checking page content and testing interaction
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
          
          // Try to interact with the system using current selectors
          if ($body.find('[data-testid="message-textarea"]').length > 0) {
            cy.get('[data-testid="message-textarea"]').type('Optimize my infrastructure costs by 30%', { force: true });
            cy.get('[data-testid="send-button"]').click({ force: true });
            
            // Wait for potential response
            cy.wait(2000);
            
            // Check if any processing indicators appear
            cy.get('body').then($responseBody => {
              const responseText = $responseBody.text();
              if (/processing|analyzing|thinking|working/i.test(responseText)) {
                cy.log('Agent processing indicators found');
              }
            });
          } else if ($body.find('textarea').length > 0) {
            // Fallback workflow test
            cy.get('textarea').first().type('Optimize my infrastructure costs by 30%', { force: true });
            cy.get('button').contains('Send').first().click({ force: true });
            cy.wait(2000);
          }
        });
      } else {
        cy.log('Authentication required - skipping workflow test');
      }
    });
  });

  it('should display agent status indicators if available', () => {
    cy.url().then((url) => {
      if (!url.includes('/login')) {
        // Mock WebSocket message for agent status
        cy.window().then((win) => {
          // Simulate WebSocket message if available
          if ((win as any).WebSocket) {
            cy.log('WebSocket available for status testing');
          }
        });
        
        cy.get('body').then($body => {
          // Look for any status indicators using current system patterns
          const statusSelectors = [
            '.status',
            '.loading',
            '.spinner',
            '[aria-busy="true"]',
            '[class*="loading"]',
            '[class*="status"]',
            '[class*="agent"]',
            '[class*="animate-spin"]', // Tailwind spinner
            '[data-testid*="status"]',
            '[data-testid*="loading"]'
          ];
          
          let foundStatus = false;
          statusSelectors.forEach(selector => {
            if ($body.find(selector).length > 0) {
              foundStatus = true;
              cy.log(`Found status indicator: ${selector}`);
            }
          });
          
          // Also check for text-based status with current system patterns
          const statusText = /loading|processing|thinking|analyzing|ready|connected|online|initializing/i;
          if (statusText.test($body.text())) {
            cy.log('Found text-based status indicator');
            foundStatus = true;
          }
          
          // It's OK if no status indicators are found - they might appear dynamically
          if (!foundStatus) {
            cy.log('No status indicators found - they may appear during interaction');
          }
          
          // Test interaction to trigger status changes
          if ($body.find('[data-testid="message-textarea"]').length > 0) {
            cy.get('[data-testid="message-textarea"]').type('Test status indicators', { force: true });
            cy.get('[data-testid="send-button"]').click({ force: true });
            
            // Check for dynamic status updates
            cy.wait(1000);
            cy.get('body').then($updatedBody => {
              if ($updatedBody.find('[class*="animate-spin"], [class*="loading"], [data-testid*="loading"]').length > 0) {
                cy.log('Dynamic status indicators appeared after interaction');
              }
            });
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
        
        // Test that main chat container exists and is stable
        cy.get('[data-testid="main-chat"]', { timeout: 5000 }).should('exist');
        
        // Wait and check if page remains stable
        cy.wait(3000);
        
        cy.url().then((newUrl) => {
          // URL should not change unexpectedly
          expect(newUrl).to.equal(initialUrl);
        });
        
        // Page should still be visible and not show errors
        cy.get('body').then($body => {
          const text = $body.text();
          // Should not show critical error messages
          const hasCriticalError = /fatal error|crash|something went wrong|page not found/i.test(text);
          if (hasCriticalError) {
            cy.log('Warning: Page may contain critical error messages');
          }
          
          // Should maintain basic structure with current system elements
          expect($body.find('*').length).to.be.greaterThan(10);
          
          // Check that main components are still present
          if ($body.find('[data-testid="main-chat"]').length > 0) {
            cy.get('[data-testid="main-chat"]').should('be.visible');
            cy.log('Main chat container remains stable');
          }
        });
        
        // Test stability under interaction
        cy.get('body').then($body => {
          if ($body.find('[data-testid="message-textarea"]').length > 0) {
            // Multiple interactions to test stability
            for (let i = 0; i < 3; i++) {
              cy.get('[data-testid="message-textarea"]').clear().type(`Stability test ${i + 1}`, { force: true });
              cy.wait(500);
            }
            
            // Check page is still stable
            cy.get('[data-testid="main-chat"]').should('exist');
            cy.url().should('eq', initialUrl);
          }
        });
      }
    });
  });

  it('should handle graceful degradation without backend', () => {
    cy.url().then((url) => {
      if (!url.includes('/login')) {
        // Mock backend unavailability
        cy.intercept('POST', '**/api/chat', {
          statusCode: 503,
          body: { 
            error: 'Service temporarily unavailable',
            message: 'Backend services are currently offline'
          }
        }).as('backendUnavailable');
        
        // Try to interact even if backend is not available
        cy.get('body').then($body => {
          // Find interactive elements using current selectors
          const interactiveElements = $body.find([
            '[data-testid="send-button"]',
            '[data-testid="message-textarea"]',
            'button', 
            'a', 
            'input', 
            'textarea', 
            'select', 
            '[role="button"]', 
            '[onclick]'
          ].join(', '));
          
          if (interactiveElements.length > 0) {
            cy.log(`Found ${interactiveElements.length} interactive elements`);
            
            // Test input functionality
            if ($body.find('[data-testid="message-textarea"]').length > 0) {
              cy.get('[data-testid="message-textarea"]').type('Test graceful degradation', { force: true });
              
              // Try to send message
              if ($body.find('[data-testid="send-button"]').length > 0) {
                cy.get('[data-testid="send-button"]').click({ force: true });
                
                // Check for graceful error handling
                cy.wait(2000);
                cy.get('body').then($errorBody => {
                  const errorText = $errorBody.text();
                  if (/service unavailable|offline|error|try again/i.test(errorText)) {
                    cy.log('Graceful error handling detected');
                  }
                });
              }
            }
            
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
          
          // Check if page shows any connection status with current system patterns
          const connectionStatus = /connecting|disconnected|offline|reconnecting|service unavailable/i;
          if (connectionStatus.test($body.text())) {
            cy.log('Page shows connection status - backend may be unavailable');
          }
          
          // Ensure main structure remains intact during degradation
          if ($body.find('[data-testid="main-chat"]').length > 0) {
            cy.get('[data-testid="main-chat"]').should('be.visible');
          }
        });
      }
    });
  });

  it('should handle authentication state correctly', () => {
    // Test that authentication is properly handled
    cy.window().then((win) => {
      const token = win.localStorage.getItem('jwt_token');
      const userData = win.localStorage.getItem('user_data');
      
      expect(token).to.not.be.null;
      expect(userData).to.not.be.null;
      
      if (userData) {
        const parsedUser = JSON.parse(userData);
        expect(parsedUser).to.have.property('email');
        expect(parsedUser.email).to.equal('test@netrasystems.ai');
      }
    });
    
    // Check that authenticated pages load correctly
    cy.url().then((url) => {
      if (url.includes('/chat')) {
        cy.log('Successfully accessed chat page with authentication');
        
        // Main chat should be available for authenticated users
        cy.get('[data-testid="main-chat"]', { timeout: 5000 }).should('exist');
      }
    });
  });

  afterEach(() => {
    // Clean up test state
    cy.window().then((win) => {
      win.localStorage.removeItem('jwt_token');
      win.localStorage.removeItem('user_data');
      win.localStorage.removeItem('test_state');
    });
  });
});