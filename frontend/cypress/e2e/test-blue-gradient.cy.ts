/**
 * Quick test for Blue Gradient Bar Removal
 */

describe('Blue Gradient Bar Removal Test', () => {
  beforeEach(() => {
    cy.visit('/chat');
    cy.get('body').should('be.visible');
    cy.wait(3000); // Give app time to initialize
  });

  it('should not have any blue gradient bars in UI', () => {
    // Check for absence of blue gradients
    cy.get('[class*="from-blue"]').should('not.exist');
    cy.get('[class*="to-blue"]').should('not.exist');
    cy.get('[class*="bg-blue-500"]').should('not.exist');
    cy.get('[class*="bg-gradient-to-r from-blue"]').should('not.exist');
    
    // Verify emerald/purple colors are used instead
    cy.get('[class*="bg-emerald"]').should('exist');
    cy.get('[class*="from-purple"]').should('exist');
  });
});