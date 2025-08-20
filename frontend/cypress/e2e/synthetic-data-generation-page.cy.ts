/// <reference types="cypress" />

/**
 * Synthetic Data Generation Page E2E Tests - Master Index
 * 
 * This file has been modularized to maintain the 450-line architectural requirement.
 * The original 4725-line test file has been split into focused modules:
 * 
 * Architecture Compliance:
 * - Each module ≤300 lines
 * - Functions ≤8 lines
 * - Single responsibility per module
 * - Reusable page object utilities
 * 
 * Business Value Justification (BVJ):
 * Growth segment - validates data generation UI, improves user experience
 * 
 * Modular Test Structure:
 * 1. utils/synthetic-data-page-object.ts - Reusable page object helpers (241 lines)
 * 2. synthetic-data-basic-functionality.cy.ts - Core functionality (221 lines)
 * 3. synthetic-data-generation-workflow.cy.ts - Generation workflow (261 lines)
 * 4. synthetic-data-advanced-features.cy.ts - Advanced features (254 lines)
 * 5. synthetic-data-quality-assurance.cy.ts - QA tests (256 lines)
 * 
 * Total coverage: All original test scenarios maintained across modular files
 */

import { SyntheticDataPageObject } from './utils/synthetic-data-page-object'

describe('Synthetic Data Generation Page - Master Test Suite', () => {
  /**
   * Smoke test to verify the page loads and basic functionality works
   * For comprehensive testing, run the individual modular test files
   */
  
  beforeEach(() => {
    SyntheticDataPageObject.visitPage()
  })

  describe('Smoke Tests - Core Functionality', () => {
    it('should load page and display main components', () => {
      SyntheticDataPageObject.verifyPageLoad()
      cy.get(SyntheticDataPageObject.selectors.page).should('be.visible')
      cy.contains('Configuration').should('be.visible')
    })

    it('should have default configuration values', () => {
      SyntheticDataPageObject.verifyDefaultValues()
    })

    it('should allow basic parameter updates', () => {
      SyntheticDataPageObject.setTraceCount('2000')
      cy.get(SyntheticDataPageObject.selectors.tracesInput)
        .should('have.value', '2000')
    })

    it('should support pattern selection', () => {
      SyntheticDataPageObject.selectWorkloadPattern('Burst')
      SyntheticDataPageObject.verifyPatternSelected('Burst')
    })

    it('should have generate button available', () => {
      cy.get(SyntheticDataPageObject.selectors.generateButton)
        .should('be.visible')
    })
  })

  describe('Modular Test Files Reference', () => {
    it('should reference basic functionality tests', () => {
      // See: synthetic-data-basic-functionality.cy.ts
      // Tests: Page load, configuration, patterns, table management
      cy.log('Basic functionality tests: synthetic-data-basic-functionality.cy.ts')
    })

    it('should reference generation workflow tests', () => {
      // See: synthetic-data-generation-workflow.cy.ts
      // Tests: Generation process, preview, validation, export
      cy.log('Workflow tests: synthetic-data-generation-workflow.cy.ts')
    })

    it('should reference advanced features tests', () => {
      // See: synthetic-data-advanced-features.cy.ts
      // Tests: Advanced config, monitoring, history, analytics
      cy.log('Advanced features: synthetic-data-advanced-features.cy.ts')
    })

    it('should reference quality assurance tests', () => {
      // See: synthetic-data-quality-assurance.cy.ts
      // Tests: Mobile, performance, accessibility, security
      cy.log('Quality assurance: synthetic-data-quality-assurance.cy.ts')
    })

    it('should reference page object utilities', () => {
      // See: utils/synthetic-data-page-object.ts
      // Utilities: Reusable selectors, actions, validation helpers
      cy.log('Page object utilities: utils/synthetic-data-page-object.ts')
    })
  })
})

/**
 * Test Execution Guide:
 * 
 * Run all modular tests:
 * cypress run --spec "cypress/e2e/synthetic-data-*.cy.ts"
 * 
 * Run specific modules:
 * cypress run --spec "cypress/e2e/synthetic-data-basic-functionality.cy.ts"
 * cypress run --spec "cypress/e2e/synthetic-data-generation-workflow.cy.ts"
 * cypress run --spec "cypress/e2e/synthetic-data-advanced-features.cy.ts"
 * cypress run --spec "cypress/e2e/synthetic-data-quality-assurance.cy.ts"
 * 
 * Run smoke tests only:
 * cypress run --spec "cypress/e2e/synthetic-data-generation-page.cy.ts"
 */