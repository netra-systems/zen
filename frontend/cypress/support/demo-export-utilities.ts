/// <reference types="cypress" />

/**
 * Demo Export Testing Utilities Module
 * 
 * BVJ: Enterprise segment - enables data portability, supports compliance requirements
 * Provides reusable utilities for export functionality testing
 */

/**
 * Export format types supported by the application
 */
export type ExportFormat = 'JSON' | 'PDF' | 'CSV';

/**
 * Export test configuration interface
 */
export interface ExportTestConfig {
  format: ExportFormat;
  expectedContent: string;
  timeout?: number;
}

/**
 * Demo section navigation helper
 */
export class DemoNavigator {
  static setupViewport(): void {
    cy.viewport(1920, 1080);
  }

  static visitDemo(): void {
    cy.visit('/demo');
    cy.contains('Financial Services').click();
    cy.wait(500);
  }

  static navigateToSection(section: string): void {
    cy.contains(section).click();
    cy.wait(500);
  }

  static navigateToROI(): void {
    cy.contains('ROI Calculator').click();
  }

  static navigateToNextSteps(): void {
    cy.contains('Next Steps').click();
  }

  static navigateToMetrics(): void {
    cy.contains('Metrics').click();
  }

  static navigateToDataInsights(): void {
    cy.contains('Data Insights').click();
  }
}

/**
 * Export operation utilities
 */
export class ExportHelpers {
  static triggerROICalculation(): void {
    cy.get('input[id="spend"]').clear().type('100000');
    cy.contains('Calculate ROI').click();
    cy.wait(1000);
  }

  static mockBlobCreation(): void {
    cy.window().then((win) => {
      const stub = cy.stub(win.URL, 'createObjectURL');
      return stub;
    });
  }

  static verifyExportAlert(expectedText: string): void {
    cy.on('window:alert', (text) => {
      expect(text).to.contain(expectedText);
    });
  }

  static setupDownloadMock(): void {
    cy.window().then((win) => {
      cy.stub(win.document, 'createElement').callsFake((tagName) => {
        if (tagName === 'a') {
          const element = document.createElement('a');
          cy.stub(element, 'click').as('downloadClick');
          return element;
        }
        return document.createElement(tagName);
      });
    });
  }

  static verifyDownloadTriggered(): void {
    cy.get('@downloadClick').should('be.called');
  }
}

/**
 * Format-specific export validators
 */
export class FormatValidators {
  static validateJSONExport(): void {
    cy.window().then((win) => {
      const jsonBlob = new Blob(['{}'], { type: 'application/json' });
      cy.stub(win, 'Blob').returns(jsonBlob);
    });
  }

  static validatePDFExport(): void {
    cy.on('window:alert', (text) => {
      expect(text).to.match(/PDF|pdf/);
    });
  }

  static validateCSVExport(): void {
    cy.on('window:alert', (text) => {
      expect(text).to.match(/CSV|csv/);
    });
  }

  static validateTimestamp(): void {
    cy.on('window:alert', (text) => {
      expect(text).to.match(/\d{13}/); // Unix timestamp
    });
  }
}

/**
 * Mobile testing utilities
 */
export class MobileTestHelpers {
  static setMobileViewport(): void {
    cy.viewport('iphone-x');
  }

  static setTabletViewport(): void {
    cy.viewport('ipad-2');
  }

  static triggerTouchInteraction(selector: string): void {
    cy.contains(selector).trigger('touchstart');
    cy.contains(selector).trigger('touchend');
  }
}

/**
 * Error simulation utilities
 */
export class ErrorSimulators {
  static simulateExportFailure(): void {
    cy.window().then((win) => {
      cy.stub(win.URL, 'createObjectURL').throws(new Error('Export failed'));
    });
  }

  static simulateNetworkError(): void {
    cy.intercept('POST', '/api/export', { statusCode: 500 });
  }

  static handleExportError(): void {
    cy.on('fail', (err) => {
      expect(err.message).to.include('Export');
      return false;
    });
  }
}

/**
 * Analytics and tracking utilities
 */
export class AnalyticsHelpers {
  static setupConsoleLogging(): void {
    cy.window().then((win) => {
      cy.stub(win.console, 'log').as('consoleLog');
    });
  }

  static verifyAnalyticsCall(): void {
    cy.get('@consoleLog').should('be.called');
  }

  static completeFullDemo(): void {
    const sections = ['ROI Calculator', 'AI Chat', 'Metrics', 'Next Steps'];
    sections.forEach(section => {
      cy.contains(section).click();
      cy.wait(500);
    });
  }
}

/**
 * Demo completion utilities
 */
export class DemoCompletionHelpers {
  static performAIChat(): void {
    cy.contains('AI Chat').click();
    cy.get('textarea').type('Optimize my workload');
    cy.get('button[aria-label="Send message"]').click();
    cy.wait(2000);
  }

  static verifyCompletionStatus(): void {
    cy.contains('Demo Complete').should('exist');
  }

  static checkProgressBar(): void {
    cy.get('[role="progressbar"]').should('exist');
  }
}

/**
 * Report customization utilities
 */
export class ReportCustomization {
  static selectReportSections(): void {
    const sections = [
      'Implementation Phases',
      'Task Breakdown', 
      'Risk Management',
      'Support & Resources'
    ];
    
    sections.forEach(section => {
      cy.contains(section).click();
    });
  }

  static verifyIndustrySpecificContent(): void {
    cy.contains('fraud detection optimization').should('be.visible');
  }
}

/**
 * Session and state management utilities
 */
export class SessionHelpers {
  static reloadAndVerifyState(): void {
    cy.reload();
    cy.contains('Financial Services').should('be.visible');
  }

  static verifySessionPersistence(): void {
    cy.contains('ROI Calculator').click();
  }
}

/**
 * Export test suite configuration
 */
export const EXPORT_TEST_CONFIG = {
  defaultTimeout: 1000,
  exportFormats: ['JSON', 'PDF', 'CSV'] as ExportFormat[],
  mobileViewports: ['iphone-x', 'ipad-2'],
  expectedAlertTexts: {
    roi: 'roi-report',
    implementation: 'implementation',
    financialServices: 'financial-services',
    syntheticData: 'synthetic-data'
  }
};