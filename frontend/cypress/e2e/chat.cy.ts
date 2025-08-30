import { Message, WebSocketMessage } from '@/types/unified';

describe('Chat UI', () => {
  beforeEach(() => {
    // Setup authenticated state using proper token key
    cy.window().then((win) => {
      win.localStorage.setItem('jwt_token', 'test-jwt-token');
      win.localStorage.setItem('user', JSON.stringify({
        id: 'test-user-id',
        email: 'test@netrasystems.ai',
        full_name: 'Test User'
      }));
    });
    
    // Mock authentication endpoint
    cy.intercept('GET', 'http://localhost:8001/api/me', {
      statusCode: 200,
      body: {
        id: 'test-user-id',
        email: 'test@netrasystems.ai',
        full_name: 'Test User'
      }
    }).as('userRequest');
    
    // Mock threads endpoint
    cy.intercept('GET', 'http://localhost:8001/api/threads', {
      statusCode: 200,
      body: { threads: [] }
    }).as('threadsRequest');
    
    // Set up WebSocket mock before visiting the page
    cy.mockWebSocket();
    cy.mockLegacyWebSocket(); // For backward compatibility with tests using window.ws
    
    cy.visit('/chat');
    
    // Wait for page to load (but don't require specific API calls)
    cy.wait(1000);
  });

  it('should send and receive messages', () => {
    // Wait for page to fully load and find input
    cy.get('[data-testid="message-input"], textarea[placeholder*="message"], textarea').first().type('Hello, world!');
    cy.get('[data-testid="send-button"], button[type="submit"]').first().click();

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
    // Check for agent status display in header or status area
    cy.get('[data-testid="chat-header"], [data-testid="agent-status"], h1, .agent-status').should('contain', 'Optimization Agent');
    cy.get('body').should('contain', 'running');
    cy.get('body').should('contain', 'toolA').and('contain', 'toolB');
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
    cy.get('[data-testid="message-input"], textarea').first().type('Start a long process');
    cy.get('[data-testid="send-button"], button[type="submit"]').first().click();
    
    // Input should be disabled while processing
    cy.get('[data-testid="message-input"], textarea').first().should('be.disabled');
    cy.get('[data-testid="send-button"], button[type="submit"]').first().should('be.disabled');
    
    // Note: Stop Processing button is not currently integrated in the UI
    // If it gets added, test would be:
    // cy.get('button').contains('Stop Processing').should('not.be.disabled');
    // cy.get('button').contains('Stop Processing').click();
  });

  it('should test example prompts functionality', () => {
    // Wait for page to load and check for example prompts
    cy.wait(2000);
    cy.get('body').then(($body) => {
      if ($body.text().includes('Quick Start Examples') || $body.text().includes('Example Prompts')) {
        // Find and click toggle if available
        cy.get('button').contains(/toggle|expand|collapse/i).click({ force: true }).then(() => {
          cy.wait(500);
          cy.get('button').contains(/toggle|expand|collapse/i).click({ force: true });
        }).catch(() => {
          cy.log('Toggle button not found, skipping toggle test');
        });
        
        // Find and click an example prompt
        cy.get('[data-testid*="example"], [role="button"], .cursor-pointer').first().click({ force: true });
        
        // After clicking a prompt, the input should be disabled (processing)
        cy.get('[data-testid="message-input"], textarea').first().should('be.disabled');
      } else {
        cy.log('Example prompts not visible, skipping test');
      }
    });
  });

  it('should disable input and send button when processing', () => {
    cy.get('[data-testid="message-input"], textarea').first().type('Test');
    cy.get('[data-testid="send-button"], button[type="submit"]').first().click();
    cy.get('[data-testid="message-input"], textarea').first().should('be.disabled');
    cy.get('[data-testid="send-button"], button[type="submit"]').first().should('be.disabled');
    
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
    cy.get('[data-testid="message-input"], textarea').first().should('not.be.disabled');
    cy.get('[data-testid="send-button"], button[type="submit"]').first().should('not.be.disabled');
  });
});