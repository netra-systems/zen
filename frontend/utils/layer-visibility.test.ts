// Tests for layer visibility fixes
// Verifies that layer visibility issues are resolved

import { calculateEnhancedLayerVisibility } from './layer-visibility-manager';
import type { FastLayerData, MediumLayerData, SlowLayerData } from '@/types/layer-types';

describe('Layer Visibility Fixes', () => {
  
  // Fix 1: FastLayer should persist when tools are active, even when isProcessing becomes false
  describe('FastLayer Tool Persistence Fix', () => {
    test('should show FastLayer when tools are active, even if not processing', () => {
      const fastLayerData: FastLayerData = {
        agentName: 'DataAgent',
        activeTools: ['database_query'],
        toolStatuses: [{
          name: 'database_query',
          startTime: Date.now() - 5000, // 5 seconds ago
          isActive: true
        }],
        timestamp: Date.now(),
        runId: 'test-run'
      };

      const result = calculateEnhancedLayerVisibility({
        fastLayerData,
        mediumLayerData: null,
        slowLayerData: null,
        isProcessing: false // Not processing but should still show
      });

      expect(result.showFastLayer).toBe(true);
      expect(result.fastLayerReason).toBe('active_tools');
    });

    test('should persist FastLayer for recently active tools', () => {
      const fastLayerData: FastLayerData = {
        agentName: 'DataAgent',
        activeTools: [],
        toolStatuses: [{
          name: 'database_query',
          startTime: Date.now() - 10000, // 10 seconds ago
          isActive: false
        }],
        timestamp: Date.now(),
        runId: 'test-run'
      };

      const result = calculateEnhancedLayerVisibility({
        fastLayerData,
        mediumLayerData: null,
        slowLayerData: null,
        isProcessing: false
      });

      expect(result.showFastLayer).toBe(true);
      expect(result.fastLayerReason).toBe('active_tools');
    });
  });

  // Fix 2: MediumLayer should show if partialContent arrives before thought
  describe('MediumLayer Partial Content Fix', () => {
    test('should show MediumLayer with partialContent even without thought', () => {
      const mediumLayerData: MediumLayerData = {
        thought: '', // No thought yet
        partialContent: 'Starting analysis...',
        stepNumber: 0,
        totalSteps: 0,
        agentName: 'DataAgent'
      };

      const result = calculateEnhancedLayerVisibility({
        fastLayerData: null,
        mediumLayerData,
        slowLayerData: null,
        isProcessing: true
      });

      expect(result.showMediumLayer).toBe(true);
      expect(result.mediumLayerReason).toBe('partial_content');
    });

    test('should show MediumLayer with thought', () => {
      const mediumLayerData: MediumLayerData = {
        thought: 'Analyzing the database structure...',
        partialContent: '',
        stepNumber: 1,
        totalSteps: 3,
        agentName: 'DataAgent'
      };

      const result = calculateEnhancedLayerVisibility({
        fastLayerData: null,
        mediumLayerData,
        slowLayerData: null,
        isProcessing: true
      });

      expect(result.showMediumLayer).toBe(true);
      expect(result.mediumLayerReason).toBe('thought');
    });
  });

  // Fix 3: SlowLayer should show with finalReport even when completedAgents is empty
  describe('SlowLayer Final Report Fix', () => {
    test('should show SlowLayer with finalReport even without completedAgents', () => {
      const slowLayerData: SlowLayerData = {
        completedAgents: [], // Empty agents array
        finalReport: {
          report: {
            summary: 'Analysis complete',
            findings: {},
            data: {},
            metadata: {
              generatedAt: new Date().toISOString(),
              version: '1.0'
            }
          },
          recommendations: [],
          actionPlan: [],
          agentMetrics: []
        },
        totalDuration: 5000,
        metrics: {
          startTime: Date.now() - 5000,
          total_duration_ms: 5000,
          total_tokens: 1500,
          total_cost: 0.05
        }
      };

      const result = calculateEnhancedLayerVisibility({
        fastLayerData: null,
        mediumLayerData: null,
        slowLayerData,
        isProcessing: false
      });

      expect(result.showSlowLayer).toBe(true);
      expect(result.slowLayerReason).toBe('final_report');
    });

    test('should show SlowLayer with completedAgents', () => {
      const slowLayerData: SlowLayerData = {
        completedAgents: [{
          agentName: 'DataAgent',
          duration: 3000,
          result: {
            output: 'Query executed',
            artifacts: {},
            status: 'success',
            data: {}
          },
          metrics: {
            executionTime: 3000,
            memoryUsage: 50,
            apiCalls: 5,
            errorCount: 0
          }
        }],
        finalReport: null,
        totalDuration: 3000,
        metrics: {
          startTime: Date.now() - 3000,
          total_duration_ms: 3000,
          total_tokens: 800,
          total_cost: 0.02
        }
      };

      const result = calculateEnhancedLayerVisibility({
        fastLayerData: null,
        mediumLayerData: null,
        slowLayerData,
        isProcessing: false
      });

      expect(result.showSlowLayer).toBe(true);
      expect(result.slowLayerReason).toBe('completed_agents');
    });
  });

  // Fix 4: Layer persistence with previousVisibility
  describe('Layer Persistence Logic', () => {
    test('should persist FastLayer when it was visible and still has data', () => {
      const fastLayerData: FastLayerData = {
        agentName: 'DataAgent',
        activeTools: [],
        toolStatuses: [],
        timestamp: Date.now(),
        runId: 'test-run'
      };

      const previousVisibility = {
        showFastLayer: true,
        showMediumLayer: false,
        showSlowLayer: false,
        fastLayerReason: 'processing',
        mediumLayerReason: 'no_content',
        slowLayerReason: 'no_results'
      };

      const result = calculateEnhancedLayerVisibility({
        fastLayerData,
        mediumLayerData: null,
        slowLayerData: null,
        isProcessing: false,
        previousVisibility
      });

      expect(result.showFastLayer).toBe(true);
      expect(result.fastLayerReason).toBe('agent_data');
    });
  });

  // Edge cases
  describe('Edge Cases', () => {
    test('should handle null data gracefully', () => {
      const result = calculateEnhancedLayerVisibility({
        fastLayerData: null,
        mediumLayerData: null,
        slowLayerData: null,
        isProcessing: false
      });

      expect(result.showFastLayer).toBe(false);
      expect(result.showMediumLayer).toBe(false);
      expect(result.showSlowLayer).toBe(false);
    });

    test('should show FastLayer during processing even without data', () => {
      const result = calculateEnhancedLayerVisibility({
        fastLayerData: null,
        mediumLayerData: null,
        slowLayerData: null,
        isProcessing: true
      });

      expect(result.showFastLayer).toBe(true);
      expect(result.fastLayerReason).toBe('processing');
    });
  });
});