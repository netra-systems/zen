/**
 * Check what's actually on the chat page
 */

describe('Page Content Investigation', () => {
  it('should show what elements are on the page', () => {
    cy.visit('/chat');
    cy.get('body').should('be.visible');
    cy.wait(5000); // Give app time to initialize
    
    // Get all classes that contain blue or emerald
    cy.get('body').then(($body) => {
      const elements = $body.find('*');
      let blueElements = [];
      let emeraldElements = [];
      
      elements.each((_, el) => {
        const className = el.className;
        if (typeof className === 'string') {
          if (className.includes('blue')) {
            blueElements.push(className);
          }
          if (className.includes('emerald')) {
            emeraldElements.push(className);
          }
        }
      });
      
      cy.log('Blue classes found:', blueElements);
      cy.log('Emerald classes found:', emeraldElements);
      
      // Take a screenshot of the current state
      cy.screenshot('chat-page-current-state');
    });
    
    // Check if there are any visible text elements
    cy.get('body').then(($body) => {
      const text = $body.text();
      cy.log('Page text content (first 500 chars):', text.substring(0, 500));
    });
  });
});