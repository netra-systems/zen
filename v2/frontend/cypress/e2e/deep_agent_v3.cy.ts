
describe('Deep Agent v3 End-to-End Test', () => {
  it('should run a deep agent analysis and display the response', () => {
    cy.visit('/deep-agent/v3');

    cy.get('textarea').type('I need to reduce costs by 20% and improve latency by 2x.');

    cy.get('button').contains('Run').click();

    cy.get('h2').contains('Response').should('be.visible');
  });
});
