describe('Debug Login Page', () => {
  it('should show what is on login page', () => {
    cy.visit('/login');
    
    // Wait for page to load
    cy.wait(2000);
    
    // Log the page content
    cy.get('body').then(($body) => {
      cy.log('Page text:', $body.text());
      
      // Check for any buttons
      const buttons = $body.find('button');
      cy.log(`Found ${buttons.length} buttons`);
      buttons.each((i, btn) => {
        cy.log(`Button ${i}: "${btn.textContent}"`);
      });
      
      // Check for inputs
      const inputs = $body.find('input');
      cy.log(`Found ${inputs.length} inputs`);
      inputs.each((i, input) => {
        cy.log(`Input ${i}: type="${input.type}", placeholder="${input.placeholder}"`);
      });
    });
    
    // Take a screenshot for visual debugging
    cy.screenshot('login-page-debug');
  });
});