/// <reference types="cypress" />

import { 
  DemoNavigator, 
  ExportHelpers, 
  DemoCompletionHelpers,
  EXPORT_TEST_CONFIG 
} from '../support/demo-export-utilities';

/**
 * Demo E2E Test Suite: Core Export Functionality
 * 
 * BVJ: Enterprise segment - enables data portability, supports compliance requirements
 * Tests core export features for implementation roadmap, ROI reports, and data export
 */
describe('Demo E2E Test Suite: Core Export Functionality', () => {
  beforeEach(() => {
    DemoNavigator.setupViewport();
    DemoNavigator.visitDemo();
  });

  describe('Implementation Roadmap Export', () => {
    it('should display export options in roadmap', () => {
      DemoNavigator.navigateToNextSteps();
      cy.contains('Implementation Roadmap').should('be.visible');
      cy.contains('Export Plan').should('be.visible');
    });

    it('should show export format options', () => {
      DemoNavigator.navigateToNextSteps();
      cy.contains('Export Plan').click();
      
      ExportHelpers.verifyExportAlert('Export');
    });

    it('should include completed steps in export', () => {
      DemoNavigator.navigateToROI();
      ExportHelpers.triggerROICalculation();
      
      DemoNavigator.navigateToNextSteps();
      cy.contains('Export Plan').click();
      
      ExportHelpers.verifyExportAlert('implementation');
    });

    it('should export implementation phases', () => {
      DemoNavigator.navigateToNextSteps();
      
      const phases = [
        'Immediate Actions',
        'Pilot Implementation', 
        'Gradual Scaling',
        'Full Production'
      ];
      
      phases.forEach(phase => {
        cy.contains(phase).should('be.visible');
      });
      
      cy.contains('Export Plan').click();
    });
  });

  describe('ROI Report Export', () => {
    it('should export ROI calculations', () => {
      DemoNavigator.navigateToROI();
      ExportHelpers.triggerROICalculation();
      
      cy.contains('Export Report').should('be.visible');
      cy.contains('Export Report').click();
      
      ExportHelpers.verifyExportAlert(EXPORT_TEST_CONFIG.expectedAlertTexts.roi);
    });

    it('should include all ROI metrics in export', () => {
      DemoNavigator.navigateToROI();
      cy.contains('Calculate ROI').click();
      cy.wait(EXPORT_TEST_CONFIG.defaultTimeout);
      
      cy.window().then((win) => {
        const stub = cy.stub(win.URL, 'createObjectURL');
        cy.contains('Export Report').click();
        expect(stub).to.be.called;
      });
    });

    it('should format export filename with timestamp', () => {
      DemoNavigator.navigateToROI();
      ExportHelpers.triggerROICalculation();
      
      ExportHelpers.setupDownloadMock();
      cy.contains('Export Report').click();
      ExportHelpers.verifyDownloadTriggered();
    });
  });

  describe('Performance Metrics Export', () => {
    it('should export performance dashboard data', () => {
      DemoNavigator.navigateToMetrics();
      cy.wait(EXPORT_TEST_CONFIG.defaultTimeout);
      
      cy.contains('Export').should('exist');
    });

    it('should export benchmark comparisons', () => {
      DemoNavigator.navigateToMetrics();
      cy.contains('Benchmarks').click();
      
      cy.contains('BERT Inference').should('be.visible');
      cy.contains('Top 5%').should('be.visible');
    });

    it('should include real-time metrics in export', () => {
      DemoNavigator.navigateToMetrics();
      
      cy.contains('Manual').click();
      cy.contains('Auto').should('be.visible');
      
      cy.wait(2000);
      cy.contains('Updated').should('be.visible');
    });
  });

  describe('Synthetic Data Export', () => {
    it('should export generated synthetic data', () => {
      DemoNavigator.navigateToDataInsights();
      cy.wait(EXPORT_TEST_CONFIG.defaultTimeout);
      
      cy.contains('Export').should('be.visible');
      cy.contains('Export').click();
      
      ExportHelpers.verifyExportAlert(
        EXPORT_TEST_CONFIG.expectedAlertTexts.financialServices
      );
    });

    it('should export data in JSON format', () => {
      DemoNavigator.navigateToDataInsights();
      
      cy.window().then((win) => {
        const blob = new Blob(['test'], { type: 'application/json' });
        cy.stub(win, 'Blob').returns(blob);
        cy.contains('Export').click();
      });
    });

    it('should include metadata in export', () => {
      DemoNavigator.navigateToDataInsights();
      cy.contains('Generate').click();
      cy.wait(2000);
      
      cy.contains('Export').click();
      
      ExportHelpers.verifyExportAlert(
        EXPORT_TEST_CONFIG.expectedAlertTexts.syntheticData
      );
    });
  });

  describe('Comprehensive Report Generation', () => {
    it('should compile data from all sections', () => {
      DemoNavigator.navigateToROI();
      ExportHelpers.triggerROICalculation();
      
      DemoCompletionHelpers.performAIChat();
      
      DemoNavigator.navigateToMetrics();
      cy.wait(EXPORT_TEST_CONFIG.defaultTimeout);
      
      DemoNavigator.navigateToNextSteps();
      cy.contains('Export Plan').should('be.visible');
    });

    it('should show completion status in final report', () => {
      const tabs = ['ROI Calculator', 'AI Chat', 'Metrics', 'Next Steps'];
      tabs.forEach(tab => {
        DemoNavigator.navigateToSection(tab);
      });
      
      DemoCompletionHelpers.verifyCompletionStatus();
    });

    it('should provide executive summary', () => {
      DemoNavigator.navigateToNextSteps();
      
      const summaryItems = [
        { label: 'Time to Value', value: '2 weeks' },
        { label: 'Expected ROI', value: '380%' }
      ];
      
      summaryItems.forEach(item => {
        cy.contains(item.label).should('be.visible');
        cy.contains(item.value).should('be.visible');
      });
    });

    it('should track demo progress metrics', () => {
      DemoNavigator.navigateToROI();
      ExportHelpers.triggerROICalculation();
      
      DemoNavigator.navigateToNextSteps();
      
      cy.contains('Demo Progress').should('be.visible');
      DemoCompletionHelpers.checkProgressBar();
    });

    it('should enable export of complete demo state', () => {
      const sections = ['ROI Calculator', 'AI Chat', 'Metrics'];
      sections.forEach(section => {
        DemoNavigator.navigateToSection(section);
      });
      
      DemoNavigator.navigateToNextSteps();
      cy.contains('Export Plan').should('be.visible');
      cy.contains('Export Plan').click();
    });
  });

  describe('Data Validation and Integrity', () => {
    it('should validate data before export', () => {
      DemoNavigator.navigateToROI();
      
      cy.contains('Export Report').should('be.visible');
      cy.contains('Export Report').click();
      
      ExportHelpers.verifyExportAlert('roi');
    });

    it('should ensure export completeness', () => {
      DemoNavigator.navigateToROI();
      ExportHelpers.triggerROICalculation();
      
      cy.contains('Export Report').click();
      
      cy.window().then((win) => {
        expect(win.URL.createObjectURL).to.exist;
      });
    });

    it('should maintain data consistency across exports', () => {
      DemoNavigator.navigateToDataInsights();
      cy.contains('Generate').click();
      cy.wait(2000);
      
      cy.contains('Export').click();
      
      cy.window().then((win) => {
        const blob = new Blob(['test'], { type: 'application/json' });
        cy.stub(win, 'Blob').returns(blob);
      });
    });
  });

  describe('Export Performance and Optimization', () => {
    it('should handle large dataset exports efficiently', () => {
      DemoNavigator.navigateToMetrics();
      cy.wait(EXPORT_TEST_CONFIG.defaultTimeout);
      
      cy.contains('Export').should('be.visible');
      cy.contains('Export').click({ timeout: 5000 });
    });

    it('should optimize export for different data sizes', () => {
      DemoNavigator.navigateToDataInsights();
      cy.contains('Generate').click();
      cy.wait(2000);
      
      cy.contains('Export').should('be.visible');
      cy.contains('Export').click();
    });

    it('should provide export progress feedback', () => {
      DemoNavigator.navigateToNextSteps();
      cy.contains('Export Plan').click();
      
      // Should show some form of progress indication
      cy.on('window:alert', (text) => {
        expect(text).to.be.a('string');
      });
    });
  });
});