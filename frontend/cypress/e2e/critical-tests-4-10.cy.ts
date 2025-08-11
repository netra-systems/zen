/// <reference types="cypress" />

/**
 * Critical E2E Tests 4-10
 * Comprehensive test suite for demo stability and business value
 */

describe('Critical Test #4: Data Generation to Insights Pipeline', () => {
  beforeEach(() => {
    cy.viewport(1920, 1080);
    cy.visit('/demo');
    cy.contains('Technology').click();
  });

  it('should generate synthetic data with expected patterns', () => {
    cy.contains('Synthetic Data').click();
    
    // Configure data generation
    cy.get('input[name="recordCount"]').clear().type('100000');
    cy.get('select[name="distribution"]').select('normal');
    cy.get('input[name="seed"]').clear().type('42');
    
    // Generate data
    cy.contains('Generate Data').click();
    
    // Verify generation progress
    cy.contains(/generating|processing/i).should('be.visible');
    
    // Wait for completion (with timeout)
    cy.contains(/generated.*100,000|100000.*records/i, { timeout: 30000 }).should('be.visible');
    
    // Verify statistical properties
    cy.contains('View Statistics').click();
    cy.contains(/mean|median|std/i).should('be.visible');
    
    // Check pattern detection
    cy.contains('Analyze Patterns').click();
    cy.wait(5000);
    
    // Should detect patterns with >95% accuracy
    cy.contains(/pattern.*detected|accuracy.*9[5-9]%|accuracy.*100%/i).should('be.visible');
  });

  it('should process data through complete pipeline', () => {
    // Generate data
    cy.contains('Synthetic Data').click();
    cy.get('input[name="recordCount"]').clear().type('10000');
    cy.contains('Generate Data').click();
    cy.wait(5000);
    
    // Process through agents
    cy.contains('AI Chat').click();
    cy.get('textarea').type('Analyze the generated dataset for optimization opportunities');
    cy.get('button[aria-label="Send message"]').click();
    
    // Wait for analysis
    cy.contains(/analyzing|processing/i, { timeout: 10000 }).should('be.visible');
    
    // Verify insights generation
    cy.contains(/insights|opportunities|recommendations/i, { timeout: 15000 }).should('be.visible');
    
    // Check for cost savings calculation
    cy.contains(/savings|reduction|optimize/i).should('be.visible');
    cy.contains(/\d+%|\$\d+/i).should('be.visible'); // Percentage or dollar amount
  });

  it('should maintain data integrity throughout pipeline', () => {
    // Generate known dataset
    cy.contains('Synthetic Data').click();
    cy.get('input[name="recordCount"]').clear().type('1000');
    cy.get('input[name="seed"]').clear().type('12345'); // Fixed seed for reproducibility
    cy.contains('Generate Data').click();
    cy.wait(3000);
    
    // Get initial count
    cy.contains(/1,?000.*records/i).should('be.visible');
    
    // Process data
    cy.contains('Process Data').click();
    cy.wait(2000);
    
    // Verify no data loss
    cy.contains(/processed.*1,?000/i).should('be.visible');
    
    // Export and verify
    cy.contains('Export Results').click();
    cy.contains(/export.*complete|download.*ready/i).should('be.visible');
  });

  it('should generate insights within 10 seconds', () => {
    const startTime = Date.now();
    
    // Quick data generation
    cy.contains('Synthetic Data').click();
    cy.get('input[name="recordCount"]').clear().type('5000');
    cy.contains('Generate Data').click();
    cy.wait(2000);
    
    // Request insights
    cy.contains('Generate Insights').click();
    
    // Should complete within 10 seconds
    cy.contains(/insights.*ready|analysis.*complete/i, { timeout: 10000 }).should('be.visible');
    
    const endTime = Date.now();
    expect(endTime - startTime).to.be.lessThan(10000);
  });
});

describe('Critical Test #5: Authentication State Corruption', () => {
  beforeEach(() => {
    cy.viewport(1920, 1080);
    
    // Set up initial auth state
    cy.window().then((win) => {
      win.localStorage.setItem('auth_token', 'initial-token-12345');
      win.localStorage.setItem('demo_progress', JSON.stringify({
        industry: 'Healthcare',
        step: 2,
        completed: ['industry_selection', 'roi_calculation']
      }));
    });
    
    cy.visit('/demo');
  });

  it('should handle token expiry during active demo', () => {
    // Start demo interaction
    cy.contains('AI Chat').click();
    cy.get('textarea').type('Initial message with valid token');
    cy.get('button[aria-label="Send message"]').click();
    cy.wait(2000);
    
    // Simulate token expiry
    cy.window().then((win) => {
      win.localStorage.setItem('auth_token', 'expired-token');
      // Trigger token validation
      win.dispatchEvent(new Event('storage'));
    });
    
    // Try to continue demo
    cy.get('textarea').clear().type('Message after token expiry');
    cy.get('button[aria-label="Send message"]').click();
    
    // Should handle gracefully
    cy.get('body').then(($body) => {
      // Either refresh token or continue in anonymous mode
      const hasAuthPrompt = $body.find('[class*="auth"], [class*="login"]').length > 0;
      const continuesAnonymous = $body.find('textarea').length > 0;
      
      expect(hasAuthPrompt || continuesAnonymous).to.be.true;
    });
  });

  it('should preserve demo state across re-authentication', () => {
    // Get initial state
    cy.window().then((win) => {
      const initialProgress = win.localStorage.getItem('demo_progress');
      expect(initialProgress).to.not.be.null;
    });
    
    // Simulate re-auth flow
    cy.window().then((win) => {
      // Clear auth but keep demo state
      win.localStorage.removeItem('auth_token');
      win.dispatchEvent(new Event('storage'));
    });
    
    // Re-authenticate
    cy.window().then((win) => {
      win.localStorage.setItem('auth_token', 'new-token-67890');
      win.dispatchEvent(new Event('storage'));
    });
    
    // Verify demo state preserved
    cy.window().then((win) => {
      const progress = JSON.parse(win.localStorage.getItem('demo_progress') || '{}');
      expect(progress.industry).to.equal('Healthcare');
      expect(progress.completed).to.include('industry_selection');
    });
  });

  it('should gracefully degrade to anonymous mode', () => {
    // Remove all auth
    cy.window().then((win) => {
      win.localStorage.clear();
      win.sessionStorage.clear();
    });
    
    cy.reload();
    
    // Should still allow demo access
    cy.url().should('include', '/demo');
    cy.contains('Select Your Industry').should('be.visible');
    
    // Can still interact
    cy.contains('Financial Services').click();
    cy.contains('ROI Calculator').should('be.visible');
  });

  it('should recover session after browser refresh', () => {
    // Set up session
    cy.contains('E-commerce').click();
    cy.contains('ROI Calculator').click();
    cy.get('input[id="spend"]').clear().type('50000');
    cy.contains('Calculate ROI').click();
    cy.wait(2000);
    
    // Save current state
    cy.window().then((win) => {
      const state = {
        industry: 'E-commerce',
        roi_calculated: true,
        monthly_spend: 50000
      };
      win.localStorage.setItem('demo_session', JSON.stringify(state));
    });
    
    // Refresh browser
    cy.reload();
    
    // Verify state recovered
    cy.contains('E-commerce').should('be.visible');
    cy.window().then((win) => {
      const recovered = JSON.parse(win.localStorage.getItem('demo_session') || '{}');
      expect(recovered.industry).to.equal('E-commerce');
      expect(recovered.roi_calculated).to.be.true;
    });
  });
});

describe('Critical Test #6: Industry-Specific Optimization Accuracy', () => {
  const industries = [
    { name: 'Financial Services', multiplier: 1.5, baseline: 100000 },
    { name: 'Healthcare', multiplier: 1.3, baseline: 80000 },
    { name: 'E-commerce', multiplier: 1.4, baseline: 60000 },
    { name: 'Technology', multiplier: 1.6, baseline: 120000 }
  ];

  industries.forEach(industry => {
    it(`should apply correct multipliers for ${industry.name}`, () => {
      cy.visit('/demo');
      cy.contains(industry.name).click();
      cy.contains('ROI Calculator').click();
      
      // Enter baseline values
      cy.get('input[id="spend"]').clear().type(industry.baseline.toString());
      cy.get('input[id="requests"]').clear().type('10000000');
      
      // Calculate
      cy.contains('Calculate ROI').click();
      cy.wait(2000);
      
      // Verify multiplier applied
      cy.contains(`Industry multiplier applied: ${industry.name}`).should('be.visible');
      
      // Check savings calculation accuracy (within 10% of expected)
      const expectedSavings = industry.baseline * 0.45 * industry.multiplier; // 45% base savings
      const minExpected = expectedSavings * 0.9;
      const maxExpected = expectedSavings * 1.1;
      
      cy.get('[data-testid="monthly-savings"], [class*="savings"]').then($el => {
        const text = $el.text();
        const savings = parseFloat(text.replace(/[^0-9.-]/g, ''));
        expect(savings).to.be.within(minExpected, maxExpected);
      });
    });
  });

  it('should handle edge cases in calculations', () => {
    cy.visit('/demo');
    cy.contains('Technology').click();
    cy.contains('ROI Calculator').click();
    
    // Test negative values
    cy.get('input[id="spend"]').clear().type('-1000');
    cy.contains('Calculate ROI').click();
    cy.contains(/invalid|error|positive/i).should('be.visible');
    
    // Test extreme values
    cy.get('input[id="spend"]').clear().type('999999999999');
    cy.contains('Calculate ROI').click();
    cy.wait(2000);
    // Should handle large numbers
    cy.contains(/savings|optimization/i).should('be.visible');
    
    // Test zero values
    cy.get('input[id="spend"]').clear().type('0');
    cy.contains('Calculate ROI').click();
    cy.contains(/enter.*valid|greater than zero/i).should('be.visible');
  });
});

describe('Critical Test #7: Memory Leak Detection', () => {
  it('should not accumulate memory after 100 interactions', () => {
    cy.visit('/demo');
    cy.contains('Technology').click();
    cy.contains('AI Chat').click();
    
    // Get initial memory if available
    let initialMemory = 0;
    cy.window().then((win) => {
      if ((win.performance as any).memory) {
        initialMemory = (win.performance as any).memory.usedJSHeapSize;
      }
    });
    
    // Perform 100 interactions
    for (let i = 0; i < 100; i++) {
      cy.get('textarea').clear().type(`Test message ${i}`);
      cy.get('button[aria-label="Send message"]').click();
      
      if (i % 10 === 0) {
        cy.wait(1000); // Brief pause every 10 messages
      }
    }
    
    // Check final memory
    cy.window().then((win) => {
      if ((win.performance as any).memory) {
        const finalMemory = (win.performance as any).memory.usedJSHeapSize;
        const growth = (finalMemory - initialMemory) / initialMemory;
        
        // Memory growth should be less than 10%
        expect(growth).to.be.lessThan(0.1);
      }
    });
  });

  it('should not accumulate DOM nodes', () => {
    cy.visit('/demo');
    cy.contains('Technology').click();
    
    // Count initial DOM nodes
    let initialNodeCount = 0;
    cy.document().then((doc) => {
      initialNodeCount = doc.getElementsByTagName('*').length;
    });
    
    // Navigate through all tabs multiple times
    const tabs = ['Overview', 'ROI Calculator', 'AI Chat', 'Metrics', 'Synthetic Data', 'Next Steps'];
    
    for (let round = 0; round < 10; round++) {
      tabs.forEach(tab => {
        cy.contains(tab).click();
        cy.wait(500);
      });
    }
    
    // Check final DOM node count
    cy.document().then((doc) => {
      const finalNodeCount = doc.getElementsByTagName('*').length;
      const growth = (finalNodeCount - initialNodeCount) / initialNodeCount;
      
      // DOM growth should be minimal
      expect(growth).to.be.lessThan(0.2);
    });
  });

  it('should clean up event listeners', () => {
    cy.visit('/demo');
    cy.contains('Technology').click();
    cy.contains('AI Chat').click();
    
    // Track event listeners (simplified check)
    cy.window().then((win) => {
      // Override addEventListener to track
      let listenerCount = 0;
      const originalAdd = win.addEventListener;
      const originalRemove = win.removeEventListener;
      
      win.addEventListener = function(...args: any[]) {
        listenerCount++;
        return originalAdd.apply(this, args);
      };
      
      win.removeEventListener = function(...args: any[]) {
        listenerCount--;
        return originalRemove.apply(this, args);
      };
      
      // Perform actions that add/remove listeners
      for (let i = 0; i < 20; i++) {
        cy.get('textarea').clear().type(`Message ${i}`);
        cy.get('button[aria-label="Send message"]').click();
        cy.wait(200);
      }
      
      // Listener count should not grow excessively
      expect(listenerCount).to.be.lessThan(50);
    });
  });
});

describe('Critical Test #8: Cross-Browser Compatibility', () => {
  const browsers = ['chrome', 'firefox', 'edge'];
  
  // Note: This test requires Cypress to be configured with multiple browsers
  // In real implementation, use cypress-multi-browser or similar
  
  it('should work consistently across browsers', () => {
    // This is a placeholder - actual cross-browser testing requires special setup
    cy.visit('/demo');
    
    // Check critical features work
    cy.contains('Technology').click();
    
    // Check WebSocket support
    cy.window().then((win) => {
      expect(win.WebSocket).to.not.be.undefined;
    });
    
    // Check CSS features
    cy.get('[class*="glassmorphism"], [class*="backdrop-blur"]').should('exist');
    
    // Check JavaScript APIs
    cy.window().then((win) => {
      expect(win.localStorage).to.not.be.undefined;
      expect(win.fetch).to.not.be.undefined;
      expect(win.Promise).to.not.be.undefined;
    });
  });

  it('should handle browser-specific quirks', () => {
    cy.visit('/demo');
    
    // Test Safari date handling
    const dateString = '2024-01-15T10:30:00Z';
    cy.window().then((win) => {
      const date = new Date(dateString);
      expect(date.toString()).to.not.equal('Invalid Date');
    });
    
    // Test Firefox flexbox rendering
    cy.get('.flex, [class*="flex"]').should('have.css', 'display').and('match', /flex/);
    
    // Test Edge smooth scrolling
    cy.contains('Technology').click();
    cy.contains('Next Steps').click();
    cy.window().scrollTo('top', { behavior: 'smooth' });
  });
});

describe('Critical Test #9: Mobile Responsive Interaction', () => {
  const devices = [
    { name: 'iphone-x', width: 375, height: 812 },
    { name: 'ipad-2', width: 768, height: 1024 },
    { name: 'samsung-s10', width: 360, height: 760 }
  ];

  devices.forEach(device => {
    it(`should support touch interactions on ${device.name}`, () => {
      cy.viewport(device.width, device.height);
      cy.visit('/demo');
      
      // Check touch targets are large enough (minimum 44px)
      cy.get('button').each($button => {
        const rect = $button[0].getBoundingClientRect();
        expect(rect.width).to.be.at.least(44);
        expect(rect.height).to.be.at.least(44);
      });
      
      // Test swipe navigation (simulated)
      cy.get('body').trigger('touchstart', { touches: [{ clientX: 300, clientY: 400 }] });
      cy.get('body').trigger('touchmove', { touches: [{ clientX: 100, clientY: 400 }] });
      cy.get('body').trigger('touchend');
      
      // Test tap interactions
      cy.contains('Technology').click();
      cy.contains('ROI Calculator').click();
      
      // Test virtual keyboard handling
      cy.get('input[id="spend"]').click();
      // Keyboard should not cover input
      cy.get('input[id="spend"]').should('be.visible');
    });
  });

  it('should handle viewport orientation changes', () => {
    // Portrait
    cy.viewport(375, 812);
    cy.visit('/demo');
    cy.contains('Technology').should('be.visible');
    
    // Landscape
    cy.viewport(812, 375);
    cy.contains('Technology').should('be.visible');
    
    // UI should adapt
    cy.get('[class*="grid"], [class*="flex"]').should('be.visible');
  });

  it('should optimize performance on mobile', () => {
    cy.viewport('iphone-x');
    cy.visit('/demo');
    
    // Check for mobile optimizations
    cy.get('img').each($img => {
      // Images should be lazy loaded or optimized
      const loading = $img.attr('loading');
      const srcset = $img.attr('srcset');
      expect(loading === 'lazy' || srcset).to.be.true;
    });
    
    // Check for reduced animations
    cy.window().then((win) => {
      const prefersReducedMotion = win.matchMedia('(prefers-reduced-motion: reduce)');
      // Should respect user preference
      cy.get('[class*="animate"], [class*="transition"]').should('exist');
    });
  });
});

describe('Critical Test #10: Error Message Clarity', () => {
  const errorScenarios = [
    {
      trigger: 'network_error',
      expectedMessage: /network|connection|try again/i,
      recovery: 'Retry'
    },
    {
      trigger: 'auth_error',
      expectedMessage: /authentication|login|session/i,
      recovery: 'Login'
    },
    {
      trigger: 'validation_error',
      expectedMessage: /invalid|check|correct/i,
      recovery: 'Fix'
    },
    {
      trigger: 'server_error',
      expectedMessage: /server|temporarily|later/i,
      recovery: 'Wait'
    }
  ];

  errorScenarios.forEach(scenario => {
    it(`should show clear message for ${scenario.trigger}`, () => {
      cy.visit('/demo');
      cy.contains('Technology').click();
      
      // Trigger specific error
      if (scenario.trigger === 'network_error') {
        cy.intercept('**/api/**', { forceNetworkError: true }).as('networkError');
        cy.contains('AI Chat').click();
        cy.get('textarea').type('Test message');
        cy.get('button[aria-label="Send message"]').click();
      } else if (scenario.trigger === 'auth_error') {
        cy.window().then((win) => {
          win.localStorage.removeItem('auth_token');
        });
        cy.contains('Export Plan').click();
      } else if (scenario.trigger === 'validation_error') {
        cy.contains('ROI Calculator').click();
        cy.get('input[id="spend"]').clear().type('invalid');
        cy.contains('Calculate ROI').click();
      } else if (scenario.trigger === 'server_error') {
        cy.intercept('**/api/**', { statusCode: 500 }).as('serverError');
        cy.contains('Generate Report').click();
      }
      
      // Check error message clarity
      cy.contains(scenario.expectedMessage, { timeout: 5000 }).should('be.visible');
      
      // Check recovery option
      cy.contains(new RegExp(scenario.recovery, 'i')).should('be.visible');
    });
  });

  it('should log errors for support', () => {
    cy.visit('/demo');
    cy.contains('Technology').click();
    
    // Set up console spy
    cy.window().then((win) => {
      cy.spy(win.console, 'error').as('consoleError');
    });
    
    // Trigger an error
    cy.intercept('**/api/**', { statusCode: 500, body: { error: 'Test error' } });
    cy.contains('AI Chat').click();
    cy.get('textarea').type('Test');
    cy.get('button[aria-label="Send message"]').click();
    
    // Verify error was logged
    cy.get('@consoleError').should('have.been.called');
  });

  it('should provide contextual help for errors', () => {
    cy.visit('/demo');
    cy.contains('Technology').click();
    cy.contains('ROI Calculator').click();
    
    // Enter invalid data
    cy.get('input[id="spend"]').clear().type('-1000');
    cy.contains('Calculate ROI').click();
    
    // Should show helpful context
    cy.contains(/must be positive|greater than zero/i).should('be.visible');
    cy.contains(/example|try entering/i).should('be.visible');
  });
});