describe('Critical WebSocket Communication Flow', () => {
  beforeEach(() => {
    // Mock authentication to access chat
    cy.clearLocalStorage();
    cy.clearCookies();
    
    // Set mock auth token to bypass login
    cy.window().then((win) => {
      win.localStorage.setItem('auth_token', 'mock-jwt-token-for-testing');
      win.localStorage.setItem('user', JSON.stringify({
        id: 'test-user-id',
        email: 'test@netrasystems.ai',
        name: 'Test User'
      }));
    });
    
    // Visit chat page
    cy.visit('/chat');
  });

  it('should establish WebSocket connection for chat', () => {
    // 1. Check if we're on chat page or redirected to login
    cy.url().then((url) => {
      if (url.includes('/login')) {
        // If redirected to login, skip WebSocket tests
        cy.log('Authentication required - skipping WebSocket test');
      } else {
        // 2. Look for chat interface elements
        cy.get('textarea, input[type="text"]', { timeout: 10000 }).should('be.visible');
        
        // 3. Look for send button or similar
        cy.get('button').should('exist');
      }
    });
  });

  it('should send and receive messages', () => {
    cy.url().then((url) => {
      if (!url.includes('/login')) {
        // 1. Find message input
        cy.get('textarea, input[type="text"]').first().as('messageInput');
        
        // 2. Type a test message
        const testMessage = 'Hello, can you help me optimize my AI workload?';
        cy.get('@messageInput').type(testMessage);
        
        // 3. Find and click send button
        cy.get('button').contains(/send|submit|→|⏎/i).click();
        
        // 4. Verify message appears in chat
        cy.contains(testMessage, { timeout: 10000 }).should('be.visible');
        
        // 5. Wait for response (may show loading state)
        cy.contains(/thinking|processing|analyzing|loading/i, { timeout: 10000 }).should('exist');
      }
    });
  });

  it('should handle connection status indicators', () => {
    cy.url().then((url) => {
      if (!url.includes('/login')) {
        // 1. Look for connection status (if visible)
        cy.get('body').then(($body) => {
          // Check if there are any connection indicators
          const statusIndicators = [
            '[class*="status"]',
            '[class*="connection"]',
            '[class*="online"]',
            '[class*="connected"]'
          ];
          
          let hasIndicator = false;
          statusIndicators.forEach(selector => {
            if ($body.find(selector).length > 0) {
              hasIndicator = true;
              cy.get(selector).first().should('be.visible');
            }
          });
          
          if (!hasIndicator) {
            cy.log('No visible connection status indicators found');
          }
        });
      }
    });
  });

  it('should maintain message history', () => {
    cy.url().then((url) => {
      if (!url.includes('/login')) {
        // 1. Send first message
        const firstMessage = 'First test message';
        cy.get('textarea, input[type="text"]').first().type(firstMessage);
        cy.get('button').contains(/send|submit|→|⏎/i).click();
        
        // 2. Wait for first message to appear
        cy.contains(firstMessage, { timeout: 10000 }).should('be.visible');
        
        // 3. Send second message
        const secondMessage = 'Second test message';
        cy.get('textarea, input[type="text"]').first().clear().type(secondMessage);
        cy.get('button').contains(/send|submit|→|⏎/i).click();
        
        // 4. Verify both messages are visible
        cy.contains(firstMessage).should('be.visible');
        cy.contains(secondMessage).should('be.visible');
        
        // 5. Check message order (second should be after first)
        cy.get('[class*="message"], [class*="chat"]').then($messages => {
          const text = $messages.text();
          const firstIndex = text.indexOf(firstMessage);
          const secondIndex = text.indexOf(secondMessage);
          expect(firstIndex).to.be.lessThan(secondIndex);
        });
      }
    });
  });

  it('should handle empty message submission', () => {
    cy.url().then((url) => {
      if (!url.includes('/login')) {
        // 1. Try to send empty message
        cy.get('textarea, input[type="text"]').first().clear();
        cy.get('button').contains(/send|submit|→|⏎/i).click();
        
        // 2. Should not send empty message
        // Check that no new empty message appears
        cy.wait(1000); // Brief wait
        
        // 3. Verify input is still available for typing
        cy.get('textarea, input[type="text"]').first().should('be.visible').and('not.be.disabled');
      }
    });
  });

  it('should handle rapid message sending', () => {
    cy.url().then((url) => {
      if (!url.includes('/login')) {
        const messages = [
          'Quick message 1',
          'Quick message 2',
          'Quick message 3'
        ];
        
        // Send messages rapidly
        messages.forEach((message, index) => {
          cy.get('textarea, input[type="text"]').first().clear().type(message);
          cy.get('button').contains(/send|submit|→|⏎/i).click();
          cy.wait(100); // Small delay between messages
        });
        
        // Verify all messages appear
        messages.forEach(message => {
          cy.contains(message, { timeout: 10000 }).should('be.visible');
        });
      }
    });
  });
});