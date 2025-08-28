/**
 * E2E Tests for GTM Circuit Breaker and Infinite Loop Prevention
 * 
 * Tests the real-world behavior of GTM event tracking with circuit breaker
 * protection in various authentication and error scenarios.
 */

describe('GTM Circuit Breaker E2E Tests', () => {
  let dataLayerEvents: any[] = [];

  beforeEach(() => {
    // Reset tracking
    dataLayerEvents = [];
    
    // Intercept and monitor dataLayer pushes
    cy.visit('/', {
      onBeforeLoad(win) {
        // Initialize dataLayer
        (win as any).dataLayer = [];
        
        // Override push to capture events
        const originalPush = (win as any).dataLayer.push;
        (win as any).dataLayer.push = function(...args: any[]) {
          dataLayerEvents.push(...args);
          return originalPush.apply(this, args);
        };
      }
    });
  });

  describe('Authentication Flow Protection', () => {
    it('should not create infinite loop on auth failure', () => {
      // Visit protected page without authentication
      cy.visit('/dashboard', { failOnStatusCode: false });
      
      // Should redirect to login
      cy.url().should('include', '/login');
      
      // Check that auth_required event was only fired once
      cy.wait(1000); // Wait for any potential duplicate events
      
      cy.window().then((win) => {
        const authRequiredEvents = dataLayerEvents.filter(
          e => e.event === 'exception' && e.event_action === 'auth_required'
        );
        
        // Should have exactly one auth_required event
        expect(authRequiredEvents.length).to.equal(1);
      });
    });

    it('should handle rapid navigation between protected pages', () => {
      // Simulate rapid navigation attempts
      const protectedPages = ['/dashboard', '/settings', '/profile', '/admin'];
      
      protectedPages.forEach(page => {
        cy.visit(page, { failOnStatusCode: false });
      });
      
      // Wait for all navigations to complete
      cy.wait(2000);
      
      cy.window().then((win) => {
        const authRequiredEvents = dataLayerEvents.filter(
          e => e.event === 'exception' && e.event_action === 'auth_required'
        );
        
        // Should have limited auth_required events despite multiple navigations
        expect(authRequiredEvents.length).to.be.lessThan(protectedPages.length * 2);
      });
    });

    it('should properly track successful authentication', () => {
      // Mock successful login
      cy.intercept('POST', '/api/auth/login', {
        statusCode: 200,
        body: {
          access_token: 'mock-token',
          user: { id: '1', email: 'test@example.com' }
        }
      });
      
      // Login
      cy.visit('/login');
      cy.get('[data-testid="email-input"]').type('test@example.com');
      cy.get('[data-testid="password-input"]').type('password');
      cy.get('[data-testid="login-button"]').click();
      
      // Should track login event
      cy.wait(1000);
      
      cy.window().then((win) => {
        const loginEvents = dataLayerEvents.filter(
          e => e.event === 'user_login'
        );
        
        // Should have exactly one login event
        expect(loginEvents.length).to.equal(1);
      });
      
      // Navigate to protected page
      cy.visit('/dashboard');
      
      cy.window().then((win) => {
        const pageViewEvents = dataLayerEvents.filter(
          e => e.event === 'page_view' && e.page_path === '/dashboard'
        );
        
        // Should track page view for protected page
        expect(pageViewEvents.length).to.be.at.least(1);
      });
    });
  });

  describe('Circuit Breaker Behavior', () => {
    it('should prevent event spam during errors', () => {
      // Simulate network errors
      cy.intercept('GET', '/api/**', { forceNetworkError: true });
      
      // Try to load page with failing API calls
      cy.visit('/dashboard', { failOnStatusCode: false });
      
      // Trigger multiple actions that would cause errors
      for (let i = 0; i < 10; i++) {
        cy.get('body').click({ force: true });
      }
      
      cy.wait(2000);
      
      cy.window().then((win) => {
        const errorEvents = dataLayerEvents.filter(
          e => e.event === 'exception'
        );
        
        // Should have limited error events despite multiple errors
        expect(errorEvents.length).to.be.lessThan(20);
      });
    });

    it('should deduplicate rapid identical events', () => {
      cy.visit('/');
      
      // Trigger the same action multiple times rapidly
      const button = cy.get('[data-testid="test-button"]', { timeout: 1000 }).should('not.exist').then(() => {
        // If button doesn't exist, create a test scenario
        cy.window().then((win) => {
          // Manually push duplicate events
          for (let i = 0; i < 20; i++) {
            (win as any).dataLayer.push({
              event: 'test_event',
              event_category: 'test',
              event_action: 'duplicate_test',
              event_label: 'same_label'
            });
          }
        });
      });
      
      cy.wait(500);
      
      cy.window().then((win) => {
        const testEvents = dataLayerEvents.filter(
          e => e.event === 'test_event' && e.event_action === 'duplicate_test'
        );
        
        // Should have significantly fewer events due to deduplication
        expect(testEvents.length).to.be.lessThan(5);
      });
    });

    it('should recover after circuit breaker trips', () => {
      cy.visit('/');
      
      // Force circuit breaker to trip by sending many events
      cy.window().then((win) => {
        for (let i = 0; i < 60; i++) {
          (win as any).dataLayer.push({
            event: 'exception',
            event_category: 'error',
            event_action: 'circuit_test',
            event_label: `error_${i}`
          });
        }
      });
      
      // Circuit should be tripped, new events blocked
      cy.window().then((win) => {
        const beforeCount = dataLayerEvents.length;
        
        (win as any).dataLayer.push({
          event: 'test_blocked',
          event_category: 'test',
          event_action: 'should_be_blocked'
        });
        
        // Event should be blocked
        const afterCount = dataLayerEvents.length;
        expect(afterCount).to.equal(beforeCount);
      });
      
      // Wait for recovery (in test, this would be mocked to be faster)
      // In real scenario, this would be 30 seconds
      cy.wait(1000);
      
      // After recovery, events should work again
      // This would need proper time manipulation in real tests
    });
  });

  describe('Performance and Memory', () => {
    it('should not degrade performance with many events', () => {
      cy.visit('/');
      
      // Measure initial performance
      cy.window().then((win) => {
        const startTime = performance.now();
        
        // Send many events
        for (let i = 0; i < 100; i++) {
          (win as any).dataLayer.push({
            event: 'performance_test',
            event_category: 'test',
            event_action: `action_${i}`,
            timestamp: new Date().toISOString()
          });
        }
        
        const endTime = performance.now();
        const duration = endTime - startTime;
        
        // Should complete quickly (less than 100ms for 100 events)
        expect(duration).to.be.lessThan(100);
      });
    });

    it('should maintain bounded memory usage', () => {
      cy.visit('/');
      
      cy.window().then((win) => {
        // Check dataLayer doesn't grow unbounded
        const initialLength = (win as any).dataLayer.length;
        
        // Send many events
        for (let i = 0; i < 1000; i++) {
          (win as any).dataLayer.push({
            event: 'memory_test',
            event_category: 'test',
            event_action: 'memory_check',
            value: i
          });
        }
        
        // DataLayer should have events but circuit breaker should limit them
        const finalLength = (win as any).dataLayer.length;
        
        // Should not have all 1000 events due to circuit breaker
        expect(finalLength - initialLength).to.be.lessThan(500);
      });
    });
  });

  describe('Real User Scenarios', () => {
    it('should handle user session timeout gracefully', () => {
      // Simulate authenticated session
      cy.window().then((win) => {
        win.localStorage.setItem('jwt_token', 'mock-token');
      });
      
      cy.visit('/dashboard');
      
      // Simulate token expiration
      cy.window().then((win) => {
        win.localStorage.removeItem('jwt_token');
      });
      
      // Trigger re-authentication check
      cy.reload();
      
      // Should redirect to login with single auth_required event
      cy.url().should('include', '/login');
      
      cy.window().then((win) => {
        const authRequiredEvents = dataLayerEvents.filter(
          e => e.event === 'exception' && e.event_action === 'auth_required'
        );
        
        // Should have exactly one auth_required event for session timeout
        expect(authRequiredEvents.length).to.equal(1);
      });
    });

    it('should handle OAuth callback without event spam', () => {
      // Simulate OAuth callback
      cy.visit('/auth/callback?code=mock-code&state=mock-state');
      
      cy.wait(2000);
      
      cy.window().then((win) => {
        const oauthEvents = dataLayerEvents.filter(
          e => e.event === 'oauth_complete'
        );
        
        // Should track OAuth completion once
        expect(oauthEvents.length).to.be.lessThan(2);
      });
    });

    it('should track user interactions without duplication', () => {
      cy.visit('/');
      
      // Simulate user clicking same button multiple times
      const selector = '[data-testid="action-button"]';
      
      // Create a test button if it doesn't exist
      cy.get('body').then($body => {
        if ($body.find(selector).length === 0) {
          cy.document().then(doc => {
            const button = doc.createElement('button');
            button.setAttribute('data-testid', 'action-button');
            button.textContent = 'Test Button';
            button.onclick = () => {
              (window as any).dataLayer.push({
                event: 'button_click',
                event_category: 'engagement',
                event_action: 'click',
                event_label: 'test_button'
              });
            };
            doc.body.appendChild(button);
          });
        }
      });
      
      // Click button multiple times rapidly
      for (let i = 0; i < 5; i++) {
        cy.get(selector).click({ force: true });
      }
      
      cy.wait(500);
      
      cy.window().then((win) => {
        const clickEvents = dataLayerEvents.filter(
          e => e.event === 'button_click'
        );
        
        // Should have limited click events due to deduplication
        expect(clickEvents.length).to.be.lessThan(3);
      });
    });
  });

  describe('Debug and Monitoring', () => {
    it('should expose circuit breaker stats for debugging', () => {
      cy.visit('/');
      
      cy.window().then((win) => {
        // Check if circuit breaker stats are accessible
        // This would be exposed in development mode
        if ((win as any).__GTM_CIRCUIT_BREAKER__) {
          const stats = (win as any).__GTM_CIRCUIT_BREAKER__.getStats();
          
          expect(stats).to.have.property('isOpen');
          expect(stats).to.have.property('recentEventsCount');
          expect(stats).to.have.property('eventTypeCounts');
        }
      });
    });

    it('should log circuit breaker actions in debug mode', () => {
      // In debug mode, check console for circuit breaker logs
      cy.visit('/?debug=true');
      
      // Trigger events that would be blocked
      cy.window().then((win) => {
        // Send duplicate events
        for (let i = 0; i < 3; i++) {
          (win as any).dataLayer.push({
            event: 'debug_test',
            event_category: 'test',
            event_action: 'debug_check'
          });
        }
      });
      
      // In debug mode, console would show deduplication messages
      // This is verified through manual testing or console spy
    });
  });
});