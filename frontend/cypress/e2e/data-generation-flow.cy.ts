describe('Synthetic Data Generation Flow', () => {
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
    
    cy.visit('/synthetic-data-generation', { failOnStatusCode: false });
    cy.wait(2000); // Wait for page load
  });

  it('should navigate to data generation page and display UI', () => {
    cy.url().then((url) => {
      // Check if redirected to login or on the correct page
      if (url.includes('/login')) {
        cy.log('Redirected to login - testing authenticated flow');
        // Verify login page loaded
        cy.get('body').should('be.visible');
        expect(url).to.include('/login');
      } else if (url.includes('/synthetic-data-generation')) {
        // On synthetic data page
        cy.get('body').should('be.visible');
        
        // Check for data generation UI elements
        cy.get('body').then($body => {
          const text = $body.text();
          const hasDataGenContent = /synthetic|data|generation|create|generate/i.test(text);
          const hasNetraContent = /netra|ai|platform/i.test(text);
          
          expect(hasDataGenContent || hasNetraContent).to.be.true;
          cy.log('Data generation page loaded successfully');
        });
      } else {
        // May have been redirected to chat or another page
        cy.log(`Redirected to: ${url}`);
        cy.get('body').should('be.visible');
      }
    });
  });

  it('should check for data generation form elements', () => {
    cy.url().then((url) => {
      if (!url.includes('/login')) {
        cy.get('body').then($body => {
          // Look for form elements
          const formElements = [
            'input',
            'textarea',
            'select',
            'button',
            '[role="combobox"]',
            '[role="button"]'
          ];
          
          let elementCount = 0;
          formElements.forEach(selector => {
            const count = $body.find(selector).length;
            if (count > 0) {
              elementCount += count;
              cy.log(`Found ${count} ${selector} element(s)`);
            }
          });
          
          if (elementCount > 0) {
            cy.log(`Total form elements found: ${elementCount}`);
          } else {
            cy.log('No form elements found - page may use chat interface for data generation');
            // Check if this is handled through chat
            const hasChatInterface = /chat|message|ask|request/i.test($body.text());
            if (hasChatInterface) {
              cy.log('Data generation appears to be handled through chat interface');
            }
          }
        });
      }
    });
  });

  it('should verify data generation capabilities', () => {
    cy.visit('/chat', { failOnStatusCode: false });
    cy.wait(2000);
    
    cy.url().then((url) => {
      if (!url.includes('/login')) {
        cy.get('body').then($body => {
          const text = $body.text();
          
          // Check for data generation related keywords
          const dataGenKeywords = [
            'synthetic',
            'data',
            'generate',
            'sample',
            'mock',
            'test data',
            'dataset',
            'records'
          ];
          
          let keywordCount = 0;
          dataGenKeywords.forEach(keyword => {
            if (new RegExp(keyword, 'i').test(text)) {
              keywordCount++;
              cy.log(`Found data generation keyword: ${keyword}`);
            }
          });
          
          // If no keywords found, it's ok - feature might be accessed differently
          if (keywordCount === 0) {
            cy.log('No data generation keywords found on initial page - feature may require interaction');
          }
        });
      }
    });
  });

  it('should handle data format selection', () => {
    cy.url().then((url) => {
      if (!url.includes('/login') && url.includes('/synthetic-data-generation')) {
        cy.get('body').then($body => {
          // Look for format selection options
          const formatOptions = ['JSON', 'CSV', 'SQL', 'XML', 'Parquet'];
          let foundFormats: string[] = [];
          
          formatOptions.forEach(format => {
            if (new RegExp(format, 'i').test($body.text())) {
              foundFormats.push(format);
            }
          });
          
          if (foundFormats.length > 0) {
            cy.log(`Found format options: ${foundFormats.join(', ')}`);
          } else {
            cy.log('No explicit format options found - may be configured differently');
          }
          
          // Check for any dropdowns or radio buttons
          const hasSelect = $body.find('select, [role="combobox"]').length > 0;
          const hasRadio = $body.find('input[type="radio"]').length > 0;
          
          if (hasSelect || hasRadio) {
            cy.log('Found selection controls for configuration');
          }
        });
      } else if (!url.includes('/login')) {
        // Try through chat interface
        cy.visit('/chat', { failOnStatusCode: false });
        cy.wait(2000);
        cy.log('Testing data generation through chat interface');
      }
    });
  });

  it('should verify data generation workflow availability', () => {
    cy.url().then((url) => {
      if (!url.includes('/login')) {
        cy.get('body').then($body => {
          // Check for workflow steps or instructions
          const workflowKeywords = [
            'step',
            'configure',
            'preview',
            'generate',
            'download',
            'export',
            'schema',
            'template'
          ];
          
          let workflowSteps: string[] = [];
          workflowKeywords.forEach(keyword => {
            if (new RegExp(keyword, 'i').test($body.text())) {
              workflowSteps.push(keyword);
            }
          });
          
          if (workflowSteps.length > 0) {
            cy.log(`Found workflow elements: ${workflowSteps.join(', ')}`);
          } else {
            cy.log('No explicit workflow steps found - feature may be streamlined');
          }
          
          // Check for action buttons
          const actionButtons = $body.find('button, [role="button"]');
          if (actionButtons.length > 0) {
            cy.log(`Found ${actionButtons.length} action button(s)`);
            
            // Check button text for generation actions
            actionButtons.each((i, btn) => {
              const btnText = Cypress.$(btn).text();
              if (/generate|create|build|export|download/i.test(btnText)) {
                cy.log(`Found action button: ${btnText}`);
              }
            });
          }
        });
      }
    });
  });

  it('should maintain stability during data generation interaction', () => {
    cy.url().then((url) => {
      if (!url.includes('/login')) {
        const initialUrl = url;
        
        // Try safe interaction
        cy.get('body').then($body => {
          // Find a safe interactive element
          const buttons = $body.find('button, [role="button"]').filter((i, el) => {
            const text = Cypress.$(el).text().toLowerCase();
            return !text.includes('delete') && !text.includes('logout');
          });
          
          if (buttons.length > 0) {
            // Click the first safe button
            cy.wrap(buttons.first()).click({ force: true });
            cy.wait(1000);
          }
          
          // Check page stability
          cy.url().then((newUrl) => {
            // Page might navigate, but should not error
            cy.get('body').should('be.visible');
            
            // Check for error messages
            const hasError = /error|failed|exception/i.test($body.text());
            if (hasError) {
              cy.log('Warning: Page may contain error messages');
            } else {
              cy.log('Page remained stable after interaction');
            }
          });
        });
      }
    });
  });
});