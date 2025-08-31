/**
 * UnifiedChatStore Layer Updates Tests - Real Store Behavior Testing
 * 
 * BVJ (Business Value Justification):
 * - Segment: All (Real-time chat experience)
 * - Business Goal: Ensure smooth multi-layer chat experience
 * - Value Impact: Critical for user engagement and retention
 * - Revenue Impact: Poor chat UX leads to churn, impacts all tiers
 * 
 * CRITICAL: Tests real store behavior, no mocking of store logic
 * Architecture: ≤300 lines, functions ≤8 lines each
 */

import { UnifiedChatStoreTestUtils, GlobalTestUtils } from './store-test-utils';

describe('UnifiedChatStore - Layer Updates', () => {
      setupAntiHang();
    jest.setTimeout(10000);
  let storeResult: ReturnType<typeof UnifiedChatStoreTestUtils.initializeStore>;

  // Setup test environment (≤8 lines)
  beforeAll(() => {
    GlobalTestUtils.setupStoreTestEnvironment();
  });

  // Reset store before each test (≤8 lines)
  beforeEach(() => {
    storeResult = UnifiedChatStoreTestUtils.initializeStore();
  });

  // Cleanup after all tests (≤8 lines)
  afterAll(() => {
    GlobalTestUtils.cleanupStoreTestEnvironment();
  });

  describe('Fast Layer Updates', () => {
        setupAntiHang();
      jest.setTimeout(10000);
    it('should update fast layer data correctly', () => {
      const fastLayerData = {
        agentName: 'Test Agent',
        activeTools: ['tool1'],
        timestamp: 123456,
        runId: 'test-run',
      };

      UnifiedChatStoreTestUtils.updateFastLayerAndVerify(storeResult, fastLayerData);
    });

    it('should handle multiple fast layer updates', () => {
      const firstUpdate = {
        agentName: 'First Agent',
        activeTools: ['tool1'],
        timestamp: 123456,
        runId: 'run-1',
      };

      const secondUpdate = {
        agentName: 'Second Agent', 
        activeTools: ['tool2', 'tool3'],
        timestamp: 123457,
        runId: 'run-2',
      };

      UnifiedChatStoreTestUtils.updateFastLayerAndVerify(storeResult, firstUpdate);
      UnifiedChatStoreTestUtils.updateFastLayerAndVerify(storeResult, secondUpdate);
    });

    it('should update active tools correctly', () => {
      const initialData = {
        agentName: 'Test Agent',
        activeTools: ['tool1'],
        timestamp: 123456,
        runId: 'test-run',
      };

      const updatedData = {
        ...initialData,
        activeTools: ['tool1', 'tool2', 'tool3'],
      };

      UnifiedChatStoreTestUtils.updateFastLayerAndVerify(storeResult, initialData);
      UnifiedChatStoreTestUtils.updateFastLayerAndVerify(storeResult, updatedData);
    });
  });

  describe('Medium Layer Updates', () => {
        setupAntiHang();
      jest.setTimeout(10000);
    it('should update medium layer data and accumulate partial content', () => {
      const firstUpdate = {
        thought: 'Thinking...',
        partialContent: 'First part',
        stepNumber: 1,
        totalSteps: 3,
        agentName: 'Test Agent',
      };

      UnifiedChatStoreTestUtils.updateMediumLayerAndVerify(storeResult, firstUpdate);
      expect(storeResult.current.mediumLayerData?.partialContent).toBe('First part');

      const secondUpdate = {
        partialContent: 'First partSecond part',
      };

      UnifiedChatStoreTestUtils.updateMediumLayerAndVerify(storeResult, secondUpdate);
      expect(storeResult.current.mediumLayerData?.partialContent).toBe('First partSecond part');
    });

    it('should handle thought updates correctly', () => {
      const thoughtUpdate = {
        thought: 'Analyzing patterns...',
        stepNumber: 2,
        totalSteps: 5,
        agentName: 'Analysis Agent',
      };

      UnifiedChatStoreTestUtils.updateMediumLayerAndVerify(storeResult, thoughtUpdate);
      expect(storeResult.current.mediumLayerData?.thought).toBe('Analyzing patterns...');
      expect(storeResult.current.mediumLayerData?.stepNumber).toBe(2);
      expect(storeResult.current.mediumLayerData?.totalSteps).toBe(5);
    });

    it('should preserve existing data when partially updating', () => {
      const initialUpdate = {
        thought: 'Initial thought',
        partialContent: 'Initial content',
        stepNumber: 1,
        totalSteps: 3,
        agentName: 'Test Agent',
      };

      const partialUpdate = {
        stepNumber: 2,
      };

      UnifiedChatStoreTestUtils.updateMediumLayerAndVerify(storeResult, initialUpdate);
      UnifiedChatStoreTestUtils.updateMediumLayerAndVerify(storeResult, partialUpdate);
      
      expect(storeResult.current.mediumLayerData?.thought).toBe('Initial thought');
      expect(storeResult.current.mediumLayerData?.stepNumber).toBe(2);
      expect(storeResult.current.mediumLayerData?.agentName).toBe('Test Agent');
    });
  });

  describe('Slow Layer Updates', () => {
        setupAntiHang();
      jest.setTimeout(10000);
    it('should update slow layer data and accumulate completed agents', () => {
      const firstAgent = {
        completedAgents: [{
          agentName: 'Agent1',
          duration: 1000,
          result: {},
          metrics: {},
        }],
      };

      UnifiedChatStoreTestUtils.updateMediumLayerAndVerify(storeResult, firstAgent);
      expect(storeResult.current.slowLayerData?.completedAgents).toHaveLength(1);

      const secondAgent = {
        completedAgents: [{
          agentName: 'Agent2',
          duration: 2000,
          result: {},
          metrics: {},
        }],
      };

      UnifiedChatStoreTestUtils.updateMediumLayerAndVerify(storeResult, secondAgent);
      expect(storeResult.current.slowLayerData?.completedAgents).toHaveLength(2);
    });

    it('should handle final report data correctly', () => {
      const finalReportData = {
        finalReport: {
          summary: 'Complete analysis',
          recommendations: [{
            id: 'rec1',
            title: 'Enable caching',
            description: 'Implement Redis caching',
            impact: 'high' as const,
            effort: 'low' as const,
            category: 'performance' as const,
          }],
        },
        totalDuration: 10000,
      };

      UnifiedChatStoreTestUtils.updateMediumLayerAndVerify(storeResult, finalReportData);
      expect(storeResult.current.slowLayerData?.finalReport).toBeDefined();
      expect(storeResult.current.slowLayerData?.totalDuration).toBe(10000);
    });

    it('should track agent metrics correctly', () => {
      const metricsUpdate = {
        completedAgents: [{
          agentName: 'Metrics Agent',
          duration: 5000,
          result: { optimization: 'cache' },
          metrics: { tokens: 1500, cost: 0.05 },
        }],
      };

      UnifiedChatStoreTestUtils.updateMediumLayerAndVerify(storeResult, metricsUpdate);
      const agent = storeResult.current.slowLayerData?.completedAgents[0];
      expect(agent?.metrics).toEqual({ tokens: 1500, cost: 0.05 });
      expect(agent?.duration).toBe(5000);
    });
  });

  describe('Layer Reset Functionality', () => {
        setupAntiHang();
      jest.setTimeout(10000);
    it('should reset all layers to null state', () => {
      // Set up some data first
      UnifiedChatStoreTestUtils.updateFastLayerAndVerify(storeResult, {
        agentName: 'Test',
        activeTools: [],
        timestamp: Date.now(),
        runId: 'test',
      });

      UnifiedChatStoreTestUtils.setProcessingAndVerify(storeResult, true);

      // Reset layers
      storeResult = UnifiedChatStoreTestUtils.initializeStore();

      expect(storeResult.current.fastLayerData).toBeNull();
      expect(storeResult.current.mediumLayerData).toBeNull();
      expect(storeResult.current.slowLayerData).toBeNull();
      expect(storeResult.current.currentRunId).toBeNull();
      expect(storeResult.current.isProcessing).toBe(false);
    });

    it('should maintain clean state after reset', () => {
      // Reset and verify clean state
      storeResult = UnifiedChatStoreTestUtils.initializeStore();

      expect(storeResult.current.messages).toHaveLength(0);
      expect(storeResult.current.isConnected).toBe(false);
      expect(storeResult.current.connectionError).toBeNull();
    });
  });
  afterEach(() => {
    cleanupAntiHang();
  });

});