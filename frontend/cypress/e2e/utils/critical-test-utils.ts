/// <reference types="cypress" />

/**
 * Critical E2E Test Utilities
 * Shared utilities for modular critical test suites
 * Business Value: Reduces test maintenance, ensures consistency
 */

// Test Data Constants
export const INDUSTRIES = [
  { name: 'Financial Services', multiplier: 1.5, baseline: 100000 },
  { name: 'Healthcare', multiplier: 1.3, baseline: 80000 },
  { name: 'E-commerce', multiplier: 1.4, baseline: 60000 },
  { name: 'Technology', multiplier: 1.6, baseline: 120000 }
] as const;

export const ERROR_SCENARIOS = [
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
] as const;

export const MOBILE_DEVICES = [
  { name: 'iphone-x', width: 375, height: 812 },
  { name: 'ipad-2', width: 768, height: 1024 },
  { name: 'samsung-s10', width: 360, height: 760 }
] as const;

// Setup Utilities
export class TestSetup {
  static standardViewport(): void {
    cy.viewport(1920, 1080);
  }

  static visitDemo(): void {
    cy.visit('/demo');
  }

  static selectIndustry(industry: string): void {
    cy.contains(industry).click();
  }

  static setupAuthState(): void {
    cy.window().then((win) => {
      win.localStorage.setItem('auth_token', 'initial-token-12345');
    });
  }

  static setupDemoProgress(): void {
    cy.window().then((win) => {
      const progress = {
        industry: 'Healthcare',
        step: 2,
        completed: ['industry_selection', 'roi_calculation']
      };
      win.localStorage.setItem('demo_progress', JSON.stringify(progress));
    });
  }
}

// Navigation Utilities  
export class Navigation {
  static goToSyntheticData(): void {
    cy.contains('Synthetic Data').click();
  }

  static goToAiChat(): void {
    cy.contains('AI Chat').click();
  }

  static goToRoiCalculator(): void {
    cy.contains('ROI Calculator').click();
  }

  static cycleAllTabs(): void {
    const tabs = ['Overview', 'ROI Calculator', 'AI Chat', 'Metrics', 'Synthetic Data', 'Next Steps'];
    tabs.forEach(tab => {
      cy.contains(tab).click();
      cy.wait(500);
    });
  }
}

// Form Interaction Utilities
export class FormUtils {
  static fillDataGeneration(records: number, seed?: number): void {
    cy.get('input[name="recordCount"]').clear().type(records.toString());
    if (seed) {
      cy.get('input[name="seed"]').clear().type(seed.toString());
    }
  }

  static fillRoiCalculator(spend: number, requests?: number): void {
    cy.get('input[id="spend"]').clear().type(spend.toString());
    if (requests) {
      cy.get('input[id="requests"]').clear().type(requests.toString());
    }
  }

  static sendChatMessage(message: string): void {
    cy.get('textarea').clear().type(message);
    cy.get('button[aria-label="Send message"]').click();
  }
}

// Assertion Utilities
export class Assertions {
  static verifyGenerationComplete(recordCount: string): void {
    const pattern = new RegExp(`generated.*${recordCount}|${recordCount}.*records`, 'i');
    cy.contains(pattern, { timeout: 30000 }).should('be.visible');
  }

  static verifyInsightsGenerated(): void {
    cy.contains(/insights|opportunities|recommendations/i, { timeout: 15000 })
      .should('be.visible');
  }

  static verifySavingsCalculation(): void {
    cy.contains(/savings|reduction|optimize/i).should('be.visible');
    cy.contains(/\d+%|\$\d+/i).should('be.visible');
  }

  static verifyErrorMessage(pattern: RegExp): void {
    cy.contains(pattern, { timeout: 5000 }).should('be.visible');
  }
}

// Performance Monitoring Utilities
export class PerformanceUtils {
  static getInitialMemory(): Cypress.Chainable<number> {
    return cy.window().then((win) => {
      if ((win.performance as any).memory) {
        return (win.performance as any).memory.usedJSHeapSize;
      }
      return 0;
    });
  }

  static checkMemoryGrowth(initialMemory: number, maxGrowth: number): void {
    cy.window().then((win) => {
      if ((win.performance as any).memory) {
        const finalMemory = (win.performance as any).memory.usedJSHeapSize;
        const growth = (finalMemory - initialMemory) / initialMemory;
        expect(growth).to.be.lessThan(maxGrowth);
      }
    });
  }

  static countDomNodes(): Cypress.Chainable<number> {
    return cy.document().then((doc) => {
      return doc.getElementsByTagName('*').length;
    });
  }

  static verifyDomGrowth(initial: number, maxGrowth: number): void {
    cy.document().then((doc) => {
      const final = doc.getElementsByTagName('*').length;
      const growth = (final - initial) / initial;
      expect(growth).to.be.lessThan(maxGrowth);
    });
  }
}

// Authentication Utilities
export class AuthUtils {
  static simulateTokenExpiry(): void {
    cy.window().then((win) => {
      win.localStorage.setItem('auth_token', 'expired-token');
      win.dispatchEvent(new Event('storage'));
    });
  }

  static clearAuth(): void {
    cy.window().then((win) => {
      win.localStorage.removeItem('auth_token');
      win.dispatchEvent(new Event('storage'));
    });
  }

  static setNewToken(token: string): void {
    cy.window().then((win) => {
      win.localStorage.setItem('auth_token', token);
      win.dispatchEvent(new Event('storage'));
    });
  }

  static verifyAuthState(hasAuth: boolean): void {
    cy.get('body').then(($body) => {
      const hasAuthPrompt = $body.find('[class*="auth"], [class*="login"]').length > 0;
      const continuesAnonymous = $body.find('textarea').length > 0;
      
      if (hasAuth) {
        expect(hasAuthPrompt || continuesAnonymous).to.be.true;
      } else {
        expect(continuesAnonymous).to.be.true;
      }
    });
  }
}

// Mobile Testing Utilities
export class MobileUtils {
  static checkTouchTargets(): void {
    cy.get('button').each($button => {
      const rect = $button[0].getBoundingClientRect();
      expect(rect.width).to.be.at.least(44);
      expect(rect.height).to.be.at.least(44);
    });
  }

  static simulateSwipe(): void {
    cy.get('body').trigger('touchstart', { touches: [{ clientX: 300, clientY: 400 }] });
    cy.get('body').trigger('touchmove', { touches: [{ clientX: 100, clientY: 400 }] });
    cy.get('body').trigger('touchend');
  }

  static checkImageOptimization(): void {
    cy.get('img').each($img => {
      const loading = $img.attr('loading');
      const srcset = $img.attr('srcset');
      expect(loading === 'lazy' || srcset).to.be.true;
    });
  }
}

// Error Simulation Utilities
export class ErrorSimulation {
  static triggerNetworkError(): void {
    cy.intercept('**/api/**', { forceNetworkError: true }).as('networkError');
  }

  static triggerServerError(): void {
    cy.intercept('**/api/**', { statusCode: 500 }).as('serverError');
  }

  static triggerAuthError(): void {
    cy.window().then((win) => {
      win.localStorage.removeItem('auth_token');
    });
  }

  static setupConsoleErrorSpy(): void {
    cy.window().then((win) => {
      cy.spy(win.console, 'error').as('consoleError');
    });
  }
}

// Wait Utilities
export class WaitUtils {
  static shortWait(): void {
    cy.wait(1000);
  }

  static mediumWait(): void {
    cy.wait(3000);
  }

  static longWait(): void {
    cy.wait(5000);
  }

  static processingWait(): void {
    cy.wait(2000);
  }
}

// Calculation Utilities
export class CalculationUtils {
  static calculateExpectedSavings(baseline: number, multiplier: number): number {
    return baseline * 0.45 * multiplier; // 45% base savings
  }

  static getSavingsRange(expected: number): { min: number; max: number } {
    return {
      min: expected * 0.9,
      max: expected * 1.1
    };
  }

  static verifySavingsInRange(expected: number): void {
    const { min, max } = this.getSavingsRange(expected);
    
    cy.get('[data-testid="monthly-savings"], [class*="savings"]').then($el => {
      const text = $el.text();
      const savings = parseFloat(text.replace(/[^0-9.-]/g, ''));
      expect(savings).to.be.within(min, max);
    });
  }
}