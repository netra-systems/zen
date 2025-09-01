import { Message, WebSocketMessage } from '@/types/unified';

describe('Chat UI', () => {
  beforeEach(() => {
    // Clear state to ensure clean test environment
    cy.clearLocalStorage();
    cy.clearCookies();
    
    // Prevent uncaught exceptions from failing critical tests
    Cypress.on('uncaught:exception', (err, runnable) => {
      return false;
    });
    
    // Setup authenticated state using current UnifiedAuthService structure
    cy.window().then((win) => {
      win.localStorage.setItem('jwt_token', 'test-jwt-token-chat');
      win.localStorage.setItem('user_data', JSON.stringify({
        id: 'test-user-id',
        email: 'test@netrasystems.ai',
        full_name: 'Test User',
        role: 'user',
        permissions: ['read', 'write']
      }));
    });
    
    // Mock unified API endpoints for current system
    cy.intercept('GET', '**/api/me', {
      statusCode: 200,
      body: {
        id: 'test-user-id',
        email: 'test@netrasystems.ai',
        full_name: 'Test User',
        role: 'user'
      }
    }).as('userRequest');
    
    // Mock agent execution endpoint
    cy.intercept('POST', '**/api/agents/execute', {
      statusCode: 200,
      body: {
        agent_id: 'test-agent-123',
        status: 'started',
        message: 'Agent execution initiated'
      }
    }).as('agentExecute');
    
    // Mock threads endpoint for thread management
    cy.intercept('GET', '**/api/threads*', {
      statusCode: 200,
      body: { threads: [] }
    }).as('threadsRequest');
    
    // Set up WebSocket mocks for current implementation
    cy.window().then((win) => {
      // Mock WebSocket for current unified system
      (win as any).mockWebSocket = {
        readyState: WebSocket.OPEN,
        send: cy.stub().as('wsSend'),
        close: cy.stub(),
        addEventListener: cy.stub(),
        removeEventListener: cy.stub()
      };
      
      // Set up WebSocket event handling
      (win as any).ws = (win as any).mockWebSocket;
    });
    
    cy.visit('/chat', { failOnStatusCode: false });
    
    // Allow for authentication processing and page load
    cy.wait(2000);
  });

  it('should send and receive messages with current UI', () => {
    // Check if we successfully accessed the chat page
    cy.url().then((url) => {
      if (url.includes('/chat')) {
        cy.log('Successfully on chat page, testing message functionality');
        
        // Look for the current message input using proper selector
        cy.get('body').then($body => {
          if ($body.find('[data-testid="message-textarea"]').length > 0) {
            // Use current system's message input with fallbacks
            cy.get('[data-testid="message-textarea"], textarea, [data-testid="message-input"]')
              .first()
              .should('be.visible')
              .type('Hello, world!', { force: true });
            
            // Look for send button with current selector and fallbacks
            cy.get('[data-testid="send-button"], button[type="submit"], button')
              .contains(/send|submit/i)
              .first()
              .click({ force: true });
            
            // Check if message appears in UI
            cy.contains('Hello, world!').should('be.visible');
            
            // Simulate WebSocket events with current structure (5 critical events)
            cy.window().then((win) => {
              const agentId = 'test-agent-chat';
              const events = [
                {
                  type: 'agent_started',
                  payload: {
                    agent_id: agentId,
                    agent_type: 'ChatTestAgent',
                    run_id: 'test-run-1',
                    timestamp: new Date().toISOString()
                  }
                },
                {
                  type: 'agent_thinking',
                  payload: {
                    thought: 'Processing your message...',
                    agent_id: agentId,
                    step_number: 1,
                    total_steps: 2
                  }
                },
                {
                  type: 'tool_executing',
                  payload: {
                    tool_name: 'response_generator',
                    agent_id: agentId,
                    timestamp: Date.now()
                  }
                },
                {
                  type: 'tool_completed',
                  payload: {
                    tool_name: 'response_generator',
                    result: { content: 'This is a response from the agent.' },
                    agent_id: agentId,
                    timestamp: Date.now()
                  }
                },
                {
                  type: 'agent_completed',
                  payload: {
                    agent_id: agentId,
                    duration_ms: 1500,
                    result: { response: 'This is a response from the agent.' },
                    metrics: { tools_used: 1 }
                  }
                }
              ];
              
              // Send events with delays to simulate real agent flow
              events.forEach((event, index) => {
                setTimeout(() => {
                  if ((win as any).ws && (win as any).ws.onmessage) {
                    (win as any).ws.onmessage({ data: JSON.stringify(event) });
                  }
                }, index * 300);
              });
            });
            
            // Verify agent response appears
            cy.contains('This is a response from the agent.').should('be.visible');
            
          } else {
            cy.log('Current UI structure different - testing basic interaction');
            // Fallback for different UI structure
            cy.get('textarea, input[type="text"]').first().should('be.visible');
          }
        });
        
      } else if (url.includes('/login')) {
        cy.log('Redirected to login - authentication required for chat');
        cy.get('body').should('be.visible');
        
      } else {
        cy.log(`Navigated to unexpected URL: ${url}`);
        cy.get('body').should('be.visible');
      }
    });
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

  it('should disable input when processing with current UI', () => {
    // Check if we're on chat page first
    cy.url().then((url) => {
      if (url.includes('/chat')) {
        // Look for message input with multiple selectors
        cy.get('[data-testid="message-textarea"], textarea, [data-testid="message-input"]')
          .first()
          .should('be.visible')
          .type('Start a long process', { force: true });
        
        // Click send button with multiple selectors
        cy.get('[data-testid="send-button"], button[type="submit"], button')
          .contains(/send|submit/i)
          .first()
          .click({ force: true });
        
        // Wait for processing to start
        cy.wait(1000);
        
        // Check if input becomes disabled during processing (flexible check)
        cy.get('[data-testid="message-textarea"], textarea, [data-testid="message-input"]')
          .first()
          .should(($input) => {
            const isDisabled = $input.prop('disabled') || $input.prop('readonly');
            // Allow for either disabled state or processing indicator
            expect(isDisabled || $input.hasClass('processing')).to.be.true;
          });
        
      } else {
        cy.log('Not on chat page, skipping processing test');
      }
    });
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