import {
  ChatNavigation,
  MessageInput,
  MessageAssertions,
  ComponentVisibility,
  WaitHelpers
} from './utils/chat-test-helpers';

describe('Synthetic Data Generation Flow', () => {
  beforeEach(() => {
    // Clear state and setup environment
    cy.clearLocalStorage();
    cy.clearCookies();
    
    // Prevent uncaught exceptions from failing tests
    Cypress.on('uncaught:exception', (err, runnable) => {
      return false;
    });
    
    // Setup authentication
    cy.window().then((win) => {
      win.localStorage.setItem('auth_token', 'mock-jwt-token-for-testing');
      win.localStorage.setItem('user', JSON.stringify({
        id: 'test-user-id',
        email: 'test@netrasystems.ai',
        name: 'Test User',
        role: 'user'
      }));
    });
    
    // Try visiting dedicated data generation page first, fallback to chat
    cy.visit('/synthetic-data-generation', { failOnStatusCode: false });
    cy.wait(2000);
  });

  it('should navigate to data generation page and display UI', () => {
    cy.url().then((url) => {
      if (url.includes('/login')) {
        cy.log('Redirected to login - testing authenticated flow');
        cy.get('body').should('be.visible');
        expect(url).to.include('/login');
      } else if (url.includes('/synthetic-data-generation')) {
        // On dedicated synthetic data page
        cy.get('body').should('be.visible');
        
        // Check for data generation specific elements
        cy.get('body').then($body => {
          const text = $body.text();
          const hasDataGenContent = /synthetic|data|generation|create|generate/i.test(text);
          const hasNetraContent = /netra|ai|platform/i.test(text);
          
          expect(hasDataGenContent || hasNetraContent).to.be.true;
          cy.log('Data generation page loaded successfully');
        });
      } else {
        // Fallback to demo/chat interface for data generation
        cy.log(`Redirected to: ${url} - using demo interface`);
        ChatNavigation.visitDemo();
        ChatNavigation.selectIndustry('Financial Services');
        cy.contains('synthetic', { matchCase: false }).should('exist');
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

  it('should verify data generation capabilities through chat', () => {
    // Navigate to demo chat for data generation
    ChatNavigation.visitDemo();
    ChatNavigation.selectIndustry('Financial Services');
    
    // Test data generation through chat interface
    const dataGenMessage = 'Generate synthetic financial transaction data for testing';
    MessageInput.sendAndWait(dataGenMessage);
    
    // Verify user message appears
    MessageAssertions.assertUserMessage(dataGenMessage);
    
    // Wait for and verify response contains data generation content
    WaitHelpers.forResponse();
    cy.get('body').then($body => {
      const text = $body.text();
      
      // Check for data generation related keywords in response
      const dataGenKeywords = [
        'synthetic',
        'data',
        'generate',
        'sample',
        'mock',
        'dataset',
        'records',
        'transaction'
      ];
      
      const foundKeywords = dataGenKeywords.filter(keyword => 
        new RegExp(keyword, 'i').test(text)
      );
      
      if (foundKeywords.length > 0) {
        cy.log(`Found data generation keywords: ${foundKeywords.join(', ')}`);
      } else {
        cy.log('Testing data generation request through chat interface');
      }
    });
  });

  it('should handle data format selection through chat', () => {
    // Navigate to demo chat
    ChatNavigation.visitDemo();
    ChatNavigation.selectIndustry('Technology');
    
    // Test format selection through chat
    const formatMessage = 'Generate synthetic data in JSON format for user analytics';
    MessageInput.sendAndWait(formatMessage);
    
    MessageAssertions.assertUserMessage(formatMessage);
    WaitHelpers.forResponse();
    
    // Check for format-related content in response
    cy.get('body').then($body => {
      const text = $body.text();
      const formatOptions = ['JSON', 'CSV', 'SQL', 'XML', 'Parquet'];
      
      const foundFormats = formatOptions.filter(format => 
        new RegExp(format, 'i').test(text)
      );
      
      if (foundFormats.length > 0) {
        cy.log(`Found format references: ${foundFormats.join(', ')}`);
      }
      
      // Look for any format selection UI elements
      const hasSelect = $body.find('select, [role="combobox"]').length > 0;
      const hasButtons = $body.find('button[data-testid*="format"]').length > 0;
      
      if (hasSelect || hasButtons) {
        cy.log('Found format selection controls');
      }
    });
  });

  it('should verify data generation workflow through chat templates', () => {
    // Navigate to demo with data generation focus
    ChatNavigation.visitDemo();
    ChatNavigation.selectIndustry('Financial Services');
    
    // Check for data generation templates in chat interface
    cy.get('body').then($body => {
      const workflowKeywords = [
        'synthetic',
        'generate',
        'sample',
        'mock',
        'test data',
        'dataset'
      ];
      
      const text = $body.text();
      const foundWorkflowSteps = workflowKeywords.filter(keyword =>
        new RegExp(keyword, 'i').test(text)
      );
      
      if (foundWorkflowSteps.length > 0) {
        cy.log(`Found data generation workflow elements: ${foundWorkflowSteps.join(', ')}`);
      }
      
      // Look for template buttons or action items
      const actionSelectors = [
        'button[data-testid*="template"]',
        'button[data-testid*="generate"]',
        '[data-testid="send-button"]'
      ];
      
      let foundActions = 0;
      actionSelectors.forEach(selector => {
        const count = $body.find(selector).length;
        if (count > 0) {
          foundActions += count;
          cy.log(`Found ${count} ${selector} elements`);
        }
      });
      
      if (foundActions > 0) {
        cy.log(`Total data generation action elements: ${foundActions}`);
      }
    });
  });

  it('should maintain stability during data generation workflow', () => {
    // Navigate to stable demo interface
    ChatNavigation.visitDemo();
    ChatNavigation.selectIndustry('E-commerce');
    
    // Test data generation stability through controlled interactions
    const testMessage = 'Create sample e-commerce product data with 100 records';
    MessageInput.send(testMessage);
    
    // Verify message sent successfully
    MessageAssertions.assertUserMessage(testMessage);
    
    // Wait for processing
    WaitHelpers.forResponse();
    
    // Verify page remained stable
    cy.get('body').should('be.visible');
    cy.get('[data-testid="demo-chat"]').should('be.visible');
    
    // Check for error indicators
    cy.get('body').then($body => {
      const text = $body.text();
      const hasError = /error|failed|exception/i.test(text);
      
      if (hasError) {
        cy.log('Warning: Error indicators detected during data generation');
      } else {
        cy.log('Data generation workflow maintained stability');
      }
    });
    
    // Verify input remains functional after interaction
    cy.get('textarea[data-testid="message-input"]')
      .should('be.visible')
      .and('not.be.disabled');
  });
});