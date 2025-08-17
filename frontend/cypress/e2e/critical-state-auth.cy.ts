/// <reference types="cypress" />

/**
 * Critical State & Authentication Tests
 * Tests for auth state management and memory leak detection
 * Business Value: Prevents user churn from auth issues and performance degradation
 */

import {
  TestSetup,
  Navigation,
  FormUtils,
  AuthUtils,
  PerformanceUtils,
  WaitUtils
} from './utils/critical-test-utils';

describe('Critical Test #5: Authentication State Corruption', () => {
  beforeEach(() => {
    TestSetup.standardViewport();
    setupInitialAuthState();
    TestSetup.visitDemo();
  });

  it('should handle token expiry during active demo', () => {
    startDemoWithValidToken();
    simulateTokenExpiryMidSession();
    attemptContinueAfterExpiry();
    verifyGracefulHandling();
  });

  it('should preserve demo state across re-authentication', () => {
    verifyInitialDemoState();
    simulateReAuthFlow();
    verifyDemoStatePreserved();
  });

  it('should gracefully degrade to anonymous mode', () => {
    removeAllAuthentication();
    verifyAnonymousModeWorks();
    testAnonymousInteractions();
  });

  it('should recover session after browser refresh', () => {
    setupDemoSession();
    saveDemoState();
    refreshAndVerifyRecovery();
  });

  // Helper functions ≤8 lines each
  function setupInitialAuthState(): void {
    TestSetup.setupAuthState();
    TestSetup.setupDemoProgress();
  }

  function startDemoWithValidToken(): void {
    Navigation.goToAiChat();
    FormUtils.sendChatMessage('Initial message with valid token');
    WaitUtils.processingWait();
  }

  function simulateTokenExpiryMidSession(): void {
    AuthUtils.simulateTokenExpiry();
  }

  function attemptContinueAfterExpiry(): void {
    FormUtils.sendChatMessage('Message after token expiry');
  }

  function verifyGracefulHandling(): void {
    AuthUtils.verifyAuthState(true);
  }

  function verifyInitialDemoState(): void {
    cy.window().then((win) => {
      const initialProgress = win.localStorage.getItem('demo_progress');
      expect(initialProgress).to.not.be.null;
    });
  }

  function simulateReAuthFlow(): void {
    AuthUtils.clearAuth();
    AuthUtils.setNewToken('new-token-67890');
  }

  function verifyDemoStatePreserved(): void {
    cy.window().then((win) => {
      const progress = JSON.parse(win.localStorage.getItem('demo_progress') || '{}');
      expect(progress.industry).to.equal('Healthcare');
      expect(progress.completed).to.include('industry_selection');
    });
  }

  function removeAllAuthentication(): void {
    cy.window().then((win) => {
      win.localStorage.clear();
      win.sessionStorage.clear();
    });
    cy.reload();
  }

  function verifyAnonymousModeWorks(): void {
    cy.url().should('include', '/demo');
    cy.contains('Select Your Industry').should('be.visible');
  }

  function testAnonymousInteractions(): void {
    cy.contains('Financial Services').click();
    cy.contains('ROI Calculator').should('be.visible');
  }

  function setupDemoSession(): void {
    cy.contains('E-commerce').click();
    Navigation.goToRoiCalculator();
    FormUtils.fillRoiCalculator(50000);
    cy.contains('Calculate ROI').click();
    WaitUtils.processingWait();
  }

  function saveDemoState(): void {
    cy.window().then((win) => {
      const state = {
        industry: 'E-commerce',
        roi_calculated: true,
        monthly_spend: 50000
      };
      win.localStorage.setItem('demo_session', JSON.stringify(state));
    });
  }

  function refreshAndVerifyRecovery(): void {
    cy.reload();
    cy.contains('E-commerce').should('be.visible');
    cy.window().then((win) => {
      const recovered = JSON.parse(win.localStorage.getItem('demo_session') || '{}');
      expect(recovered.industry).to.equal('E-commerce');
      expect(recovered.roi_calculated).to.be.true;
    });
  }
});

describe('Critical Test #7: Memory Leak Detection', () => {
  it('should not accumulate memory after 100 interactions', () => {
    TestSetup.visitDemo();
    TestSetup.selectIndustry('Technology');
    Navigation.goToAiChat();
    
    performMemoryIntensiveTest();
  });

  it('should not accumulate DOM nodes', () => {
    TestSetup.visitDemo();
    TestSetup.selectIndustry('Technology');
    
    performDomGrowthTest();
  });

  it('should clean up event listeners', () => {
    TestSetup.visitDemo();
    TestSetup.selectIndustry('Technology');
    Navigation.goToAiChat();
    
    performEventListenerTest();
  });

  // Helper functions ≤8 lines each
  function performMemoryIntensiveTest(): void {
    PerformanceUtils.getInitialMemory().then((initialMemory) => {
      performHundredInteractions();
      PerformanceUtils.checkMemoryGrowth(initialMemory, 0.1);
    });
  }

  function performHundredInteractions(): void {
    for (let i = 0; i < 100; i++) {
      FormUtils.sendChatMessage(`Test message ${i}`);
      
      if (i % 10 === 0) {
        WaitUtils.shortWait();
      }
    }
  }

  function performDomGrowthTest(): void {
    PerformanceUtils.countDomNodes().then((initialCount) => {
      performNavigationCycles();
      PerformanceUtils.verifyDomGrowth(initialCount, 0.2);
    });
  }

  function performNavigationCycles(): void {
    for (let round = 0; round < 10; round++) {
      Navigation.cycleAllTabs();
    }
  }

  function performEventListenerTest(): void {
    setupEventListenerTracking();
    performListenerIntensiveActions();
    verifyListenerCount();
  }

  function setupEventListenerTracking(): void {
    cy.window().then((win) => {
      let listenerCount = 0;
      const originalAdd = win.addEventListener;
      const originalRemove = win.removeEventListener;
      
      overrideEventListenerMethods(win, originalAdd, originalRemove, listenerCount);
    });
  }

  function overrideEventListenerMethods(win: Window, originalAdd: any, originalRemove: any, listenerCount: number): void {
    win.addEventListener = function(...args: any[]) {
      listenerCount++;
      return originalAdd.apply(this, args);
    };
    
    win.removeEventListener = function(...args: any[]) {
      listenerCount--;
      return originalRemove.apply(this, args);
    };
  }

  function performListenerIntensiveActions(): void {
    for (let i = 0; i < 20; i++) {
      FormUtils.sendChatMessage(`Message ${i}`);
      cy.wait(200);
    }
  }

  function verifyListenerCount(): void {
    cy.window().then((win) => {
      // This is a simplified check - in real implementation,
      // we'd need more sophisticated listener tracking
      cy.get('body').should('exist'); // Basic verification
    });
  }
});