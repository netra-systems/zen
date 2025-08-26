import { Message, WebSocketMessage } from '@/types/unified';

describe('Chat UI', () => {
  beforeEach(() => {
    // Setup authenticated state
    cy.window().then((win) => {
      win.localStorage.setItem('authToken', 'test-token');
      win.localStorage.setItem('jwt_token', 'test-jwt-token');
    });
    
    // Mock authentication endpoint
    cy.intercept('GET', '/api/me', {
      statusCode: 200,
      body: {
        id: 1,
        email: 'test@netrasystems.ai',
        full_name: 'Test User'
      }
    }).as('userRequest');
    
    // Mock threads endpoint
    cy.intercept('GET', '/api/threads', {
      statusCode: 200,
      body: []
    }).as('threadsRequest');
    
    // Set up WebSocket mock before visiting the page
    cy.mockWebSocket();
    cy.mockLegacyWebSocket(); // For backward compatibility with tests using window.ws
    
    cy.visit('/chat');
    
    // Wait for page to load (but don't require specific API calls)
    cy.wait(1000);
  });

  it('should send and receive messages', () => {
    cy.get('textarea[aria-label="Message input"]').type('Hello, world!');
    cy.get('button[aria-label="Send message"]').click();

    // Assert that the user's message is displayed
    cy.contains('Hello, world!').should('be.visible');

    // Mock a response from the websocket
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
    
    // Simulate WebSocket message using legacy approach
    cy.window().then((win) => {
      if ((win as any).ws && (win as any).ws.onmessage) {
        (win as any).ws.onmessage({ data: JSON.stringify(message) });
      }
    });

    // Assert that the agent's message is displayed
    cy.contains('This is a response from the agent.').should('be.visible');
  });

  it('should show and hide raw data', () => {
    // Mock a message with raw data
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
    
    // Simulate WebSocket message using legacy approach
    cy.window().then((win) => {
      if ((win as any).ws && (win as any).ws.onmessage) {
        (win as any).ws.onmessage({ data: JSON.stringify(message) });
      }
    });

    cy.contains('This message has raw data.').should('be.visible');
    cy.get('button').contains('View Raw Data').click();
    cy.get('.react-json-view').should('be.visible');
  });

  it('should display sub-agent name, status, and tools in the header', () => {
    // Mock a sub-agent update message
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
    
    // Simulate WebSocket message using legacy approach
    cy.window().then((win) => {
      if ((win as any).ws && (win as any).ws.onmessage) {
        (win as any).ws.onmessage({ data: JSON.stringify(message) });
      }
    });
    cy.get('h1').should('contain', 'Optimization Agent');
    cy.get('p').should('contain', 'running');
    cy.get('p').should('contain', 'Tools: toolA, toolB');
  });

  it('should display user messages with references', () => {
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
    
    // Simulate WebSocket message using legacy approach
    cy.window().then((win) => {
      if ((win as any).ws && (win as any).ws.onmessage) {
        (win as any).ws.onmessage({ data: JSON.stringify(message) });
      }
    });
    cy.contains('User query with references.').should('be.visible');
    cy.contains('References:').should('be.visible');
    cy.contains('ref_doc_1').should('be.visible');
    cy.contains('ref_doc_2').should('be.visible');
  });

  it('should disable input when processing', () => {
    // Test that input is disabled during processing
    cy.get('textarea[aria-label="Message input"]').type('Start a long process');
    cy.get('button[aria-label="Send message"]').click();
    
    // Input should be disabled while processing
    cy.get('textarea[aria-label="Message input"]').should('be.disabled');
    cy.get('button[aria-label="Send message"]').should('be.disabled');
    
    // Note: Stop Processing button is not currently integrated in the UI
    // If it gets added, test would be:
    // cy.get('button').contains('Stop Processing').should('not.be.disabled');
    // cy.get('button').contains('Stop Processing').click();
  });

  it('should test example prompts functionality', () => {
    // Check for Quick Start Examples (not Example Prompts)
    cy.get('h2').contains('Quick Start Examples').should('be.visible');
    
    // The collapsible uses ChevronDown icon button for toggling
    cy.get('button[aria-label="Toggle example prompts"]').click(); // Collapse
    cy.get('button[aria-label="Toggle example prompts"]').click(); // Expand again
    
    // Click on one of the example prompt cards
    cy.get('[role="button"]').first().click();
    
    // After clicking a prompt, the input should be disabled (processing)
    cy.get('textarea[aria-label="Message input"]').should('be.disabled');
    
    // The example prompts panel should collapse after sending
    cy.get('h2').contains('Quick Start Examples').should('exist');
  });

  it('should disable input and send button when processing', () => {
    cy.get('textarea[aria-label="Message input"]').type('Test');
    cy.get('button[aria-label="Send message"]').click();
    cy.get('textarea[aria-label="Message input"]').should('be.disabled');
    cy.get('button[aria-label="Send message"]').should('be.disabled');
    
    // Simulate processing complete
    cy.window().then((win) => {
      if ((win as any).ws && (win as any).ws.onmessage) {
        (win as any).ws.onmessage({ 
          data: JSON.stringify({
            type: 'processing_complete',
            payload: {}
          })
        });
      }
    });
    
    // Wait for UI to update
    cy.wait(500);
    
    // Input should be enabled again
    cy.get('textarea[aria-label="Message input"]').should('not.be.disabled');
    cy.get('button[aria-label="Send message"]').should('not.be.disabled');
  });
});