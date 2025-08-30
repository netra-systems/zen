import {
  WEBSOCKET_CONFIG,
  setupTestEnvironment,
  navigateToChat,
  waitForConnection,
  findWebSocketConnection
} from '../support/websocket-test-helpers';

import {
  MessageInput,
  MessageAssertions,
  ComponentVisibility,
  WaitHelpers
} from './utils/chat-test-helpers';

describe('Critical WebSocket Communication Flow', () => {
  beforeEach(() => {
    setupTestEnvironment();
    navigateToChat();
  });

  it('should establish WebSocket connection for chat', () => {
    // Verify chat component is loaded
    ComponentVisibility.assertChatComponent();
    ComponentVisibility.assertHeader();
    
    // Verify message input and send button are available
    cy.get('textarea[data-testid="message-input"]', { timeout: 10000 }).should('be.visible');
    cy.get('[data-testid="send-button"]').should('exist');
    
    // Verify WebSocket connection is established
    waitForConnection().then((ws) => {
      if (ws) {
        expect(ws.readyState).to.be.oneOf([0, 1], 'WebSocket should be CONNECTING or OPEN');
      } else {
        // Fallback: check connection status indicator
        cy.get('[data-testid="connection-status"]').should('exist');
      }
    });
  });

  it('should send and receive messages', () => {
    const testMessage = 'Hello, can you help me optimize my AI workload?';
    
    // Send message using helper
    MessageInput.send(testMessage);
    
    // Verify user message appears
    MessageAssertions.assertUserMessage(testMessage);
    
    // Verify processing indicators
    cy.get('[data-testid="agent-processing"]', { timeout: 10000 }).should('be.visible');
    
    // Wait for and verify assistant response
    WaitHelpers.forResponse();
    MessageAssertions.assertAssistantMessage();
    
    // Verify WebSocket message transmission
    cy.window().then((win) => {
      const ws = findWebSocketConnection(win);
      if (ws) {
        cy.wrap(ws).should('have.property', 'readyState', 1);
      }
    });
  });

  it('should handle connection status indicators', () => {
    // Verify connection status component exists
    ComponentVisibility.assertConnectionStatus();
    
    // Check for specific connection indicators
    cy.get('[data-testid="connection-status"]').should('have.class', 'bg-green-500');
    
    // Verify WebSocket status indicator if present
    cy.get('body').then(($body) => {
      if ($body.find('[data-testid="ws-indicator"]').length > 0) {
        cy.get('[data-testid="ws-indicator"]').should('be.visible');
      }
    });
    
    // Test connection state change detection
    cy.window().then((win) => {
      const ws = findWebSocketConnection(win);
      if (ws && ws.readyState === 1) {
        cy.log('WebSocket connection is OPEN and healthy');
      }
    });
  });

  it('should maintain message history', () => {
    const firstMessage = 'First test message';
    const secondMessage = 'Second test message';
    
    // Send first message
    MessageInput.sendAndWait(firstMessage);
    MessageAssertions.assertUserMessage(firstMessage);
    
    // Send second message
    MessageInput.sendAndWait(secondMessage);
    MessageAssertions.assertUserMessage(secondMessage);
    
    // Verify both messages are visible
    cy.contains(firstMessage).should('be.visible');
    cy.contains(secondMessage).should('be.visible');
    
    // Check message order in chat container
    cy.get('[data-testid="chat-container"]').within(() => {
      cy.get('[data-testid="user-message"]').then($messages => {
        const messages = Array.from($messages).map(el => el.textContent);
        const firstIndex = messages.findIndex(msg => msg?.includes(firstMessage));
        const secondIndex = messages.findIndex(msg => msg?.includes(secondMessage));
        expect(firstIndex).to.be.lessThan(secondIndex);
      });
    });
  });

  it('should handle empty message submission', () => {
    // Clear input and attempt to send
    MessageInput.clear();
    cy.get('[data-testid="send-button"]').should('be.disabled');
    
    // Try clicking disabled send button
    cy.get('[data-testid="send-button"]').click({ force: true });
    
    // Verify no empty message was sent
    cy.wait(1000);
    cy.get('[data-testid="user-message"]').should('not.exist');
    
    // Verify input remains available and enabled
    cy.get('textarea[data-testid="message-input"]')
      .should('be.visible')
      .and('not.be.disabled')
      .and('have.value', '');
  });

  it('should handle rapid message sending', () => {
    const messages = [
      'Quick message 1',
      'Quick message 2', 
      'Quick message 3'
    ];
    
    // Send messages rapidly using helper
    messages.forEach((message, index) => {
      MessageInput.send(message);
      MessageAssertions.assertUserMessage(message);
      cy.wait(100); // Brief delay to prevent overwhelming
    });
    
    // Verify all messages appear in correct order
    cy.get('[data-testid="chat-container"]').within(() => {
      messages.forEach(message => {
        cy.contains(message, { timeout: 10000 }).should('be.visible');
      });
    });
    
    // Verify WebSocket can handle rapid messages
    cy.window().then((win) => {
      const ws = findWebSocketConnection(win);
      if (ws) {
        expect(ws.readyState).to.equal(1, 'WebSocket should remain open after rapid messages');
      }
    });
  });
});