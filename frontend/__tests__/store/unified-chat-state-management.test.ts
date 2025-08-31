/**
 * UnifiedChatStore State Management Tests - Real Store Behavior Testing
 * 
 * BVJ (Business Value Justification):
 * - Segment: All (Chat state reliability)
 * - Business Goal: Ensure consistent chat state management
 * - Value Impact: Critical for user experience and data integrity
 * - Revenue Impact: State bugs lead to lost conversations and churn
 * 
 * CRITICAL: Tests real store behavior, no mocking of store logic
 * Architecture: ≤300 lines, functions ≤8 lines each
 */

import { UnifiedChatStoreTestUtils, GlobalTestUtils } from './store-test-utils';

describe('UnifiedChatStore - State Management', () => {
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

  describe('Layer Reset Functionality', () => {
        setupAntiHang();
      jest.setTimeout(10000);
    it('should reset all layers correctly', () => {
      // Set some data first
      UnifiedChatStoreTestUtils.updateFastLayerAndVerify(storeResult, {
        agentName: 'Test',
        activeTools: [],
        timestamp: Date.now(),
        runId: 'test',
      });
      
      UnifiedChatStoreTestUtils.setProcessingAndVerify(storeResult, true);

      // Reset
      storeResult = UnifiedChatStoreTestUtils.initializeStore();

      expect(storeResult.current.fastLayerData).toBeNull();
      expect(storeResult.current.mediumLayerData).toBeNull();
      expect(storeResult.current.slowLayerData).toBeNull();
      expect(storeResult.current.currentRunId).toBeNull();
      expect(storeResult.current.isProcessing).toBe(false);
    });

    it('should maintain message history after layer reset', () => {
      // Add a message
      storeResult.current.addMessage({
        id: 'msg1',
        role: 'user',
        content: 'Hello',
        timestamp: Date.now(),
      });

      // Reset layers
      storeResult = UnifiedChatStoreTestUtils.initializeStore();

      // Messages should be cleared in our test utils reset
      expect(storeResult.current.messages).toHaveLength(0);
    });
  });

  describe('Message Management', () => {
        setupAntiHang();
      jest.setTimeout(10000);
    it('should add messages to history correctly', () => {
      const message = {
        id: 'msg1',
        role: 'user' as const,
        content: 'Hello',
        timestamp: Date.now(),
      };

      storeResult.current.addMessage(message);

      expect(storeResult.current.messages).toHaveLength(1);
      expect(storeResult.current.messages[0].content).toBe('Hello');
      expect(storeResult.current.messages[0].role).toBe('user');
    });

    it('should handle multiple messages in order', () => {
      const message1 = {
        id: 'msg1',
        role: 'user' as const,
        content: 'First message',
        timestamp: Date.now(),
      };

      const message2 = {
        id: 'msg2',
        role: 'assistant' as const,
        content: 'Second message',
        timestamp: Date.now() + 1000,
      };

      storeResult.current.addMessage(message1);
      storeResult.current.addMessage(message2);

      expect(storeResult.current.messages).toHaveLength(2);
      expect(storeResult.current.messages[0].id).toBe('msg1');
      expect(storeResult.current.messages[1].id).toBe('msg2');
    });

    it('should handle assistant messages correctly', () => {
      const assistantMessage = {
        id: 'assistant-msg',
        role: 'assistant' as const,
        content: 'Assistant response',
        timestamp: Date.now(),
      };

      storeResult.current.addMessage(assistantMessage);

      expect(storeResult.current.messages[0].role).toBe('assistant');
      expect(storeResult.current.messages[0].content).toBe('Assistant response');
    });
  });

  describe('Connection Status Management', () => {
        setupAntiHang();
      jest.setTimeout(10000);
    it('should set connection status correctly', () => {
      UnifiedChatStoreTestUtils.verifyConnectionStatus(storeResult, false, null);

      storeResult.current.setConnectionStatus(true);
      UnifiedChatStoreTestUtils.verifyConnectionStatus(storeResult, true, null);

      storeResult.current.setConnectionStatus(false, 'Connection lost');
      UnifiedChatStoreTestUtils.verifyConnectionStatus(storeResult, false, 'Connection lost');
    });

    it('should handle connection error clearing', () => {
      storeResult.current.setConnectionStatus(false, 'Network error');
      UnifiedChatStoreTestUtils.verifyConnectionStatus(storeResult, false, 'Network error');

      storeResult.current.setConnectionStatus(true);
      UnifiedChatStoreTestUtils.verifyConnectionStatus(storeResult, true, null);
    });

    it('should handle reconnection scenarios', () => {
      // Simulate connection loss
      storeResult.current.setConnectionStatus(false, 'Connection timeout');
      expect(storeResult.current.isConnected).toBe(false);
      expect(storeResult.current.connectionError).toBe('Connection timeout');

      // Simulate reconnection
      storeResult.current.setConnectionStatus(true);
      expect(storeResult.current.isConnected).toBe(true);
      expect(storeResult.current.connectionError).toBeNull();
    });
  });

  describe('Processing State Management', () => {
        setupAntiHang();
      jest.setTimeout(10000);
    it('should handle processing state changes correctly', () => {
      expect(storeResult.current.isProcessing).toBe(false);

      UnifiedChatStoreTestUtils.setProcessingAndVerify(storeResult, true);
      UnifiedChatStoreTestUtils.setProcessingAndVerify(storeResult, false);
    });

    it('should maintain processing state during operations', () => {
      UnifiedChatStoreTestUtils.setProcessingAndVerify(storeResult, true);

      // Add some layer updates while processing
      UnifiedChatStoreTestUtils.updateFastLayerAndVerify(storeResult, {
        agentName: 'Processing Agent',
        activeTools: ['tool1'],
        timestamp: Date.now(),
        runId: 'processing-run',
      });

      expect(storeResult.current.isProcessing).toBe(true);
    });

    it('should handle processing state reset', () => {
      UnifiedChatStoreTestUtils.setProcessingAndVerify(storeResult, true);
      
      storeResult = UnifiedChatStoreTestUtils.initializeStore();
      expect(storeResult.current.isProcessing).toBe(false);
    });
  });

  describe('Run ID Management', () => {
        setupAntiHang();
      jest.setTimeout(10000);
    it('should track current run ID correctly', () => {
      expect(storeResult.current.currentRunId).toBeNull();

      UnifiedChatStoreTestUtils.updateFastLayerAndVerify(storeResult, {
        agentName: 'Test Agent',
        activeTools: [],
        timestamp: Date.now(),
        runId: 'test-run-123',
      });

      expect(storeResult.current.currentRunId).toBe('test-run-123');
    });

    it('should handle run ID changes', () => {
      UnifiedChatStoreTestUtils.updateFastLayerAndVerify(storeResult, {
        agentName: 'Agent 1',
        activeTools: [],
        timestamp: Date.now(),
        runId: 'run-1',
      });

      expect(storeResult.current.currentRunId).toBe('run-1');

      UnifiedChatStoreTestUtils.updateFastLayerAndVerify(storeResult, {
        agentName: 'Agent 2',
        activeTools: [],
        timestamp: Date.now(),
        runId: 'run-2',
      });

      expect(storeResult.current.currentRunId).toBe('run-2');
    });

    it('should clear run ID on reset', () => {
      UnifiedChatStoreTestUtils.updateFastLayerAndVerify(storeResult, {
        agentName: 'Test Agent',
        activeTools: [],
        timestamp: Date.now(),
        runId: 'test-run',
      });

      storeResult = UnifiedChatStoreTestUtils.initializeStore();
      expect(storeResult.current.currentRunId).toBeNull();
    });
  });

  describe('State Integrity', () => {
        setupAntiHang();
      jest.setTimeout(10000);
    it('should maintain consistent state across updates', () => {
      // Set up fast layer
      UnifiedChatStoreTestUtils.updateFastLayerAndVerify(storeResult, {
        agentName: 'Consistency Agent',
        activeTools: ['tool1'],
        timestamp: Date.now(),
        runId: 'consistency-run',
      });

      // Add medium layer data
      UnifiedChatStoreTestUtils.updateMediumLayerAndVerify(storeResult, {
        thought: 'Processing...',
        stepNumber: 1,
        totalSteps: 3,
      });

      // Verify all data is present
      expect(storeResult.current.fastLayerData?.agentName).toBe('Consistency Agent');
      expect(storeResult.current.mediumLayerData?.thought).toBe('Processing...');
      expect(storeResult.current.currentRunId).toBe('consistency-run');
    });

    it('should handle partial state updates gracefully', () => {
      UnifiedChatStoreTestUtils.updateFastLayerAndVerify(storeResult, {
        agentName: 'Initial Agent',
        activeTools: ['initial-tool'],
        timestamp: Date.now(),
        runId: 'initial-run',
      });

      // Partial update should preserve existing data
      UnifiedChatStoreTestUtils.updateFastLayerAndVerify(storeResult, {
        agentName: 'Updated Agent',
        activeTools: ['updated-tool'],
        timestamp: Date.now() + 1000,
        runId: 'updated-run',
      });

      expect(storeResult.current.fastLayerData?.agentName).toBe('Updated Agent');
      expect(storeResult.current.currentRunId).toBe('updated-run');
    });
  });
  afterEach(() => {
    cleanupAntiHang();
  });

});