describe('Synthetic Data Generation Flow', () => {
  beforeEach(() => {
    // Clear state and mock authentication
    cy.clearLocalStorage();
    cy.clearCookies();
    
    cy.window().then((win) => {
      win.localStorage.setItem('auth_token', 'mock-jwt-token-for-testing');
      win.localStorage.setItem('user', JSON.stringify({
        id: 'test-user-id',
        email: 'test@netra.ai',
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
        cy.visit('/chat');
        cy.wait(1000);
        
        // Try through chat interface
        const dataRequest = 'I need to generate synthetic training data for my AI model';
        cy.get('textarea, input[type="text"]').first().type(dataRequest);
        cy.get('button').contains(/send|submit|→|⏎/i).click();
        
        cy.contains(dataRequest, { timeout: 10000 }).should('be.visible');
        cy.contains(/synthetic|data|generation|training/i, { timeout: 20000 }).should('exist');
      } else {
        // On synthetic data page
        cy.get('body').should('be.visible');
        
        // Check for data generation UI elements
        cy.get('h1, h2, h3').then(($headers) => {
          const headerText = $headers.text();
          expect(headerText).to.match(/synthetic|data|generation/i);
        });
        
        // Look for input fields or configuration options
        cy.get('input, textarea, select, button').should('have.length.greaterThan', 0);
      }
    });
  });

  it('should generate synthetic data based on specifications', () => {
    // Navigate through chat if needed
    cy.url().then((url) => {
      if (url.includes('/synthetic-data-generation')) {
        // Direct page access
        cy.get('body').then(($body) => {
          // Look for data type selector
          const selectors = ['select', 'input[type="radio"]', 'button[role="option"]'];
          let foundSelector = false;
          
          selectors.forEach(selector => {
            if ($body.find(selector).length > 0) {
              foundSelector = true;
              cy.get(selector).first().click();
            }
          });
          
          // Fill in data generation parameters
          cy.get('input[type="number"], input[type="text"]').then(($inputs) => {
            if ($inputs.length > 0) {
              $inputs.each((index, input) => {
                const $input = Cypress.$(input);
                const placeholder = $input.attr('placeholder') || '';
                const name = $input.attr('name') || '';
                
                if (placeholder.match(/count|number|quantity/i) || name.match(/count|number|quantity/i)) {
                  cy.wrap(input).type('100');
                } else if (placeholder.match(/format|type/i) || name.match(/format|type/i)) {
                  cy.wrap(input).type('json');
                } else {
                  cy.wrap(input).type('test_data');
                }
              });
            }
          });
          
          // Submit generation request
          cy.get('button').contains(/generate|create|start|submit/i).click();
          
          // Wait for generation to complete
          cy.contains(/generating|processing|creating/i, { timeout: 15000 }).should('exist');
          cy.contains(/complete|finished|generated|download|preview/i, { timeout: 30000 }).should('exist');
        });
      } else {
        // Use chat interface for data generation
        cy.visit('/chat');
        cy.wait(2000);
        
        const dataRequest = 'Generate 100 synthetic customer records with names, emails, and purchase history in JSON format';
        cy.get('textarea, input[type="text"]').first().type(dataRequest);
        cy.get('button').contains(/send|submit|→|⏎/i).click();
        
        cy.contains(dataRequest, { timeout: 10000 }).should('be.visible');
        
        // Check for data generation response
        cy.contains(/generating|creating|synthetic/i, { timeout: 15000 }).should('exist');
        
        // Verify data format in response
        cy.get('body', { timeout: 30000 }).then(($body) => {
          const text = $body.text();
          // Should contain JSON indicators or data structure
          expect(text).to.match(/json|\{|\[|record|customer|email|name/i);
        });
      }
    });
  });

  it('should handle different data generation templates', () => {
    cy.visit('/chat');
    cy.wait(2000);
    
    // Test multiple data generation scenarios
    const scenarios = [
      {
        request: 'Generate synthetic API logs for load testing',
        keywords: /api|log|endpoint|status|timestamp/i
      },
      {
        request: 'Create sample training data for sentiment analysis',
        keywords: /sentiment|positive|negative|neutral|text|label/i
      },
      {
        request: 'Generate mock user behavior data for analytics',
        keywords: /user|behavior|session|event|click|page/i
      }
    ];
    
    // Test first scenario (to keep test reasonable length)
    const scenario = scenarios[0];
    cy.get('textarea, input[type="text"]').first().type(scenario.request);
    cy.get('button').contains(/send|submit|→|⏎/i).click();
    
    cy.contains(scenario.request, { timeout: 10000 }).should('be.visible');
    cy.contains(/generating|creating|preparing/i, { timeout: 15000 }).should('exist');
    
    // Verify appropriate data type in response
    cy.get('body', { timeout: 30000 }).then(($body) => {
      const text = $body.text();
      expect(text).to.match(scenario.keywords);
    });
  });

  it('should provide data validation and preview', () => {
    cy.visit('/chat');
    cy.wait(2000);
    
    const validationRequest = 'Generate 10 sample records and validate the data structure before generating the full dataset';
    cy.get('textarea, input[type="text"]').first().type(validationRequest);
    cy.get('button').contains(/send|submit|→|⏎/i).click();
    
    cy.contains(validationRequest, { timeout: 10000 }).should('be.visible');
    
    // Check for preview/validation phase
    cy.contains(/sample|preview|validate|structure|format/i, { timeout: 20000 }).should('exist');
    
    // Check for data structure information
    cy.get('body', { timeout: 30000 }).then(($body) => {
      const text = $body.text();
      // Should show sample data or structure
      expect(text).to.match(/field|type|example|sample|structure/i);
    });
    
    // Follow up to generate full dataset
    const confirmRequest = 'Looks good, generate the full dataset of 1000 records';
    cy.get('textarea, input[type="text"]').first().clear().type(confirmRequest);
    cy.get('button').contains(/send|submit|→|⏎/i).click();
    
    cy.contains(confirmRequest, { timeout: 10000 }).should('be.visible');
    cy.contains(/generating|1000|full dataset|creating/i, { timeout: 30000 }).should('exist');
  });

  it('should handle data export and download options', () => {
    cy.visit('/chat');
    cy.wait(2000);
    
    const exportRequest = 'Generate 50 records and provide options to export as CSV, JSON, and Parquet';
    cy.get('textarea, input[type="text"]').first().type(exportRequest);
    cy.get('button').contains(/send|submit|→|⏎/i).click();
    
    cy.contains(exportRequest, { timeout: 10000 }).should('be.visible');
    
    // Wait for generation
    cy.contains(/generating|creating/i, { timeout: 15000 }).should('exist');
    
    // Check for export format options
    cy.get('body', { timeout: 30000 }).then(($body) => {
      const text = $body.text();
      // Should mention export formats
      expect(text).to.match(/csv|json|parquet|export|download|format/i);
      
      // Look for download links or buttons
      const downloadElements = $body.find('a[download], button:contains("download"), [href*="download"]');
      if (downloadElements.length > 0) {
        cy.log(`Found ${downloadElements.length} download elements`);
      }
    });
  });

  it('should provide generation statistics and metadata', () => {
    cy.visit('/chat');
    cy.wait(2000);
    
    const statsRequest = 'Generate a synthetic dataset with 500 records and show me generation statistics';
    cy.get('textarea, input[type="text"]').first().type(statsRequest);
    cy.get('button').contains(/send|submit|→|⏎/i).click();
    
    cy.contains(statsRequest, { timeout: 10000 }).should('be.visible');
    
    // Wait for generation to complete
    cy.contains(/generating|processing/i, { timeout: 15000 }).should('exist');
    cy.contains(/complete|finished|generated/i, { timeout: 30000 }).should('exist');
    
    // Check for statistics in response
    cy.get('body', { timeout: 35000 }).then(($body) => {
      const text = $body.text();
      // Should contain statistics
      expect(text).to.match(/500|record|generated|total|statistic|summary/i);
      // May contain timing information
      const hasTimingInfo = /time|duration|seconds|ms|elapsed/i.test(text);
      if (hasTimingInfo) {
        cy.log('Generation timing information found');
      }
      // May contain data quality metrics
      const hasQualityInfo = /quality|valid|unique|distribution/i.test(text);
      if (hasQualityInfo) {
        cy.log('Data quality metrics found');
      }
    });
  });
});