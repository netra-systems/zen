/// <reference types="cypress" />

describe('GTM Analytics Flow E2E Tests', () => {
  let gtmDataLayer: any[] = [];
  
  beforeEach(() => {
    // Reset GTM data layer
    gtmDataLayer = [];
    
    // Mock GTM and dataLayer
    cy.visit('/', {
      onBeforeLoad: (win) => {
        // Initialize dataLayer before GTM loads
        win.dataLayer = gtmDataLayer;
        
        // Mock GTM script loading
        Object.defineProperty(win, 'gtag', {
          value: cy.stub().as('gtag')
        });
        
        // Mock Google Tag Manager
        Object.defineProperty(win, 'google_tag_manager', {
          value: {
            'GTM-WKP28PNQ': {
              dataLayer: gtmDataLayer
            }
          }
        });
        
        // Spy on dataLayer.push method
        const originalPush = win.dataLayer.push;
        win.dataLayer.push = function(...args) {
          gtmDataLayer.push(...args);
          return originalPush.apply(this, args);
        };
      }
    });
    
    // Wait for app to be ready
    cy.get('[data-testid="app-container"]', { timeout: 10000 }).should('be.visible');
    
    // Verify GTM is loaded
    cy.window().should('have.property', 'dataLayer');
    cy.window().its('dataLayer').should('be.an', 'array');
  });

  describe('Authentication Analytics', () => {
    it('should track complete login flow with GTM events', () => {
      // Navigate to login page
      cy.visit('/login');
      
      // Verify initial GTM setup
      cy.window().then((win) => {
        const initEvent = win.dataLayer.find((item: any) => item.event === 'gtm.js');
        expect(initEvent).to.exist;
        expect(initEvent.environment).to.equal('development');
      });
      
      // Fill login form
      cy.get('[data-testid="email-input"]').type('test@netra.com');
      cy.get('[data-testid="password-input"]').type('testpassword');
      
      // Submit login form
      cy.get('[data-testid="login-submit-btn"]').click();
      
      // Wait for login to complete
      cy.url().should('include', '/chat');
      cy.get('[data-testid="user-menu"]').should('be.visible');
      
      // Verify login event was tracked
      cy.window().then((win) => {
        const loginEvent = win.dataLayer.find((item: any) => item.event === 'user_login');
        expect(loginEvent).to.exist;
        expect(loginEvent.event_category).to.equal('authentication');
        expect(loginEvent.auth_method).to.equal('email');
        expect(loginEvent.is_new_user).to.be.a('boolean');
        expect(loginEvent.user_tier).to.be.oneOf(['free', 'early', 'mid', 'enterprise']);
        expect(loginEvent.timestamp).to.exist;
        expect(loginEvent.page_path).to.equal('/login');
      });
    });
    
    it('should track Google OAuth login flow', () => {
      cy.visit('/login');
      
      // Mock Google OAuth flow
      cy.window().then((win) => {
        // Simulate OAuth popup completion
        win.postMessage({
          type: 'oauth_complete',
          provider: 'google',
          user: {
            id: 'google123',
            email: 'user@gmail.com',
            name: 'Google User'
          }
        }, '*');
      });
      
      // Click Google login button
      cy.get('[data-testid="google-login-btn"]').click();
      
      // Wait for OAuth completion
      cy.url().should('include', '/chat');
      
      // Verify OAuth events
      cy.window().then((win) => {
        const oauthEvent = win.dataLayer.find((item: any) => item.event === 'oauth_complete');
        expect(oauthEvent).to.exist;
        expect(oauthEvent.auth_method).to.equal('oauth');
        
        const loginEvent = win.dataLayer.find((item: any) => item.event === 'user_login');
        expect(loginEvent).to.exist;
        expect(loginEvent.auth_method).to.equal('google');
      });
    });
    
    it('should track signup flow with conversion events', () => {
      cy.visit('/signup');
      
      // Fill signup form
      cy.get('[data-testid="signup-email-input"]').type('newuser@test.com');
      cy.get('[data-testid="signup-password-input"]').type('newpassword');
      cy.get('[data-testid="signup-confirm-password-input"]').type('newpassword');
      cy.get('[data-testid="signup-name-input"]').type('New User');
      
      // Submit signup
      cy.get('[data-testid="signup-submit-btn"]').click();
      
      // Wait for signup completion
      cy.url().should('include', '/onboarding');
      
      // Verify signup and conversion events
      cy.window().then((win) => {
        const signupEvent = win.dataLayer.find((item: any) => item.event === 'user_signup');
        expect(signupEvent).to.exist;
        expect(signupEvent.is_new_user).to.equal(true);
        expect(signupEvent.user_tier).to.equal('free');
        
        const conversionEvent = win.dataLayer.find((item: any) => 
          item.event === 'trial_started' || item.event === 'conversion'
        );
        expect(conversionEvent).to.exist;
      });
    });
    
    it('should track logout flow', () => {
      // First login
      cy.login('test@netra.com', 'password');
      cy.visit('/chat');
      
      // Logout
      cy.get('[data-testid="user-menu"]').click();
      cy.get('[data-testid="logout-btn"]').click();
      
      // Verify logout event
      cy.url().should('include', '/login');
      cy.window().then((win) => {
        const logoutEvent = win.dataLayer.find((item: any) => item.event === 'user_logout');
        expect(logoutEvent).to.exist;
        expect(logoutEvent.event_category).to.equal('authentication');
      });
    });
  });

  describe('Chat and Engagement Analytics', () => {
    beforeEach(() => {
      cy.login('test@netra.com', 'password');
      cy.visit('/chat');
    });
    
    it('should track chat session start and message flow', () => {
      // Start new chat
      cy.get('[data-testid="new-chat-btn"]').click();
      
      // Verify chat started event
      cy.window().then((win) => {
        const chatStartedEvent = win.dataLayer.find((item: any) => item.event === 'chat_started');
        expect(chatStartedEvent).to.exist;
        expect(chatStartedEvent.event_category).to.equal('engagement');
        expect(chatStartedEvent.session_duration).to.be.a('number');
      });
      
      // Send a message
      const testMessage = 'Hello, can you help me with coding?';
      cy.get('[data-testid="message-input"]').type(testMessage);
      cy.get('[data-testid="send-message-btn"]').click();
      
      // Wait for message to be sent
      cy.get('[data-testid="message-list"]').should('contain', testMessage);
      
      // Verify message sent event
      cy.window().then((win) => {
        const messageSentEvent = win.dataLayer.find((item: any) => item.event === 'message_sent');
        expect(messageSentEvent).to.exist;
        expect(messageSentEvent.event_category).to.equal('engagement');
        expect(messageSentEvent.message_length).to.equal(testMessage.length);
        expect(messageSentEvent.thread_id).to.exist;
      });
      
      // Wait for agent response
      cy.get('[data-testid="thinking-indicator"]', { timeout: 30000 }).should('be.visible');
      cy.get('[data-testid="thinking-indicator"]', { timeout: 30000 }).should('not.exist');
      
      // Verify agent response event
      cy.window().then((win) => {
        const agentResponseEvent = win.dataLayer.find((item: any) => 
          item.event === 'message_sent' && item.agent_type
        );
        expect(agentResponseEvent).to.exist;
        expect(agentResponseEvent.agent_type).to.be.a('string');
      });
    });
    
    it('should track thread creation and management', () => {
      // Create new thread
      cy.get('[data-testid="new-thread-btn"]').click();
      
      // Verify thread created event
      cy.window().then((win) => {
        const threadCreatedEvent = win.dataLayer.find((item: any) => item.event === 'thread_created');
        expect(threadCreatedEvent).to.exist;
        expect(threadCreatedEvent.event_category).to.equal('engagement');
        expect(threadCreatedEvent.thread_id).to.exist;
      });
      
      // Switch between threads
      cy.get('[data-testid="thread-sidebar"]').should('be.visible');
      cy.get('[data-testid^="thread-item-"]').first().click();
      
      // Send message in different thread
      cy.get('[data-testid="message-input"]').type('Message in different thread');
      cy.get('[data-testid="send-message-btn"]').click();
      
      // Verify message is associated with correct thread
      cy.window().then((win) => {
        const recentMessages = win.dataLayer
          .filter((item: any) => item.event === 'message_sent')
          .slice(-2);
        
        // Should have different thread IDs
        expect(recentMessages).to.have.length(2);
        expect(recentMessages[0].thread_id).to.not.equal(recentMessages[1].thread_id);
      });
    });
    
    it('should track agent activation and tool usage', () => {
      cy.get('[data-testid="new-chat-btn"]').click();
      
      // Send message that triggers agent activation
      cy.get('[data-testid="message-input"]').type('Generate some Python code for data analysis');
      cy.get('[data-testid="send-message-btn"]').click();
      
      // Wait for agent to activate
      cy.get('[data-testid="agent-status-panel"]', { timeout: 10000 }).should('be.visible');
      cy.get('[data-testid="agent-status"]').should('contain', 'active');
      
      // Verify agent activation event
      cy.window().then((win) => {
        const agentActivatedEvent = win.dataLayer.find((item: any) => item.event === 'agent_activated');
        expect(agentActivatedEvent).to.exist;
        expect(agentActivatedEvent.event_category).to.equal('engagement');
        expect(agentActivatedEvent.agent_type).to.be.a('string');
        expect(agentActivatedEvent.thread_id).to.exist;
      });
      
      // Wait for tool usage if applicable
      cy.get('[data-testid="tool-indicator"]', { timeout: 15000 }).then(($toolIndicator) => {
        if ($toolIndicator.length > 0) {
          // Verify feature usage event
          cy.window().then((win) => {
            const featureUsedEvent = win.dataLayer.find((item: any) => item.event === 'feature_used');
            expect(featureUsedEvent).to.exist;
            expect(featureUsedEvent.feature_type).to.be.a('string');
          });
        }
      });
    });
    
    it('should track file upload feature usage', () => {
      cy.get('[data-testid="new-chat-btn"]').click();
      
      // Upload a file
      const fileName = 'test-data.csv';
      const fileContent = 'name,age,city\nJohn,25,NYC\nJane,30,LA';
      
      cy.get('[data-testid="file-upload-input"]').selectFile({
        contents: fileContent,
        fileName: fileName,
        mimeType: 'text/csv'
      }, { force: true });
      
      // Wait for file processing
      cy.get('[data-testid="file-upload-progress"]', { timeout: 10000 }).should('be.visible');
      cy.get('[data-testid="file-upload-success"]', { timeout: 15000 }).should('be.visible');
      
      // Verify file upload events
      cy.window().then((win) => {
        const fileUploadEvent = win.dataLayer.find((item: any) => item.event === 'feature_used');
        expect(fileUploadEvent).to.exist;
        expect(fileUploadEvent.feature_type).to.equal('file_upload');
        expect(fileUploadEvent.thread_id).to.exist;
      });
    });
  });

  describe('Conversion and Business Events', () => {
    beforeEach(() => {
      cy.login('test@netra.com', 'password');
    });
    
    it('should track demo request conversion', () => {
      cy.visit('/demo');
      
      // Fill demo request form
      cy.get('[data-testid="demo-name-input"]').type('John Doe');
      cy.get('[data-testid="demo-email-input"]').type('john@company.com');
      cy.get('[data-testid="demo-company-input"]').type('Acme Corp');
      cy.get('[data-testid="demo-use-case-textarea"]').type('We need AI optimization for our data pipeline');
      
      // Submit demo request
      cy.get('[data-testid="demo-request-btn"]').click();
      
      // Wait for submission success
      cy.get('[data-testid="demo-success-message"]').should('be.visible');
      
      // Verify demo request conversion event
      cy.window().then((win) => {
        const demoRequestEvent = win.dataLayer.find((item: any) => item.event === 'demo_requested');
        expect(demoRequestEvent).to.exist;
        expect(demoRequestEvent.event_category).to.equal('conversion');
        expect(demoRequestEvent.conversion_source).to.exist;
        expect(demoRequestEvent.event_action).to.equal('demo requested');
      });
    });
    
    it('should track plan upgrade conversion flow', () => {
      cy.visit('/pricing');
      
      // Click upgrade to premium
      cy.get('[data-testid="upgrade-premium-btn"]').click();
      
      // Fill billing information
      cy.get('[data-testid="billing-name"]').type('John Doe');
      cy.get('[data-testid="billing-email"]').type('john@test.com');
      
      // Mock payment processing
      cy.get('[data-testid="mock-payment-success"]').click();
      
      // Wait for upgrade completion
      cy.url().should('include', '/dashboard');
      cy.get('[data-testid="plan-status"]').should('contain', 'Premium');
      
      // Verify plan upgrade events
      cy.window().then((win) => {
        const planUpgradeEvent = win.dataLayer.find((item: any) => item.event === 'plan_upgraded');
        expect(planUpgradeEvent).to.exist;
        expect(planUpgradeEvent.event_category).to.equal('conversion');
        expect(planUpgradeEvent.plan_type).to.equal('premium');
        expect(planUpgradeEvent.transaction_value).to.be.a('number');
        expect(planUpgradeEvent.transaction_id).to.exist;
        
        const paymentEvent = win.dataLayer.find((item: any) => item.event === 'payment_completed');
        expect(paymentEvent).to.exist;
        expect(paymentEvent.currency).to.equal('USD');
      });
    });
    
    it('should track trial start conversion', () => {
      cy.visit('/');
      
      // Click start free trial
      cy.get('[data-testid="start-trial-btn"]').click();
      
      // Complete trial signup
      cy.get('[data-testid="trial-email-input"]').type('trial@test.com');
      cy.get('[data-testid="trial-password-input"]').type('trialpassword');
      cy.get('[data-testid="trial-submit-btn"]').click();
      
      // Wait for trial activation
      cy.url().should('include', '/onboarding');
      cy.get('[data-testid="trial-welcome"]').should('be.visible');
      
      // Verify trial start event
      cy.window().then((win) => {
        const trialStartedEvent = win.dataLayer.find((item: any) => item.event === 'trial_started');
        expect(trialStartedEvent).to.exist;
        expect(trialStartedEvent.event_category).to.equal('conversion');
        expect(trialStartedEvent.plan_type).to.equal('trial');
        expect(trialStartedEvent.conversion_source).to.exist;
      });
    });
  });

  describe('Page Navigation and User Journey', () => {
    it('should track page views across user journey', () => {
      const pagesToVisit = [
        { path: '/', title: 'Home' },
        { path: '/features', title: 'Features' },
        { path: '/pricing', title: 'Pricing' },
        { path: '/about', title: 'About' },
        { path: '/contact', title: 'Contact' }
      ];
      
      pagesToVisit.forEach((page, index) => {
        cy.visit(page.path);
        cy.title().should('contain', page.title);
        
        // Verify page view event
        cy.window().then((win) => {
          const pageViewEvents = win.dataLayer.filter((item: any) => item.event === 'page_view');
          expect(pageViewEvents).to.have.length.at.least(index + 1);
          
          const lastPageView = pageViewEvents[pageViewEvents.length - 1];
          expect(lastPageView.page_path).to.equal(page.path);
          expect(lastPageView.event_category).to.equal('navigation');
        });
      });
    });
    
    it('should track user interactions and button clicks', () => {
      cy.visit('/');
      
      // Track various button interactions
      const interactions = [
        { testId: 'hero-cta-btn', label: 'hero_cta' },
        { testId: 'features-learn-more-btn', label: 'features_learn_more' },
        { testId: 'pricing-view-btn', label: 'pricing_view' }
      ];
      
      interactions.forEach((interaction) => {
        cy.get(`[data-testid="${interaction.testId}"]`).click();
        
        // Verify user action event
        cy.window().then((win) => {
          const userActionEvent = win.dataLayer.find((item: any) => 
            item.event === 'user_action' && item.event_label === interaction.label
          );
          expect(userActionEvent).to.exist;
          expect(userActionEvent.event_category).to.equal('interaction');
          expect(userActionEvent.event_action).to.equal('click');
        });
        
        // Go back to continue testing
        cy.go('back');
      });
    });
  });

  describe('Error Handling and Edge Cases', () => {
    it('should handle GTM loading failures gracefully', () => {
      // Visit page with GTM disabled
      cy.visit('/', {
        onBeforeLoad: (win) => {
          // Don't initialize GTM
          win.dataLayer = [];
          // Simulate GTM script failure
          Object.defineProperty(win, 'google_tag_manager', {
            value: undefined
          });
        }
      });
      
      // App should still function
      cy.get('[data-testid="app-container"]').should('be.visible');
      
      // Login should still work
      cy.visit('/login');
      cy.get('[data-testid="email-input"]').type('test@netra.com');
      cy.get('[data-testid="password-input"]').type('password');
      cy.get('[data-testid="login-submit-btn"]').click();
      
      // Should redirect successfully even without GTM
      cy.url().should('include', '/chat');
    });
    
    it('should handle rapid event generation without breaking', () => {
      cy.login('test@netra.com', 'password');
      cy.visit('/chat');
      
      // Generate many events rapidly
      for (let i = 0; i < 10; i++) {
        cy.get('[data-testid="new-chat-btn"]').click();
        cy.get('[data-testid="message-input"]').type(`Message ${i}`);
        cy.get('[data-testid="send-message-btn"]').click();
        cy.wait(100); // Small delay to prevent overwhelming
      }
      
      // Verify events were tracked
      cy.window().then((win) => {
        const messageEvents = win.dataLayer.filter((item: any) => item.event === 'message_sent');
        expect(messageEvents.length).to.be.at.least(10);
        
        // All events should have proper structure
        messageEvents.forEach((event: any) => {
          expect(event.timestamp).to.exist;
          expect(event.event_category).to.equal('engagement');
        });
      });
    });
    
    it('should handle network interruptions during tracking', () => {
      cy.login('test@netra.com', 'password');
      cy.visit('/chat');
      
      // Intercept and fail some requests
      cy.intercept('POST', '**/api/**', { forceNetworkError: true }).as('networkError');
      
      // Perform actions that would normally trigger API calls
      cy.get('[data-testid="new-chat-btn"]').click();
      cy.get('[data-testid="message-input"]').type('This message might fail to send');
      cy.get('[data-testid="send-message-btn"]').click();
      
      // GTM events should still be tracked locally
      cy.window().then((win) => {
        const messageSentEvent = win.dataLayer.find((item: any) => item.event === 'message_sent');
        expect(messageSentEvent).to.exist;
        
        // Error event might also be tracked
        const errorEvents = win.dataLayer.filter((item: any) => 
          item.event.includes('error') || item.event_category === 'error'
        );
        expect(errorEvents.length).to.be.at.least(0); // May or may not have error events
      });
    });
  });

  describe('Cross-browser Compatibility', () => {
    // These tests would run in different browsers via Cypress configuration
    it('should track events consistently across browsers', () => {
      cy.visit('/');
      
      // Verify GTM works in current browser
      cy.window().should('have.property', 'dataLayer');
      
      // Perform standard flow
      cy.get('[data-testid="start-trial-btn"]').click();
      cy.get('[data-testid="trial-email-input"]').type('browser-test@test.com');
      
      // Verify events are tracked regardless of browser
      cy.window().then((win) => {
        const events = win.dataLayer.filter((item: any) => item.event);
        expect(events.length).to.be.at.least(1);
        
        // All events should have proper timestamps and structure
        events.forEach((event: any) => {
          if (event.event !== 'gtm.js') {
            expect(event.timestamp).to.exist;
            expect(event.page_path).to.be.a('string');
          }
        });
      });
    });
  });

  describe('Performance Impact', () => {
    it('should not significantly impact page load performance', () => {
      // Measure performance with GTM
      cy.visit('/', {
        onBeforeLoad: (win) => {
          win.performance.mark('navigation-start');
        }
      });
      
      cy.window().then((win) => {
        win.performance.mark('app-ready');
        const measure = win.performance.measure('load-time', 'navigation-start', 'app-ready');
        
        // Page should load within reasonable time even with GTM
        expect(measure.duration).to.be.lessThan(5000); // 5 seconds max
      });
      
      // Verify GTM is loaded without blocking
      cy.window().should('have.property', 'dataLayer');
      cy.get('[data-testid="app-container"]').should('be.visible');
    });
    
    it('should handle large dataLayer without memory issues', () => {
      cy.visit('/');
      
      // Simulate large number of events
      cy.window().then((win) => {
        // Add many events to simulate heavy usage
        for (let i = 0; i < 1000; i++) {
          win.dataLayer.push({
            event: 'test_event',
            index: i,
            timestamp: new Date().toISOString(),
            data: `test_data_${i}`
          });
        }
        
        // Verify dataLayer can handle large datasets
        expect(win.dataLayer.length).to.be.at.least(1000);
        
        // App should remain responsive
        cy.get('[data-testid="app-container"]').should('be.visible');
        cy.get('body').should('be.visible');
      });
    });
  });

  afterEach(() => {
    // Clean up any test data or states
    cy.window().then((win) => {
      if (win.dataLayer) {
        win.dataLayer.length = 0;
      }
    });
  });
});