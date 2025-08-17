/// <reference types="cypress" />

import { 
  SyntheticDataTestUtils, 
  ConfigurationFactory, 
  GenerationActions, 
  UIHelpers, 
  TestData 
} from './synthetic-data-test-utils'

/**
 * Monitoring and integration tests for synthetic data generator
 * BVJ: Growth segment - enterprise monitoring and integration capabilities
 */
describe('SyntheticDataGenerator - Monitoring and Integration Tests', () => {
  beforeEach(() => {
    SyntheticDataTestUtils.setupViewport()
    SyntheticDataTestUtils.visitComponent()
  })

  describe('Advanced Monitoring and Alerts', () => {
    beforeEach(() => {
      ConfigurationFactory.setTraceCount(TestData.smallDataset)
      GenerationActions.startGeneration()
    })

    it('should display real-time performance metrics', () => {
      UIHelpers.verifyElementVisible('performance-dashboard')
      UIHelpers.verifyTextContent('CPU Usage')
      UIHelpers.verifyTextContent('Memory Usage')
    })

    it('should show generation progress analytics', () => {
      UIHelpers.verifyElementVisible('progress-analytics')
      cy.get('[data-testid="eta-display"]').should('contain', 'ETA:')
    })

    it('should display resource utilization graphs', () => {
      UIHelpers.verifyElementVisible('resource-graphs')
      UIHelpers.verifyElementVisible('cpu-graph')
      UIHelpers.verifyElementVisible('memory-graph')
    })

    it('should configure performance alerts', () => {
      UIHelpers.clickElement('alert-settings')
      UIHelpers.typeInField('cpuThreshold', '80')
      UIHelpers.typeInField('memoryThreshold', '90')
      cy.get('input[name="enableAlerts"]').check()
    })

    it('should show throughput monitoring', () => {
      UIHelpers.verifyElementVisible('throughput-monitor')
      cy.get('[data-testid="current-throughput"]').should('contain', 'req/s')
    })

    it('should display error rate tracking', () => {
      UIHelpers.verifyElementVisible('error-rate-monitor')
      cy.get('[data-testid="current-error-rate"]').should('contain', '%')
    })
  })

  describe('Integration Settings', () => {
    beforeEach(() => {
      UIHelpers.clickElement('advanced-toggle')
      UIHelpers.clickElement('integration-tab')
    })

    it('should configure database connection settings', () => {
      UIHelpers.typeInField('dbHost', 'localhost')
      UIHelpers.typeInField('dbPort', '5432')
      UIHelpers.typeInField('dbName', 'synthetic_data')
    })

    it('should set authentication credentials', () => {
      UIHelpers.typeInField('username', 'admin')
      UIHelpers.typeInField('password', 'password123')
      cy.get('input[name="useSSL"]').check()
    })

    it('should configure external API integration', () => {
      UIHelpers.typeInField('apiEndpoint', 'https://api.example.com')
      UIHelpers.typeInField('apiKey', 'sk-test-123')
    })

    it('should test connection settings', () => {
      UIHelpers.clickElement('test-connection')
      UIHelpers.verifyTextContent('Connection successful')
    })

    it('should configure webhook notifications', () => {
      UIHelpers.typeInField('webhookUrl', 'https://hooks.example.com/webhook')
      cy.get('input[name="enableWebhooks"]').check()
    })

    it('should set up email notifications', () => {
      UIHelpers.typeInField('smtpServer', 'smtp.example.com')
      UIHelpers.typeInField('emailRecipients', 'admin@example.com')
      cy.get('input[name="enableEmail"]').check()
    })
  })

  describe('Bulk Operations and Scheduling', () => {
    beforeEach(() => {
      UIHelpers.clickElement('advanced-toggle')
      UIHelpers.clickElement('scheduling-tab')
    })

    it('should configure scheduled generation', () => {
      cy.get('input[name="enableScheduling"]').check()
      UIHelpers.typeInField('scheduleTime', '02:00')
      cy.get('select[name="frequency"]').select('daily')
    })

    it('should set bulk generation parameters', () => {
      cy.get('input[name="bulkMode"]').check()
      UIHelpers.typeInField('batchCount', '10')
      UIHelpers.typeInField('batchInterval', '5')
    })

    it('should configure automatic cleanup', () => {
      cy.get('input[name="autoCleanup"]').check()
      UIHelpers.typeInField('retentionDays', '30')
    })

    it('should set concurrent job limits', () => {
      UIHelpers.typeInField('maxConcurrentJobs', '3')
      cy.get('input[name="queueManagement"]').check()
    })

    it('should configure retry policies', () => {
      UIHelpers.typeInField('maxRetries', '3')
      UIHelpers.typeInField('retryDelay', '60')
      cy.get('select[name="retryStrategy"]').select('exponential')
    })
  })

  describe('System Health Monitoring', () => {
    it('should display system status dashboard', () => {
      UIHelpers.clickElement('health-dashboard')
      UIHelpers.verifyElementVisible('system-status')
    })

    it('should show database connectivity status', () => {
      UIHelpers.clickElement('health-dashboard')
      UIHelpers.verifyTextContent('Database Connection')
      cy.get('[data-testid="db-status"]').should('contain', 'Connected')
    })

    it('should monitor disk space usage', () => {
      UIHelpers.clickElement('health-dashboard')
      UIHelpers.verifyTextContent('Disk Space')
      cy.get('[data-testid="disk-usage"]').should('contain', '%')
    })

    it('should track service uptime', () => {
      UIHelpers.clickElement('health-dashboard')
      UIHelpers.verifyTextContent('Uptime')
      cy.get('[data-testid="uptime-display"]').should('contain', 'days')
    })

    it('should show API response times', () => {
      UIHelpers.clickElement('health-dashboard')
      UIHelpers.verifyTextContent('API Response Time')
      cy.get('[data-testid="response-time"]').should('contain', 'ms')
    })
  })

  describe('Audit and Compliance Features', () => {
    beforeEach(() => {
      UIHelpers.clickElement('advanced-toggle')
      UIHelpers.clickElement('audit-tab')
    })

    it('should enable audit logging', () => {
      cy.get('input[name="enableAuditLog"]').check()
      UIHelpers.verifyTextContent('Audit logging enabled')
    })

    it('should configure compliance reporting', () => {
      cy.get('select[name="complianceStandard"]').select('GDPR')
      cy.get('input[name="enableCompliance"]').check()
    })

    it('should set data retention policies', () => {
      UIHelpers.typeInField('dataRetentionDays', '90')
      cy.get('input[name="autoDelete"]').check()
    })

    it('should configure access controls', () => {
      cy.get('select[name="accessLevel"]').select('restricted')
      UIHelpers.typeInField('allowedUsers', 'admin,operator')
    })

    it('should enable encryption settings', () => {
      cy.get('input[name="encryptAtRest"]').check()
      cy.get('input[name="encryptInTransit"]').check()
      cy.get('select[name="encryptionAlgorithm"]').select('AES-256')
    })
  })

  describe('Performance Optimization', () => {
    beforeEach(() => {
      UIHelpers.clickElement('advanced-toggle')
      UIHelpers.clickElement('optimization-tab')
    })

    it('should configure memory optimization', () => {
      cy.get('input[name="enableMemoryOptimization"]').check()
      UIHelpers.typeInField('memoryLimit', '4096')
    })

    it('should set connection pooling', () => {
      cy.get('input[name="enableConnectionPooling"]').check()
      UIHelpers.typeInField('poolSize', '20')
    })

    it('should configure caching strategies', () => {
      cy.get('select[name="cacheStrategy"]').select('LRU')
      UIHelpers.typeInField('cacheSize', '1000')
    })

    it('should enable query optimization', () => {
      cy.get('input[name="enableQueryOptimization"]').check()
      cy.get('input[name="enableIndexing"]').check()
    })
  })

  describe('Error Handling and Recovery', () => {
    it('should configure error recovery settings', () => {
      UIHelpers.clickElement('advanced-toggle')
      UIHelpers.clickElement('error-handling-tab')
      cy.get('input[name="enableAutoRecovery"]').check()
    })

    it('should set failure thresholds', () => {
      UIHelpers.clickElement('error-handling-tab')
      UIHelpers.typeInField('failureThreshold', '10')
      UIHelpers.typeInField('recoveryTimeout', '300')
    })

    it('should configure circuit breaker', () => {
      UIHelpers.clickElement('error-handling-tab')
      cy.get('input[name="enableCircuitBreaker"]').check()
      UIHelpers.typeInField('circuitBreakerThreshold', '5')
    })
  })
})