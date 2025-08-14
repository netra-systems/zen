import { Message, WebSocketMessage } from '@/types/chat';

describe('Chat UI', () => {
  beforeEach(() => {
    cy.visit('/chat');
  });

  it('should send and receive messages', () => {
    cy.get('textarea[aria-label="Message input"]').type('Hello, world!');
    cy.get('button[aria-label="Send message"]').click();

    // Assert that the user's message is displayed
    cy.contains('Hello, world!').should('be.visible');

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
      (win as any).ws.onmessage({ data: JSON.stringify(message) });
    });

    // Assert that the agent's message is displayed
    cy.contains('This is a response from the agent.').should('be.visible');
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
      (win as any).ws.onmessage({ data: JSON.stringify(message) });
    });

    cy.contains('This message has raw data.').should('be.visible');
    cy.get('button').contains('View Raw Data').click();
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
      (win as any).ws.onmessage({ data: JSON.stringify(message) });
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
      (win as any).ws.onmessage({ data: JSON.stringify(message) });
    });
    cy.contains('User query with references.').should('be.visible');
    cy.contains('References:').should('be.visible');
    cy.contains('ref_doc_1').should('be.visible');
    cy.contains('ref_doc_2').should('be.visible');
  });

  it('should test the Stop Processing button', () => {
    cy.get('textarea[aria-label="Message input"]').type('Start a long process');
    cy.get('button[aria-label="Send message"]').click();
    cy.get('button').contains('Stop Processing').should('not.be.disabled');
    cy.get('button').contains('Stop Processing').click();
    cy.get('button').contains('Stop Processing').should('be.disabled');
  });

  it('should test example prompts functionality', () => {
    cy.get('h2').contains('Example Prompts').should('be.visible');
    cy.get('button').contains('Show').click(); // Expand if collapsed
    cy.get('.cursor-pointer').first().click();
    cy.get('textarea[aria-label="Message input"]').should('be.disabled');
    cy.get('button').contains('Show').should('be.visible'); // Panel should collapse
  });

  it('should disable input and send button when processing', () => {
    cy.get('textarea[aria-label="Message input"]').type('Test');
    cy.get('button[aria-label="Send message"]').click();
    cy.get('textarea[aria-label="Message input"]').should('be.disabled');
    cy.get('button[aria-label="Send message"]').should('be.disabled');
  });
});