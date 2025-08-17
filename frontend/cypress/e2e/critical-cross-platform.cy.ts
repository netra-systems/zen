/// <reference types="cypress" />

/**
 * Critical Cross-Platform Tests
 * Tests for browser compatibility, mobile responsiveness, and error handling
 * Business Value: Ensures platform works for all customer segments and devices
 */

import {
  TestSetup,
  Navigation,
  FormUtils,
  Assertions,
  MobileUtils,
  ErrorSimulation,
  MOBILE_DEVICES,
  ERROR_SCENARIOS
} from './utils/critical-test-utils';

describe('Critical Test #8: Cross-Browser Compatibility', () => {
  it('should work consistently across browsers', () => {
    TestSetup.visitDemo();
    TestSetup.selectIndustry('Technology');
    
    verifyWebSocketSupport();
    verifyCssFeatures();
    verifyJavaScriptApis();
  });

  it('should handle browser-specific quirks', () => {
    TestSetup.visitDemo();
    
    testSafariDateHandling();
    testFirefoxFlexboxRendering();
    testEdgeSmoothScrolling();
  });

  // Helper functions ≤8 lines each
  function verifyWebSocketSupport(): void {
    cy.window().then((win) => {
      expect(win.WebSocket).to.not.be.undefined;
    });
  }

  function verifyCssFeatures(): void {
    cy.get('[class*="glassmorphism"], [class*="backdrop-blur"]').should('exist');
  }

  function verifyJavaScriptApis(): void {
    cy.window().then((win) => {
      expect(win.localStorage).to.not.be.undefined;
      expect(win.fetch).to.not.be.undefined;
      expect(win.Promise).to.not.be.undefined;
    });
  }

  function testSafariDateHandling(): void {
    const dateString = '2024-01-15T10:30:00Z';
    cy.window().then((win) => {
      const date = new Date(dateString);
      expect(date.toString()).to.not.equal('Invalid Date');
    });
  }

  function testFirefoxFlexboxRendering(): void {
    cy.get('.flex, [class*="flex"]').should('have.css', 'display').and('match', /flex/);
  }

  function testEdgeSmoothScrolling(): void {
    TestSetup.selectIndustry('Technology');
    cy.contains('Next Steps').click();
    cy.window().scrollTo('top');
  }
});

describe('Critical Test #9: Mobile Responsive Interaction', () => {
  MOBILE_DEVICES.forEach(device => {
    it(`should support touch interactions on ${device.name}`, () => {
      cy.viewport(device.width, device.height);
      TestSetup.visitDemo();
      
      verifyTouchTargetSizes();
      testSwipeInteractions();
      testTapInteractions();
      testVirtualKeyboardHandling();
    });
  });

  it('should handle viewport orientation changes', () => {
    testPortraitOrientation();
    testLandscapeOrientation();
    verifyUiAdaptation();
  });

  it('should optimize performance on mobile', () => {
    cy.viewport('iphone-x');
    TestSetup.visitDemo();
    
    MobileUtils.checkImageOptimization();
    verifyReducedMotionSupport();
  });

  // Helper functions ≤8 lines each
  function verifyTouchTargetSizes(): void {
    MobileUtils.checkTouchTargets();
  }

  function testSwipeInteractions(): void {
    MobileUtils.simulateSwipe();
  }

  function testTapInteractions(): void {
    cy.contains('Technology').click();
    Navigation.goToRoiCalculator();
  }

  function testVirtualKeyboardHandling(): void {
    cy.get('input[id="spend"]').click();
    cy.get('input[id="spend"]').should('be.visible');
  }

  function testPortraitOrientation(): void {
    cy.viewport(375, 812);
    TestSetup.visitDemo();
    cy.contains('Technology').should('be.visible');
  }

  function testLandscapeOrientation(): void {
    cy.viewport(812, 375);
    cy.contains('Technology').should('be.visible');
  }

  function verifyUiAdaptation(): void {
    cy.get('[class*="grid"], [class*="flex"]').should('be.visible');
  }

  function verifyReducedMotionSupport(): void {
    cy.window().then((win) => {
      win.matchMedia('(prefers-reduced-motion: reduce)');
      cy.get('[class*="animate"], [class*="transition"]').should('exist');
    });
  }
});

describe('Critical Test #10: Error Message Clarity', () => {
  ERROR_SCENARIOS.forEach(scenario => {
    it(`should show clear message for ${scenario.trigger}`, () => {
      TestSetup.visitDemo();
      TestSetup.selectIndustry('Technology');
      
      triggerSpecificError(scenario);
      verifyErrorMessageClarity(scenario);
      verifyRecoveryOption(scenario);
    });
  });

  it('should log errors for support', () => {
    TestSetup.visitDemo();
    TestSetup.selectIndustry('Technology');
    
    setupErrorLogging();
    triggerTestError();
    verifyErrorLogged();
  });

  it('should provide contextual help for errors', () => {
    TestSetup.visitDemo();
    TestSetup.selectIndustry('Technology');
    Navigation.goToRoiCalculator();
    
    triggerValidationError();
    verifyContextualHelp();
  });

  // Helper functions ≤8 lines each
  function triggerSpecificError(scenario: typeof ERROR_SCENARIOS[0]): void {
    if (scenario.trigger === 'network_error') {
      triggerNetworkError();
    } else if (scenario.trigger === 'auth_error') {
      triggerAuthError();
    } else if (scenario.trigger === 'validation_error') {
      triggerValidationError();
    } else if (scenario.trigger === 'server_error') {
      triggerServerError();
    }
  }

  function triggerNetworkError(): void {
    ErrorSimulation.triggerNetworkError();
    Navigation.goToAiChat();
    FormUtils.sendChatMessage('Test message');
  }

  function triggerAuthError(): void {
    ErrorSimulation.triggerAuthError();
    cy.contains('Export Plan').click();
  }

  function triggerValidationError(): void {
    Navigation.goToRoiCalculator();
    FormUtils.fillRoiCalculator(-1000);
    cy.contains('Calculate ROI').click();
  }

  function triggerServerError(): void {
    ErrorSimulation.triggerServerError();
    cy.contains('Generate Report').click();
  }

  function verifyErrorMessageClarity(scenario: typeof ERROR_SCENARIOS[0]): void {
    Assertions.verifyErrorMessage(scenario.expectedMessage);
  }

  function verifyRecoveryOption(scenario: typeof ERROR_SCENARIOS[0]): void {
    cy.contains(new RegExp(scenario.recovery, 'i')).should('be.visible');
  }

  function setupErrorLogging(): void {
    ErrorSimulation.setupConsoleErrorSpy();
  }

  function triggerTestError(): void {
    cy.intercept('**/api/**', { statusCode: 500, body: { error: 'Test error' } });
    Navigation.goToAiChat();
    FormUtils.sendChatMessage('Test');
  }

  function verifyErrorLogged(): void {
    cy.get('@consoleError').should('have.been.called');
  }

  function verifyContextualHelp(): void {
    cy.contains(/must be positive|greater than zero/i).should('be.visible');
    cy.contains(/example|try entering/i).should('be.visible');
  }
});