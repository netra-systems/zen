/// <reference types="cypress" />

import { 
  SyntheticDataTestUtils, 
  ConfigurationFactory, 
  UIHelpers, 
  TestData 
} from './synthetic-data-test-utils'

/**
 * Advanced configuration tests for synthetic data generator
 * BVJ: Growth segment - advanced configuration for enterprise customers
 */
describe('SyntheticDataGenerator - Advanced Configuration Tests', () => {
  beforeEach(() => {
    SyntheticDataTestUtils.setupViewport()
    SyntheticDataTestUtils.visitComponent()
    expandAdvancedOptions()
  })

  function expandAdvancedOptions(): void {
    UIHelpers.clickElement('advanced-toggle')
    UIHelpers.verifyElementVisible('advanced-options')
  }

  describe('Advanced Configuration Options', () => {
    it('should show advanced options toggle', () => {
      UIHelpers.verifyElementVisible('advanced-toggle')
    })

    it('should display latency distribution settings', () => {
      UIHelpers.verifyTextContent('Latency Distribution')
      cy.get('input[name="minLatency"]').should('be.visible')
      cy.get('input[name="maxLatency"]').should('be.visible')
    })

    it('should configure custom service names', () => {
      UIHelpers.clickElement('add-service')
      UIHelpers.typeInField('serviceName', 'api-gateway')
      UIHelpers.clickElement('add-service-confirm')
      UIHelpers.verifyTextContent('api-gateway')
    })

    it('should add custom data fields', () => {
      UIHelpers.clickElement('add-field')
      UIHelpers.typeInField('fieldName', 'region')
      cy.get('select[name="fieldType"]').select('string')
      UIHelpers.clickElement('add-field-confirm')
      UIHelpers.verifyTextContent('region')
    })

    it('should configure data distribution parameters', () => {
      cy.get('select[name="distribution"]').select('normal')
      UIHelpers.typeInField('mean', '100')
      UIHelpers.typeInField('stddev', '20')
    })

    it('should set custom error patterns', () => {
      UIHelpers.clickElement('error-patterns')
      cy.get('select[name="errorPattern"]').select('burst')
      UIHelpers.typeInField('errorDuration', '30')
    })

    it('should configure geographic distribution', () => {
      UIHelpers.clickElement('geo-settings')
      cy.get('select[name="regions"]').select('us-east-1')
      UIHelpers.typeInField('latencyOffset', '50')
    })
  })

  describe('Custom Field Configuration', () => {
    it('should add string field type', () => {
      addCustomField('user_agent', 'string', 'Mozilla/5.0')
    })

    it('should add number field type', () => {
      addCustomField('response_size', 'number', '1024')
    })

    it('should add boolean field type', () => {
      addCustomField('is_authenticated', 'boolean', 'true')
    })

    it('should add date field type', () => {
      addCustomField('created_at', 'date', '2024-01-01')
    })

    function addCustomField(name: string, type: string, value: string): void {
      UIHelpers.clickElement('add-field')
      UIHelpers.typeInField('fieldName', name)
      cy.get('select[name="fieldType"]').select(type)
      UIHelpers.typeInField('defaultValue', value)
      UIHelpers.clickElement('add-field-confirm')
      UIHelpers.verifyTextContent(name)
    }
  })

  describe('Data Distribution Patterns', () => {
    it('should configure normal distribution', () => {
      setDistribution('normal', { mean: '100', stddev: '20' })
      verifyDistributionPreview()
    })

    it('should configure exponential distribution', () => {
      setDistribution('exponential', { lambda: '0.1' })
      verifyDistributionPreview()
    })

    it('should configure uniform distribution', () => {
      setDistribution('uniform', { min: '10', max: '100' })
      verifyDistributionPreview()
    })

    function setDistribution(type: string, params: Record<string, string>): void {
      cy.get('select[name="distribution"]').select(type)
      Object.entries(params).forEach(([key, value]) => {
        UIHelpers.typeInField(key, value)
      })
    }

    function verifyDistributionPreview(): void {
      UIHelpers.verifyElementVisible('distribution-preview')
    }
  })

  describe('Workload Pattern Customization', () => {
    it('should create custom workload patterns', () => {
      ConfigurationFactory.setWorkloadPattern('Custom')
      UIHelpers.verifyElementVisible('custom-pattern-editor')
    })

    it('should define time-based load variations', () => {
      ConfigurationFactory.setWorkloadPattern('Custom')
      addLoadPattern('09:00', '100')
      addLoadPattern('12:00', '200')
      addLoadPattern('18:00', '150')
    })

    it('should preview custom pattern graph', () => {
      ConfigurationFactory.setWorkloadPattern('Custom')
      UIHelpers.verifyElementVisible('pattern-graph')
    })

    function addLoadPattern(time: string, load: string): void {
      UIHelpers.clickElement('add-pattern-point')
      UIHelpers.typeInField('time', time)
      UIHelpers.typeInField('load', load)
      UIHelpers.clickElement('add-point-confirm')
    }
  })

  describe('Performance Optimization Settings', () => {
    beforeEach(() => {
      UIHelpers.clickElement('performance-tab')
    })

    it('should configure batch size settings', () => {
      UIHelpers.typeInField('batchSize', '1000')
      UIHelpers.verifyTextContent('Batch processing enabled')
    })

    it('should set memory usage limits', () => {
      UIHelpers.typeInField('maxMemory', '512')
      cy.get('select[name="memoryUnit"]').select('MB')
    })

    it('should configure parallel processing', () => {
      cy.get('input[name="enableParallel"]').check()
      UIHelpers.typeInField('workerCount', '4')
    })

    it('should set disk cache options', () => {
      cy.get('input[name="enableCache"]').check()
      UIHelpers.typeInField('cacheSize', '100')
    })
  })

  describe('Quality Assurance Configuration', () => {
    beforeEach(() => {
      UIHelpers.clickElement('quality-tab')
    })

    it('should configure data validation rules', () => {
      cy.get('input[name="strictValidation"]').check()
      UIHelpers.typeInField('toleranceLevel', '0.01')
    })

    it('should set duplicate detection settings', () => {
      cy.get('input[name="detectDuplicates"]').check()
      cy.get('select[name="duplicateField"]').select('trace_id')
    })

    it('should configure outlier detection', () => {
      cy.get('input[name="detectOutliers"]').check()
      UIHelpers.typeInField('outlierThreshold', '3')
    })

    it('should set data consistency checks', () => {
      cy.get('input[name="consistencyCheck"]').check()
      cy.get('select[name="checkLevel"]').select('strict')
    })
  })

  describe('Export Format Customization', () => {
    beforeEach(() => {
      setupGeneratedDataForExport()
      UIHelpers.clickElement('advanced-export')
    })

    function setupGeneratedDataForExport(): void {
      ConfigurationFactory.setTraceCount(TestData.smallDataset)
      UIHelpers.clickElement('generate-btn')
      cy.wait(3000)
    }

    it('should configure custom CSV format', () => {
      cy.get('select[name="csvDelimiter"]').select('semicolon')
      cy.get('input[name="includeHeaders"]').check()
      cy.get('select[name="dateFormat"]').select('ISO8601')
    })

    it('should set JSON formatting options', () => {
      cy.get('input[name="prettyPrint"]').check()
      cy.get('input[name="compressJson"]').uncheck()
      UIHelpers.typeInField('indentSize', '2')
    })

    it('should configure Parquet compression', () => {
      cy.get('select[name="compression"]').select('snappy')
      cy.get('select[name="encodingType"]').select('plain')
    })
  })
})