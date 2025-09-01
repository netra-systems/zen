describe('Debug Simple Agent Workflow', () => {
  beforeEach(() => {
    // Set up mock JWT token
    cy.window().then((win) => {
      const futureTimestamp = Math.floor(Date.now() / 1000) + (24 * 60 * 60);
      const mockPayload = btoa(JSON.stringify({
        sub: 'test-user-id',
        email: 'test@example.com',
        full_name: 'Test User',
        role: 'user',
        iat: Math.floor(Date.now() / 1000),
        exp: futureTimestamp
      }));
      const mockToken = `eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.${mockPayload}.mock-signature-for-testing`;
      win.localStorage.setItem('jwt_token', mockToken);
    });
    
    // Visit chat page
    cy.visit('/chat');
    
    // Wait longer and be more patient
    cy.wait(5000);
  });

  it('should debug what elements are present on the page', () => {
    // Debug authentication state
    cy.window().then((win) => {
      const token = win.localStorage.getItem('jwt_token');
      cy.log('JWT Token exists:', !!token);
      if (token) {
        cy.log('Token starts with:', token.substring(0, 50) + '...');
      }
    });

    // Check for Cypress detection
    cy.window().then((win) => {
      cy.log('Cypress detected:', !!(win as any).Cypress);
    });

    // Take screenshot
    cy.screenshot('page-state');

    // Check what's actually rendered
    cy.get('body').then(($body) => {
      cy.log('Body HTML length:', $body.html().length);
      cy.log('Body contains "Loading":', $body.html().includes('Loading'));
      cy.log('Body contains "Verifying":', $body.html().includes('Verifying'));
      cy.log('Body contains "textarea":', $body.html().includes('textarea'));
      cy.log('Body contains "message":', $body.html().includes('message'));
    });

    // Look for all textareas
    cy.get('body').then(() => {
      cy.document().then(doc => {
        const textareas = doc.querySelectorAll('textarea');
        cy.log(`Found ${textareas.length} textarea elements`);
        textareas.forEach((textarea, i) => {
          cy.log(`Textarea ${i}:`, {
            id: textarea.id,
            className: textarea.className,
            placeholder: textarea.placeholder,
            'data-testid': textarea.getAttribute('data-testid')
          });
        });
      });
    });

    // Look for any elements with testids
    cy.get('body').then(() => {
      cy.document().then(doc => {
        const testidElements = doc.querySelectorAll('[data-testid]');
        cy.log(`Found ${testidElements.length} elements with data-testid`);
        testidElements.forEach((el, i) => {
          cy.log(`Element ${i}:`, {
            tag: el.tagName,
            testid: el.getAttribute('data-testid'),
            className: el.className
          });
        });
      });
    });

    // Wait for any potential loading states to complete
    cy.wait(3000);

    // Check again after waiting
    cy.get('body').then(() => {
      cy.document().then(doc => {
        const textareas = doc.querySelectorAll('textarea');
        cy.log(`After waiting - Found ${textareas.length} textarea elements`);
      });
    });

    // Try to find the textarea with a more lenient approach
    cy.get('body').then(($body) => {
      if ($body.find('textarea[data-testid="message-textarea"]').length > 0) {
        cy.log('SUCCESS: Found message-textarea!');
        cy.get('textarea[data-testid="message-textarea"]').should('be.visible');
      } else if ($body.find('textarea').length > 0) {
        cy.log('Found some textarea but not with expected testid');
        cy.get('textarea').first().should('be.visible');
      } else {
        cy.log('ERROR: No textarea found at all');
        // Don't fail the test, just log the issue
      }
    });
  });
});