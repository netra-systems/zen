import { Message, WebSocketMessage } from '@/types/chat';

describe('Thread Management and Conversation History', () => {
  beforeEach(() => {
    // Setup authenticated state
    cy.window().then((win) => {
      win.localStorage.setItem('jwt_token', 'test-jwt-token');
    });

    // Mock threads endpoint
    cy.intercept('GET', '/api/threads', {
      statusCode: 200,
      body: [
        {
          id: 'thread-1',
          title: 'LLM Optimization Discussion',
          created_at: new Date(Date.now() - 86400000).toISOString(),
          updated_at: new Date(Date.now() - 3600000).toISOString(),
          user_id: 1,
          message_count: 5
        },
        {
          id: 'thread-2',
          title: 'Cost Analysis Project',
          created_at: new Date(Date.now() - 172800000).toISOString(),
          updated_at: new Date(Date.now() - 7200000).toISOString(),
          user_id: 1,
          message_count: 3
        },
        {
          id: 'thread-3',
          title: 'Performance Testing',
          created_at: new Date(Date.now() - 259200000).toISOString(),
          updated_at: new Date(Date.now() - 86400000).toISOString(),
          user_id: 1,
          message_count: 8
        }
      ]
    }).as('getThreads');

    cy.visit('/chat');
  });

  it('should display thread list and allow switching between threads', () => {
    // Open thread sidebar - use a more generic selector
    cy.get('button').contains('Threads').click({ timeout: 10000 });

    // Verify threads are displayed
    cy.contains('LLM Optimization Discussion').should('be.visible');
    cy.contains('Cost Analysis Project').should('be.visible');
    cy.contains('Performance Testing').should('be.visible');

    // Mock thread messages for thread-1
    cy.intercept('GET', '/api/threads/thread-1/messages', {
      statusCode: 200,
      body: [
        {
          id: 'msg-1',
          thread_id: 'thread-1',
          content: 'How can I optimize my LLM inference?',
          type: 'user',
          created_at: new Date(Date.now() - 3700000).toISOString()
        },
        {
          id: 'msg-2',
          thread_id: 'thread-1',
          content: 'I can help you optimize your LLM inference. Let me analyze your current setup.',
          type: 'agent',
          sub_agent_name: 'OptimizationsCoreSubAgent',
          created_at: new Date(Date.now() - 3650000).toISOString()
        }
      ]
    }).as('getThread1Messages');

    // Click on first thread
    cy.contains('LLM Optimization Discussion').click();
    cy.wait('@getThread1Messages');

    // Verify messages from thread are loaded
    cy.contains('How can I optimize my LLM inference?').should('be.visible');
    cy.contains('I can help you optimize your LLM inference').should('be.visible');

    // Mock thread messages for thread-2
    cy.intercept('GET', '/api/threads/thread-2/messages', {
      statusCode: 200,
      body: [
        {
          id: 'msg-3',
          thread_id: 'thread-2',
          content: 'Analyze the cost of my current deployment',
          type: 'user',
          created_at: new Date(Date.now() - 7300000).toISOString()
        },
        {
          id: 'msg-4',
          thread_id: 'thread-2',
          content: 'Analyzing your deployment costs...',
          type: 'agent',
          sub_agent_name: 'DataSubAgent',
          created_at: new Date(Date.now() - 7250000).toISOString()
        }
      ]
    }).as('getThread2Messages');

    // Switch to second thread
    cy.contains('Cost Analysis Project').click();
    cy.wait('@getThread2Messages');

    // Verify different messages are shown
    cy.contains('Analyze the cost of my current deployment').should('be.visible');
    cy.contains('Analyzing your deployment costs').should('be.visible');
    
    // Previous thread messages should not be visible
    cy.contains('How can I optimize my LLM inference?').should('not.exist');
  });

  it('should create a new thread and maintain conversation context', () => {
    // Click new thread button - use a more generic selector
    cy.get('button').contains('New').click({ timeout: 10000 });

    // Mock new thread creation
    cy.intercept('POST', '/api/threads', {
      statusCode: 201,
      body: {
        id: 'thread-new',
        title: 'New Conversation',
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
        user_id: 1,
        message_count: 0
      }
    }).as('createThread');

    // Type and send first message in new thread
    const firstMessage = 'Start a new optimization analysis';
    cy.get('input[placeholder*="message"]', { timeout: 10000 }).type(firstMessage);
    cy.get('button').contains('Send').click();

    // Wait for thread creation
    cy.wait('@createThread');

    // Verify message is sent with thread context
    cy.get('.bg-blue-50').should('contain', firstMessage);

    // Simulate agent response with thread context
    cy.window().then((win) => {
      const agentResponse: WebSocketMessage = {
        type: 'message',
        payload: {
          id: 'msg-new-1',
          thread_id: 'thread-new',
          created_at: new Date().toISOString(),
          content: 'Starting new optimization analysis for your system...',
          type: 'agent',
          sub_agent_name: 'TriageSubAgent',
          displayed_to_user: true
        } as Message
      };
      // @ts-ignore
      win.ws.onmessage({ data: JSON.stringify(agentResponse) });
    });

    cy.contains('Starting new optimization analysis').should('be.visible');

    // Send follow-up message in same thread
    const followUp = 'Focus on GPU utilization';
    cy.get('input[placeholder*="message"]').type(followUp);
    cy.get('button').contains('Send').click();

    // Verify conversation maintains context
    cy.get('.bg-blue-50').eq(1).should('contain', followUp);

    // Simulate context-aware response
    cy.window().then((win) => {
      const contextResponse: WebSocketMessage = {
        type: 'message',
        payload: {
          id: 'msg-new-2',
          thread_id: 'thread-new',
          created_at: new Date().toISOString(),
          content: 'Focusing the optimization analysis on GPU utilization as requested...',
          type: 'agent',
          sub_agent_name: 'OptimizationsCoreSubAgent',
          displayed_to_user: true
        } as Message
      };
      // @ts-ignore
      win.ws.onmessage({ data: JSON.stringify(contextResponse) });
    });

    cy.contains('Focusing the optimization analysis on GPU utilization').should('be.visible');
  });

  it('should search and filter threads', () => {
    // Open thread sidebar
    cy.get('button').contains('Threads').click({ timeout: 10000 });

    // Type in search box
    cy.get('input[placeholder="Search threads..."]').type('optimization');

    // Mock filtered threads endpoint
    cy.intercept('GET', '/api/threads?search=optimization', {
      statusCode: 200,
      body: [
        {
          id: 'thread-1',
          title: 'LLM Optimization Discussion',
          created_at: new Date(Date.now() - 86400000).toISOString(),
          updated_at: new Date(Date.now() - 3600000).toISOString(),
          user_id: 1,
          message_count: 5
        }
      ]
    }).as('searchThreads');

    // Trigger search
    cy.get('button[aria-label="Search"]').click();
    cy.wait('@searchThreads');

    // Verify filtered results
    cy.contains('LLM Optimization Discussion').should('be.visible');
    cy.contains('Cost Analysis Project').should('not.exist');
    cy.contains('Performance Testing').should('not.exist');

    // Clear search
    cy.get('input[placeholder="Search threads..."]').clear();
    cy.get('button[aria-label="Search"]').click();
    cy.wait('@getThreads');

    // All threads should be visible again
    cy.contains('Cost Analysis Project').should('be.visible');
    cy.contains('Performance Testing').should('be.visible');
  });

  it('should delete a thread and update the list', () => {
    // Open thread sidebar
    cy.get('button').contains('Threads').click({ timeout: 10000 });

    // Hover over thread to show delete button
    cy.contains('Performance Testing').parent().trigger('mouseenter');
    
    // Click delete button
    cy.get('button[aria-label="Delete thread"]').last().click();

    // Confirm deletion in modal
    cy.contains('Are you sure you want to delete this thread?').should('be.visible');
    
    // Mock delete endpoint
    cy.intercept('DELETE', '/api/threads/thread-3', {
      statusCode: 204
    }).as('deleteThread');

    // Mock updated threads list
    cy.intercept('GET', '/api/threads', {
      statusCode: 200,
      body: [
        {
          id: 'thread-1',
          title: 'LLM Optimization Discussion',
          created_at: new Date(Date.now() - 86400000).toISOString(),
          updated_at: new Date(Date.now() - 3600000).toISOString(),
          user_id: 1,
          message_count: 5
        },
        {
          id: 'thread-2',
          title: 'Cost Analysis Project',
          created_at: new Date(Date.now() - 172800000).toISOString(),
          updated_at: new Date(Date.now() - 7200000).toISOString(),
          user_id: 1,
          message_count: 3
        }
      ]
    }).as('getUpdatedThreads');

    // Confirm deletion
    cy.get('button').contains('Delete').click();
    cy.wait('@deleteThread');
    cy.wait('@getUpdatedThreads');

    // Verify thread is removed
    cy.contains('Performance Testing').should('not.exist');
    cy.contains('LLM Optimization Discussion').should('be.visible');
    cy.contains('Cost Analysis Project').should('be.visible');
  });

  it('should rename a thread', () => {
    // Open thread sidebar
    cy.get('button').contains('Threads').click({ timeout: 10000 });

    // Select thread to rename
    cy.contains('Cost Analysis Project').parent().trigger('mouseenter');
    
    // Click rename button
    cy.get('button[aria-label="Rename thread"]').first().click();

    // Input new name
    const newName = 'Updated Cost Analysis';
    cy.get('input[value="Cost Analysis Project"]').clear().type(newName);

    // Mock rename endpoint
    cy.intercept('PATCH', '/api/threads/thread-2', {
      statusCode: 200,
      body: {
        id: 'thread-2',
        title: newName,
        created_at: new Date(Date.now() - 172800000).toISOString(),
        updated_at: new Date().toISOString(),
        user_id: 1,
        message_count: 3
      }
    }).as('renameThread');

    // Save new name
    cy.get('button[aria-label="Save thread name"]').click();
    cy.wait('@renameThread');

    // Verify thread is renamed
    cy.contains(newName).should('be.visible');
    cy.contains('Cost Analysis Project').should('not.exist');
  });

  it('should load more messages on scroll', () => {
    // Mock initial messages
    cy.intercept('GET', '/api/threads/thread-1/messages?limit=20&offset=0', {
      statusCode: 200,
      body: Array.from({ length: 20 }, (_, i) => ({
        id: `msg-${i}`,
        thread_id: 'thread-1',
        content: `Message ${i}`,
        type: i % 2 === 0 ? 'user' : 'agent',
        created_at: new Date(Date.now() - (i * 60000)).toISOString()
      }))
    }).as('getInitialMessages');

    // Load thread
    cy.get('button').contains('Threads').click({ timeout: 10000 });
    cy.contains('LLM Optimization Discussion').click();
    cy.wait('@getInitialMessages');

    // Mock older messages
    cy.intercept('GET', '/api/threads/thread-1/messages?limit=20&offset=20', {
      statusCode: 200,
      body: Array.from({ length: 20 }, (_, i) => ({
        id: `msg-${i + 20}`,
        thread_id: 'thread-1',
        content: `Older Message ${i + 20}`,
        type: i % 2 === 0 ? 'user' : 'agent',
        created_at: new Date(Date.now() - ((i + 20) * 60000)).toISOString()
      }))
    }).as('getOlderMessages');

    // Scroll to top to trigger load more
    cy.get('.overflow-y-auto').scrollTo('top');
    cy.wait('@getOlderMessages');

    // Verify older messages are loaded
    cy.contains('Older Message 20').should('be.visible');
    cy.contains('Older Message 39').should('be.visible');

    // Original messages should still be visible
    cy.contains('Message 0').should('be.visible');
  });

  it('should export thread conversation', () => {
    // Load a thread
    cy.get('button').contains('Threads').click({ timeout: 10000 });
    
    // Mock thread messages
    cy.intercept('GET', '/api/threads/thread-1/messages', {
      statusCode: 200,
      body: [
        {
          id: 'msg-1',
          content: 'Test question',
          type: 'user',
          created_at: new Date().toISOString()
        },
        {
          id: 'msg-2',
          content: 'Test response',
          type: 'agent',
          created_at: new Date().toISOString()
        }
      ]
    }).as('getMessages');

    cy.contains('LLM Optimization Discussion').click();
    cy.wait('@getMessages');

    // Mock export endpoint
    cy.intercept('GET', '/api/threads/thread-1/export', {
      statusCode: 200,
      headers: {
        'content-type': 'application/json',
        'content-disposition': 'attachment; filename="thread-export.json"'
      },
      body: {
        thread: {
          id: 'thread-1',
          title: 'LLM Optimization Discussion'
        },
        messages: [
          { content: 'Test question', type: 'user' },
          { content: 'Test response', type: 'agent' }
        ]
      }
    }).as('exportThread');

    // Click export button
    cy.get('button[aria-label="Export conversation"]').click();
    
    // Select export format
    cy.contains('Export as JSON').click();
    cy.wait('@exportThread');

    // Verify download initiated (browser handles actual download)
    cy.get('@exportThread').should('have.been.called');
  });
});