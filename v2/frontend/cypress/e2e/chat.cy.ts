import { Message, WebSocketMessage } from '@/types/chat';

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
      const payload: Message = {
        id: '1',
        created_at: new Date().toISOString(),
        content: 'This is a response from the agent.',
        type: 'agent',
        sub_agent_name: 'Test Agent',
        displayed_to_user: true,
      };
      const message: WebSocketMessage = {
        type: 'message',
        payload: payload,
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
      const payload: Message = {
        id: '2',
        created_at: new Date().toISOString(),
        content: 'This message has raw data.',
        type: 'agent',
        sub_agent_name: 'Test Agent',
        raw_data: { key: 'value' },
        displayed_to_user: true,
      };
      const message: WebSocketMessage = {
        type: 'message',
        payload: payload,
      };
      // @ts-ignore
      win.ws.onmessage({ data: JSON.stringify(message) });
    });

    cy.get('.bg-gray-50').should('contain', 'This message has raw data.');
    cy.get('span').contains('View Raw Data').click();
    cy.get('.react-json-view').should('be.visible');
  });

  it('should display sub-agent name, status, and tools in the header', () => {
    // Mock a sub-agent update message
    cy.window().then((win) => {
      const message: WebSocketMessage = {
        type: 'sub_agent_update',
        payload: {
          subAgentName: 'Optimization Agent',
          subAgentStatus: {
            status: 'running',
            tools: ['toolA', 'toolB'],
          },
        },
      };
      // @ts-ignore
      win.ws.onmessage({ data: JSON.stringify(message) });
    });
    cy.get('h1').should('contain', 'Optimization Agent');
    cy.get('p').should('contain', 'running');
    cy.get('p').should('contain', 'Tools: toolA, toolB');
  });

  it('should display user messages with references', () => {
    cy.window().then((win) => {
      const payload: Message = {
        id: '3',
        created_at: new Date().toISOString(),
        content: 'User query with references.',
        type: 'user',
        displayed_to_user: true,
        references: ['ref_doc_1', 'ref_doc_2'],
      };
      const message: WebSocketMessage = {
        type: 'message',
        payload: payload,
      };
      // @ts-ignore
      win.ws.onmessage({ data: JSON.stringify(message) });
    });
    cy.get('.bg-blue-50').should('contain', 'User query with references.');
    cy.get('.bg-blue-50').should('contain', 'References:');
    cy.get('.bg-blue-50').should('contain', 'ref_doc_1');
    cy.get('.bg-blue-50').should('contain', 'ref_doc_2');
  });

  it('should test the Stop Processing button', () => {
    cy.get('input[placeholder="Type your message..."]').type('Start a long process');
    cy.get('button').contains('Send').click();
    cy.get('button').contains('Stop Processing').should('not.be.disabled');
    cy.get('button').contains('Stop Processing').click();
    cy.get('button').contains('Stop Processing').should('be.disabled');
  });

  it('should test example prompts functionality', () => {
    cy.get('h2').contains('Example Prompts').should('be.visible');
    cy.get('button').contains('Show').click(); // Expand if collapsed
    cy.get('.cursor-pointer').first().click();
    cy.get('input[placeholder="Agent is thinking..."]').should('be.disabled');
    cy.get('button').contains('Show').should('be.visible'); // Panel should collapse
  });

  it('should disable input and send button when processing', () => {
    cy.get('input[placeholder="Type your message..."]').type('Test');
    cy.get('button').contains('Send').click();
    cy.get('input[placeholder="Agent is thinking..."]').should('be.disabled');
    cy.get('button').contains('Send').should('be.disabled');
  });
});