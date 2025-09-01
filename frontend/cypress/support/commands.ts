/// <reference types="cypress" />

// Mock WebSocket implementation for tests
interface MockWebSocketCallbacks {
  onmessage?: (event: MessageEvent) => void;
  onopen?: () => void;
  onclose?: () => void;
  onerror?: (error: Event) => void;
}

class MockWebSocket {
  url: string;
  readyState: number = 0; // CONNECTING
  onmessage?: (event: MessageEvent) => void;
  onopen?: () => void;
  onclose?: () => void;
  onerror?: (error: Event) => void;
  
  constructor(url: string) {
    this.url = url;
    // Simulate connection opening
    setTimeout(() => {
      this.readyState = 1; // OPEN
      this.onopen?.();
    }, 10);
  }
  
  send(data: string | ArrayBuffer | Blob): void {
    // Mock send implementation
    // console output removed: console.log('MockWebSocket send:', data);
  }
  
  close(): void {
    this.readyState = 3; // CLOSED
    this.onclose?.();
  }
  
  // Helper method to simulate receiving a message
  simulateMessage(data: any): void {
    if (this.onmessage) {
      const event = new MessageEvent('message', { data: JSON.stringify(data) });
      this.onmessage(event);
    }
  }
}

// Custom command to mock WebSocket
Cypress.Commands.add('mockWebSocket', () => {
  cy.window().then((win) => {
    // Store the original WebSocket constructor
    const OriginalWebSocket = win.WebSocket;
    
    // Create a mock WebSocket instance
    let mockWs: MockWebSocket | null = null;
    
    // Override the WebSocket constructor
    (win as any).WebSocket = class extends MockWebSocket {
      constructor(url: string) {
        super(url);
        mockWs = this;
        // Expose it on window for test access
        (win as any).mockWs = this;
        return this;
      }
    };
    
    // Restore original WebSocket on test cleanup
    cy.on('test:after:run', () => {
      (win as any).WebSocket = OriginalWebSocket;
      delete (win as any).mockWs;
    });
  });
});

// Custom command to send WebSocket message
Cypress.Commands.add('sendWebSocketMessage', (message: any) => {
  cy.window().then((win) => {
    const mockWs = (win as any).mockWs;
    if (mockWs && mockWs.simulateMessage) {
      mockWs.simulateMessage(message);
    }
  });
});

// Legacy support for tests using window.ws
Cypress.Commands.add('mockLegacyWebSocket', () => {
  cy.window().then((win) => {
    (win as any).ws = {
      onmessage: null,
      send: cy.stub().as('wsSend'),
      close: cy.stub().as('wsClose'),
      readyState: 1, // OPEN
    };
  });
});

import { performUILogin, setupAuthenticatedState } from './auth-helpers';

// Custom login command for authentication in tests
// Uses unified auth helpers for consistency
Cypress.Commands.add('login', (email?: string, password?: string) => {
  // For most tests, use the faster mock authentication
  // For integration tests that need real login, use performUILogin
  if (Cypress.env('USE_REAL_LOGIN')) {
    performUILogin(email, password);
  } else {
    // Default to faster mock authentication for most tests
    setupAuthenticatedState({ email: email || 'dev@example.com' });
    cy.visit('/chat');
  }
});

declare global {
  namespace Cypress {
    interface Chainable {
      mockWebSocket(): Chainable<void>
      sendWebSocketMessage(message: any): Chainable<void>
      mockLegacyWebSocket(): Chainable<void>
      login(email?: string, password?: string): Chainable<void>
    }
  }
}