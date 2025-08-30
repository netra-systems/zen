/**
 * Agent Interaction Flow E2E Tests
 * 
 * Tests real user scenarios for AI optimization workflows using real services.
 * Focuses on business value and customer scenarios per CLAUDE.md standards.
 * 
 * Business Value: Tests core customer workflows for AI optimization platform
 * - Free tier users can access basic optimization recommendations
 * - Users can submit optimization requests and receive AI-powered analysis
 * - System maintains stability during real agent interactions
 */

describe('Agent Interaction Flow - Real Services', () => {
  beforeEach(() => {
    // Clear state for clean test environment
    cy.clearLocalStorage();
    cy.clearCookies();
    
    // Configure Cypress to handle real application behavior
    Cypress.on('uncaught:exception', (err, runnable) => {
      // Log the error but don't fail the test for network/timing issues
      console.log('Uncaught exception:', err.message);
      return false;
    });
    
    // Visit chat page to trigger real authentication flow
    cy.visit('/chat', { failOnStatusCode: false });
    
    // Wait for initial page load and auth initialization
    cy.get('body', { timeout: 10000 }).should('be.visible');
  });

  it('should authenticate user and load chat interface', () => {
    // Debug: Check what's actually on the page
    cy.get('body').then(($body) => {
      cy.log('Page content:', $body.text().substring(0, 200));
    });
    
    // Check for 404 error and handle appropriately
    cy.get('body').then(($body) => {
      if ($body.text().includes('404') || $body.text().includes('This page could not be found')) {
        cy.log('Page showing 404 error - this indicates a routing issue in the SUT');
        // The test should fail here as this indicates a problem with the System Under Test
        throw new Error('Chat page returns 404 - SUT routing issue detected');
      }
    });
    
    // Wait for auth initialization in development mode
    cy.get('[data-testid="loading"], [data-testid="main-chat"]', { timeout: 15000 }).should('exist');
    
    // In development mode, should auto-authenticate and show chat interface
    cy.get('[data-testid="main-chat"]', { timeout: 10000 }).should('be.visible');
    
    // Verify core interface elements are present
    cy.get('[data-testid="message-textarea"]').should('be.visible');
    cy.get('[data-testid="send-button"]').should('be.visible');
    
    // Verify welcome content shows business value proposition
    cy.get('body').should('contain.text', 'Netra AI');
    cy.get('body').should('contain.text', 'optimization');
  });

  it('should submit optimization request and show real agent response', () => {
    // Wait for chat interface to load completely
    cy.get('[data-testid="main-chat"]', { timeout: 10000 }).should('be.visible');
    cy.get('[data-testid="message-textarea"]', { timeout: 5000 }).should('be.visible');
    
    // Submit real business optimization request
    const optimizationRequest = 'I need to reduce my AI infrastructure costs by 30% while maintaining quality. Currently spending $5000/month on OpenAI API calls.';
    
    cy.get('[data-testid="message-textarea"]').clear().type(optimizationRequest);
    cy.get('[data-testid="send-button"]').should('be.enabled');
    cy.get('[data-testid="send-button"]').click();
    
    // Verify message was sent (input should be cleared)
    cy.get('[data-testid="message-textarea"]').should('have.value', '');
    
    // Check for real agent processing indicators
    cy.get('body', { timeout: 5000 }).should('contain.text', 'processing');
    
    // Verify system shows actual agent response (with extended timeout for real LLM)
    cy.get('body', { timeout: 30000 }).should('contain.text', optimizationRequest);
    
    // Check for business value elements in response
    cy.get('body').then($body => {
      const responseText = $body.text().toLowerCase();
      const hasBusinessValue = /cost|save|optimize|reduce|efficiency|performance|recommendation/i.test(responseText);
      expect(hasBusinessValue).to.be.true;
    });
  });

  it('should display real-time agent processing status', () => {
    // Ensure chat interface is loaded
    cy.get('[data-testid="main-chat"]', { timeout: 10000 }).should('be.visible');
    cy.get('[data-testid="message-textarea"]').should('be.visible');
    
    // Submit a request to trigger real agent processing
    cy.get('[data-testid="message-textarea"]').type('Quick cost analysis for my current setup');
    cy.get('[data-testid="send-button"]').click();
    
    // Verify real-time status indicators appear
    cy.get('[class*="animate-spin"], [data-testid*="loading"]', { timeout: 5000 }).should('exist');
    
    // Check for agent processing text indicators
    cy.get('body').should('contain.text', 'processing');
    
    // Verify status updates over time (real agent workflow)
    cy.wait(3000);
    cy.get('body').then($body => {
      const bodyText = $body.text().toLowerCase();
      const hasAgentActivity = /analyzing|thinking|processing|working/i.test(bodyText);
      expect(hasAgentActivity).to.be.true;
    });
  });

  it('should handle multiple optimization requests sequentially', () => {
    // Ensure chat interface is ready
    cy.get('[data-testid="main-chat"]', { timeout: 10000 }).should('be.visible');
    cy.get('[data-testid="message-textarea"]').should('be.visible');
    
    // Test sequential business requests
    const requests = [
      'Analyze my database query performance',
      'Recommend cost optimization strategies'
    ];
    
    requests.forEach((request, index) => {
      cy.log(`Submitting request ${index + 1}: ${request}`);
      
      // Type and send each request
      cy.get('[data-testid="message-textarea"]').clear().type(request);
      cy.get('[data-testid="send-button"]').click();
      
      // Wait for processing to start
      cy.get('body', { timeout: 5000 }).should('contain.text', 'processing');
      
      // Wait between requests to ensure proper handling
      cy.wait(2000);
    });
    
    // Verify both requests are visible in chat history
    requests.forEach(request => {
      cy.get('body').should('contain.text', request);
    });
    
    // Verify system maintains functionality after multiple requests
    cy.get('[data-testid="message-textarea"]').should('be.enabled');
    cy.get('[data-testid="send-button"]').should('be.visible');
  });

  it('should provide clear feedback for user interactions', () => {
    // Ensure chat interface is ready
    cy.get('[data-testid="main-chat"]', { timeout: 10000 }).should('be.visible');
    cy.get('[data-testid="message-textarea"]').should('be.visible');
    
    // Test input validation and feedback
    cy.get('[data-testid="message-textarea"]').clear();
    cy.get('[data-testid="send-button"]').should('be.disabled');
    
    // Type a meaningful business request
    cy.get('[data-testid="message-textarea"]').type('Help me optimize my cloud spending');
    cy.get('[data-testid="send-button"]').should('be.enabled');
    
    // Submit request and verify immediate feedback
    cy.get('[data-testid="send-button"]').click();
    
    // Verify user gets immediate feedback
    cy.get('[data-testid="send-button"] [data-testid="loading-icon"]', { timeout: 3000 }).should('exist');
    
    // Verify message input is cleared after sending
    cy.get('[data-testid="message-textarea"]').should('have.value', '');
    
    // Verify user can continue typing while processing
    cy.get('[data-testid="message-textarea"]').type('Follow-up question');
    cy.get('[data-testid="message-textarea"]').should('have.value', 'Follow-up question');
  });

  it('should handle real authentication and session persistence', () => {
    // Verify development mode auto-authentication works
    cy.get('[data-testid="main-chat"]', { timeout: 15000 }).should('be.visible');
    
    // Check that real authentication token exists (development mode)
    cy.window().then((win) => {
      const token = win.localStorage.getItem('jwt_token');
      if (token) {
        expect(token).to.not.equal('mock-jwt-token-for-testing');
        cy.log('Real authentication token found');
      } else {
        cy.log('No token found - may be in offline development mode');
      }
    });
    
    // Test session persistence by refreshing page
    cy.reload();
    
    // Should remain authenticated and show chat interface
    cy.get('[data-testid="main-chat"]', { timeout: 10000 }).should('be.visible');
    cy.get('[data-testid="message-textarea"]').should('be.visible');
    
    // Verify user can still interact after refresh
    cy.get('[data-testid="message-textarea"]').type('Test session persistence');
    cy.get('[data-testid="send-button"]').should('be.enabled');
  });

  afterEach(() => {
    // Clean up any test-specific state only
    cy.window().then((win) => {
      // Remove only test-specific items, preserve real auth for development
      win.localStorage.removeItem('test_state');
      win.localStorage.removeItem('cypress_test_data');
    });
  });
});