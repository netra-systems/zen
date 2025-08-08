
describe('Apex Optimizer Agent  End-to-End Test', () => {
    it('should run an Apex Optimizer Agent analysis and display the response', () => {
    cy.visit('/apex-optimizer-agent/');

    cy.get('textarea').type('I need to reduce costs by 20% and improve latency by 2x.');

    cy.get('button').contains('Run').click();

    cy.get('h2').contains('Response').should('be.visible');
  });
});
