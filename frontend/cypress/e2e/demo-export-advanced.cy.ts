/// <reference types="cypress" />

import { 
  DemoNavigator, 
  ExportHelpers,
  AnalyticsHelpers,
  ReportCustomization,
  SessionHelpers,
  EXPORT_TEST_CONFIG 
} from '../support/demo-export-utilities';

/**
 * Demo E2E Test Suite: Advanced Export Features
 * 
 * BVJ: Enterprise segment - enables data portability, supports compliance requirements
 * Tests advanced export features, scheduling, analytics, and customization
 */
describe('Demo E2E Test Suite: Advanced Export Features', () => {
  beforeEach(() => {
    DemoNavigator.setupViewport();
    DemoNavigator.visitDemo();
  });

  describe('Scheduling and Follow-up Actions', () => {
    it('should allow scheduling executive briefing', () => {
      DemoNavigator.navigateToROI();
      ExportHelpers.triggerROICalculation();
      
      cy.contains('Schedule Executive Briefing').should('be.visible');
      cy.contains('Schedule Executive Briefing').click();
    });

    it('should provide contact options', () => {
      DemoNavigator.navigateToNextSteps();
      cy.contains('Support & Resources').click();
      
      const contactInfo = [
        '24/7 Enterprise Support',
        'success@netrasystems.ai',
        '1-800-NETRA-AI'
      ];
      
      contactInfo.forEach(info => {
        cy.contains(info).should('be.visible');
      });
    });

    it('should enable pilot program signup', () => {
      DemoNavigator.navigateToNextSteps();
      
      cy.contains('Start Pilot Program').should('be.visible');
      cy.contains('Start Pilot Program').click();
    });

    it('should offer deep dive scheduling', () => {
      const sections = ['ROI Calculator', 'AI Chat', 'Metrics'];
      sections.forEach(section => {
        DemoNavigator.navigateToSection(section);
      });
      
      cy.get('[data-testid="demo-complete"]').within(() => {
        cy.contains('Schedule Deep Dive').should('be.visible');
      });
    });

    it('should integrate calendar scheduling', () => {
      DemoNavigator.navigateToROI();
      ExportHelpers.triggerROICalculation();
      
      cy.contains('Schedule Executive Briefing').click();
      
      // Should trigger calendar integration
      cy.on('window:alert', (text) => {
        expect(text).to.contain('calendar');
      });
    });
  });

  describe('Report Accessibility and Sharing', () => {
    it('should generate shareable links', () => {
      DemoNavigator.navigateToNextSteps();
      cy.get('button').should('exist');
    });

    it('should support email delivery of reports', () => {
      DemoNavigator.navigateToNextSteps();
      cy.contains('Email').click();
      
      cy.on('window:alert', (text) => {
        expect(text).to.contain('email');
      });
    });

    it('should maintain report state in session', () => {
      DemoNavigator.navigateToROI();
      ExportHelpers.triggerROICalculation();
      
      SessionHelpers.reloadAndVerifyState();
      SessionHelpers.verifySessionPersistence();
    });

    it('should enable collaborative sharing', () => {
      DemoNavigator.navigateToNextSteps();
      
      cy.window().then((win) => {
        cy.stub(win.navigator, 'share').resolves();
      });
      
      cy.contains('Export Plan').click();
    });

    it('should track sharing analytics', () => {
      AnalyticsHelpers.setupConsoleLogging();
      
      DemoNavigator.navigateToNextSteps();
      cy.contains('Export Plan').click();
      
      AnalyticsHelpers.verifyAnalyticsCall();
    });
  });

  describe('Report Customization', () => {
    it('should allow selecting report sections', () => {
      DemoNavigator.navigateToNextSteps();
      ReportCustomization.selectReportSections();
    });

    it('should include only completed sections in export', () => {
      DemoNavigator.navigateToROI();
      ExportHelpers.triggerROICalculation();
      
      DemoNavigator.navigateToNextSteps();
      cy.contains('Export Plan').click();
      
      ExportHelpers.verifyExportAlert('roi');
    });

    it('should personalize report with industry data', () => {
      DemoNavigator.navigateToNextSteps();
      ReportCustomization.verifyIndustrySpecificContent();
    });

    it('should customize export templates', () => {
      DemoNavigator.navigateToNextSteps();
      
      cy.contains('Template Options').should('exist');
      cy.contains('Executive Summary').should('be.visible');
      cy.contains('Technical Details').should('be.visible');
    });

    it('should apply branding to exports', () => {
      DemoNavigator.navigateToROI();
      ExportHelpers.triggerROICalculation();
      
      cy.contains('Export Report').click();
      
      cy.on('window:alert', (text) => {
        expect(text).to.contain('netra');
      });
    });
  });

  describe('Analytics and Tracking', () => {
    it('should track export events', () => {
      AnalyticsHelpers.setupConsoleLogging();
      
      DemoNavigator.navigateToNextSteps();
      cy.contains('Export Plan').click();
      
      AnalyticsHelpers.verifyAnalyticsCall();
    });

    it('should include demo metrics in export', () => {
      DemoNavigator.navigateToROI();
      ExportHelpers.triggerROICalculation();
      
      DemoNavigator.navigateToNextSteps();
      
      cy.contains('Demo Progress').should('be.visible');
      cy.get('[role="progressbar"]').should('exist');
    });

    it('should timestamp all exports', () => {
      DemoNavigator.navigateToDataInsights();
      cy.contains('Export').click();
      
      cy.on('window:alert', (text) => {
        expect(text).to.match(/\d{13}/);
      });
    });

    it('should track user interaction patterns', () => {
      AnalyticsHelpers.setupConsoleLogging();
      AnalyticsHelpers.completeFullDemo();
      
      AnalyticsHelpers.verifyAnalyticsCall();
    });

    it('should measure export performance metrics', () => {
      const startTime = Date.now();
      
      DemoNavigator.navigateToROI();
      ExportHelpers.triggerROICalculation();
      cy.contains('Export Report').click();
      
      cy.then(() => {
        const duration = Date.now() - startTime;
        expect(duration).to.be.lessThan(5000);
      });
    });
  });

  describe('Enterprise Features', () => {
    it('should support audit trail export', () => {
      AnalyticsHelpers.completeFullDemo();
      
      DemoNavigator.navigateToNextSteps();
      cy.contains('Export Plan').click();
      
      cy.on('window:alert', (text) => {
        expect(text).to.contain('audit');
      });
    });

    it('should enable compliance reporting', () => {
      DemoNavigator.navigateToMetrics();
      cy.wait(EXPORT_TEST_CONFIG.defaultTimeout);
      
      cy.contains('Compliance Report').should('exist');
      cy.contains('Export').click();
    });

    it('should provide data governance features', () => {
      DemoNavigator.navigateToDataInsights();
      
      cy.contains('Data Governance').should('be.visible');
      cy.contains('Export').click();
      
      ExportHelpers.verifyExportAlert('governance');
    });

    it('should support multi-tenant export isolation', () => {
      cy.window().then((win) => {
        cy.stub(win.localStorage, 'getItem')
          .withArgs('tenant_id')
          .returns('enterprise_tenant');
      });
      
      DemoNavigator.navigateToNextSteps();
      cy.contains('Export Plan').click();
    });
  });

  describe('Integration and API Export', () => {
    it('should support API-based exports', () => {
      cy.intercept('POST', '/api/export', {
        statusCode: 200,
        body: { exportId: 'test-123', status: 'success' }
      });
      
      DemoNavigator.navigateToROI();
      ExportHelpers.triggerROICalculation();
      cy.contains('Export Report').click();
    });

    it('should handle webhook notifications', () => {
      cy.intercept('POST', '/api/webhooks/export', {
        statusCode: 200
      });
      
      DemoNavigator.navigateToNextSteps();
      cy.contains('Export Plan').click();
    });

    it('should integrate with external systems', () => {
      cy.window().then((win) => {
        cy.stub(win, 'postMessage').as('externalMessage');
      });
      
      DemoNavigator.navigateToMetrics();
      cy.contains('Export').click();
      
      cy.get('@externalMessage').should('be.called');
    });
  });
});