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

// Custom login command for authentication in tests
Cypress.Commands.add('login', (email?: string, password?: string) => {
  const testEmail = email || Cypress.env('CYPRESS_TEST_USER') || 'dev@example.com';
  const testPassword = password || Cypress.env('CYPRESS_TEST_PASSWORD') || 'dev';
  
  // Visit login page
  cy.visit('/login');
  
  // Wait for page to load
  cy.get('body', { timeout: 10000 }).should('be.visible');
  
  // Check if already logged in by checking URL
  cy.url().then((url) => {
    if (url.includes('/chat')) {
      // Already logged in, no need to do anything
      cy.log('Already authenticated, skipping login');
      return;
    }
    
    // Check if we're in development mode by looking for auth config
    cy.request({
      url: 'http://localhost:8081/auth/config',
      failOnStatusCode: false,
      timeout: 3000
    }).then((response) => {
      if (response.status === 200 && response.body?.development_mode) {
        // Development mode login - just click Quick Dev Login
        cy.contains('button', 'Quick Dev Login', { timeout: 10000 })
          .should('be.visible')
          .should('not.be.disabled')
          .click();
        
        // Wait for successful login
        cy.url({ timeout: 15000 }).should('not.include', '/login');
        
        // Verify JWT token is stored
        cy.window().then((win) => {
          expect(win.localStorage.getItem('jwt_token')).to.be.a('string').and.not.be.empty;
        });
      } else {
      // Production/OAuth mode - skip actual login for these tests
      cy.log('OAuth mode detected - mocking authentication for security tests');
      
      // Mock a valid JWT token in localStorage for testing purposes
      // This creates a token that expires in the far future for testing stability
      const futureTimestamp = Math.floor(Date.now() / 1000) + (24 * 60 * 60); // 24 hours from now
      const mockPayload = btoa(JSON.stringify({
        sub: 'test-user-id',
        email: 'test@example.com',
        full_name: 'Test User',
        role: 'user',
        iat: Math.floor(Date.now() / 1000),
        exp: futureTimestamp
      }));
      const mockToken = `eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.${mockPayload}.mock-signature-for-testing`;
      cy.window().then((win) => {
        win.localStorage.setItem('jwt_token', mockToken);
      });
      
        // Navigate away from login page
        cy.visit('/chat');
      }
    });
  });
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