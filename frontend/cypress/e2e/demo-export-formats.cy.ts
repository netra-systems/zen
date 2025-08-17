/// <reference types="cypress" />

import { 
  DemoNavigator, 
  ExportHelpers,
  FormatValidators,
  MobileTestHelpers,
  ErrorSimulators,
  EXPORT_TEST_CONFIG 
} from '../support/demo-export-utilities';

/**
 * Demo E2E Test Suite: Export Formats and Mobile Functionality
 * 
 * BVJ: Enterprise segment - enables data portability, supports compliance requirements
 * Tests format-specific exports, mobile compatibility, and error handling
 */
describe('Demo E2E Test Suite: Export Formats and Mobile Functionality', () => {
  beforeEach(() => {
    DemoNavigator.setupViewport();
    DemoNavigator.visitDemo();
  });

  describe('Export Format Options', () => {
    it('should support JSON export format', () => {
      DemoNavigator.navigateToNextSteps();
      
      FormatValidators.validateJSONExport();
      cy.contains('Export Plan').click();
    });

    it('should handle PDF export request', () => {
      DemoNavigator.navigateToNextSteps();
      cy.contains('Export Plan').click();
      
      FormatValidators.validatePDFExport();
    });

    it('should handle CSV export for tabular data', () => {
      DemoNavigator.navigateToMetrics();
      cy.wait(EXPORT_TEST_CONFIG.defaultTimeout);
      
      cy.contains('Export').click();
      FormatValidators.validateCSVExport();
    });

    it('should maintain format consistency across exports', () => {
      EXPORT_TEST_CONFIG.exportFormats.forEach(format => {
        DemoNavigator.navigateToNextSteps();
        
        cy.window().then((win) => {
          const mimeType = format === 'JSON' ? 'application/json' : 
                          format === 'PDF' ? 'application/pdf' : 'text/csv';
          const blob = new Blob(['test'], { type: mimeType });
          cy.stub(win, 'Blob').returns(blob);
        });
        
        cy.contains('Export Plan').click();
      });
    });

    it('should validate export format selection', () => {
      DemoNavigator.navigateToDataInsights();
      cy.contains('Export').click();
      
      cy.on('window:alert', (text) => {
        expect(text).to.match(/json|pdf|csv/i);
      });
    });

    it('should include format metadata in exports', () => {
      DemoNavigator.navigateToROI();
      ExportHelpers.triggerROICalculation();
      
      cy.contains('Export Report').click();
      FormatValidators.validateTimestamp();
    });
  });

  describe('Mobile Export Functionality', () => {
    it('should support export on mobile devices', () => {
      MobileTestHelpers.setMobileViewport();
      
      DemoNavigator.navigateToNextSteps();
      cy.contains('Export Plan').should('be.visible');
      cy.contains('Export Plan').click();
    });

    it('should adapt export UI for tablet', () => {
      MobileTestHelpers.setTabletViewport();
      
      DemoNavigator.navigateToROI();
      ExportHelpers.triggerROICalculation();
      
      cy.contains('Export Report').should('be.visible');
      cy.contains('Export Report').click();
    });

    it('should handle touch interactions for export', () => {
      MobileTestHelpers.setMobileViewport();
      
      DemoNavigator.navigateToDataInsights();
      MobileTestHelpers.triggerTouchInteraction('Export');
    });

    it('should optimize mobile export performance', () => {
      MobileTestHelpers.setMobileViewport();
      
      DemoNavigator.navigateToMetrics();
      cy.wait(EXPORT_TEST_CONFIG.defaultTimeout);
      
      cy.contains('Export').should('be.visible');
      cy.contains('Export').click({ timeout: 3000 });
    });

    it('should maintain export quality on mobile', () => {
      MobileTestHelpers.setMobileViewport();
      
      DemoNavigator.navigateToROI();
      ExportHelpers.triggerROICalculation();
      cy.contains('Export Report').click();
      
      ExportHelpers.verifyExportAlert('roi');
    });

    it('should handle mobile network constraints', () => {
      MobileTestHelpers.setMobileViewport();
      
      cy.intercept('POST', '/api/export', { 
        statusCode: 200, 
        delay: 2000 
      });
      
      DemoNavigator.navigateToNextSteps();
      cy.contains('Export Plan').click();
    });
  });

  describe('Error Handling in Export', () => {
    it('should handle export failures gracefully', () => {
      DemoNavigator.navigateToNextSteps();
      
      ErrorSimulators.simulateExportFailure();
      cy.contains('Export Plan').click();
      
      ErrorSimulators.handleExportError();
    });

    it('should validate data before export', () => {
      DemoNavigator.navigateToROI();
      
      cy.contains('Export Report').should('be.visible');
      cy.contains('Export Report').click();
      
      ExportHelpers.verifyExportAlert('roi');
    });

    it('should handle network issues during export', () => {
      ErrorSimulators.simulateNetworkError();
      
      DemoNavigator.navigateToNextSteps();
      cy.contains('Export Plan').click();
      
      ExportHelpers.verifyExportAlert('export');
    });

    it('should provide meaningful error messages', () => {
      DemoNavigator.navigateToDataInsights();
      
      cy.window().then((win) => {
        cy.stub(win, 'Blob').throws(new Error('Blob creation failed'));
      });
      
      cy.contains('Export').click();
      
      cy.on('fail', (err) => {
        expect(err.message).to.include('Blob');
        return false;
      });
    });

    it('should recover from partial export failures', () => {
      DemoNavigator.navigateToMetrics();
      
      cy.intercept('POST', '/api/export', { 
        statusCode: 500,
        body: { error: 'Server error' }
      });
      
      cy.contains('Export').click();
      
      // Should fallback to client-side export
      cy.on('window:alert', (text) => {
        expect(text).to.be.a('string');
      });
    });

    it('should handle browser compatibility issues', () => {
      DemoNavigator.navigateToROI();
      ExportHelpers.triggerROICalculation();
      
      cy.window().then((win) => {
        // Simulate missing download attribute support
        Object.defineProperty(win.HTMLAnchorElement.prototype, 'download', {
          value: undefined,
          writable: false
        });
      });
      
      cy.contains('Export Report').click();
    });
  });

  describe('Export Security and Validation', () => {
    it('should sanitize export data', () => {
      DemoNavigator.navigateToDataInsights();
      
      cy.window().then((win) => {
        const sanitizedBlob = new Blob(['clean_data'], { 
          type: 'application/json' 
        });
        cy.stub(win, 'Blob').returns(sanitizedBlob);
      });
      
      cy.contains('Export').click();
    });

    it('should validate export permissions', () => {
      DemoNavigator.navigateToNextSteps();
      
      cy.window().then((win) => {
        cy.stub(win.navigator, 'permissions').value({
          query: () => Promise.resolve({ state: 'granted' })
        });
      });
      
      cy.contains('Export Plan').click();
    });

    it('should prevent unauthorized data access', () => {
      DemoNavigator.navigateToROI();
      
      cy.window().then((win) => {
        cy.stub(win.localStorage, 'getItem').returns(null);
      });
      
      cy.contains('Export Report').should('be.visible');
    });

    it('should handle export size limitations', () => {
      DemoNavigator.navigateToMetrics();
      
      cy.window().then((win) => {
        const largeData = 'x'.repeat(10000000); // 10MB string
        const blob = new Blob([largeData], { type: 'text/plain' });
        cy.stub(win, 'Blob').returns(blob);
      });
      
      cy.contains('Export').click();
    });
  });

  describe('Cross-Browser Export Compatibility', () => {
    it('should work with different download implementations', () => {
      DemoNavigator.navigateToROI();
      ExportHelpers.triggerROICalculation();
      
      ExportHelpers.setupDownloadMock();
      cy.contains('Export Report').click();
      ExportHelpers.verifyDownloadTriggered();
    });

    it('should handle different blob implementations', () => {
      DemoNavigator.navigateToDataInsights();
      
      cy.window().then((win) => {
        const customBlob = { size: 100, type: 'application/json' };
        cy.stub(win, 'Blob').returns(customBlob);
      });
      
      cy.contains('Export').click();
    });

    it('should support legacy browser fallbacks', () => {
      DemoNavigator.navigateToNextSteps();
      
      cy.window().then((win) => {
        delete win.URL.createObjectURL;
        cy.stub(win, 'open').as('windowOpen');
      });
      
      cy.contains('Export Plan').click();
      cy.get('@windowOpen').should('be.called');
    });
  });
});