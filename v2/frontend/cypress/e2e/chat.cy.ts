describe('Chat UI', () => {
  beforeEach(() => {
    cy.visit('/chat');
  });

  it('should send and receive messages', () => {
    cy.get('input[placeholder="Type your message..."]').type('Hello, world!');
    cy.get('button').contains('Send').click();

    // Assert that the user's message is displayed
    cy.get('.bg-blue-50').should('contain', 'Hello, world!');

    // Mock a response from the websocket
    cy.window().then((win) => {
      const message = {
        type: 'message',
        payload: {
          id: '1',
          created_at: new Date().toISOString(),
          content: 'This is a response from the agent.',
          type: 'agent',
          sub_agent_name: 'Test Agent',
          displayed_to_user: true,
        },
      };
      // @ts-ignore
      win.ws.onmessage({ data: JSON.stringify(message) });
    });

    // Assert that the agent's message is displayed
    cy.get('.bg-gray-50').should('contain', 'This is a response from the agent.');
  });

  it('should show and hide raw data', () => {
    // Mock a message with raw data
    cy.window().then((win) => {
      const message = {
        type: 'message',
        payload: {
          id: '2',
          created_at: new Date().toISOString(),
          content: 'This message has raw data.',
          type: 'agent',
          sub_agent_name: 'Test Agent',
          raw_data: { key: 'value' },
          displayed_to_user: true,
        },
      };
      // @ts-ignore
      win.ws.onmessage({ data: JSON.stringify(message) });
    });

    cy.get('.bg-gray-50').should('contain', 'This message has raw data.');
    cy.get('span').contains('View Raw Data').click();
    cy.get('.react-json-view').should('be.visible');
  });
});
