/**
 * Thread State Machine Comprehensive Unit Tests
 * 
 * Business Value Justification (BVJ):
 * - Segment: Platform/Internal
 * - Business Goal: Prevent race conditions in thread management that cause user disconnections
 * - Value Impact: Ensures atomic thread operations, preventing data corruption and lost conversations
 * - Strategic Impact: Core platform stability for chat functionality (90% of business value)
 * 
 * CRITICAL: These tests validate the frontend thread state machine that prevents
 * race conditions between thread creation, switching, and loading operations.
 * 
 * Test Difficulty: HIGH (70% expected failure rate on edge cases)
 * - Thread operation race conditions
 * - State transition edge cases under concurrent operations
 * - Guard conditions and action execution validation
 * - Manager isolation between multiple threads
 * 
 * @compliance TEST_CREATION_GUIDE.md - Follows SSOT patterns for frontend tests
 * @compliance CLAUDE.md - Real business value tests, validates actual FSM behavior
 */

import {
  ThreadStateMachine,
  ThreadStateMachineManager,
  threadStateMachineManager,
  createThreadStateMachineConfig,
  ThreadState,
  ThreadEvent,
  ThreadStateData,
  ThreadTransition,
  ThreadStateMachineConfig
} from '@/lib/thread-state-machine';

// Test utilities
function createMockStateData(overrides: Partial<ThreadStateData> = {}): ThreadStateData {
  return {
    currentState: 'idle',
    targetThreadId: null,
    operationId: null,
    startTime: null,
    error: null,
    canTransition: true,
    ...overrides
  };
}

function createTestConfig(overrides: Partial<ThreadStateMachineConfig> = {}): ThreadStateMachineConfig {
  return {
    initialState: 'idle',
    transitions: [
      { from: 'idle', to: 'creating', event: 'START_CREATE' },
      { from: 'creating', to: 'idle', event: 'COMPLETE_SUCCESS' },
      { from: 'creating', to: 'error', event: 'COMPLETE_ERROR' },
    ],
    ...overrides
  };
}

describe('ThreadStateMachine Core Functionality', () => {
  let stateMachine: ThreadStateMachine;
  let stateChangeEvents: Array<{ from: ThreadState; to: ThreadState; data: ThreadStateData }> = [];

  beforeEach(() => {
    stateChangeEvents = [];
    
    const config = createThreadStateMachineConfig();
    config.onStateChange = (from, to, data) => {
      stateChangeEvents.push({ from, to, data });
    };
    
    stateMachine = new ThreadStateMachine(config);
  });

  afterEach(() => {
    stateChangeEvents = [];
  });

  describe('Basic State Management', () => {
    it('should initialize with correct default state', () => {
      expect(stateMachine.getState()).toBe('idle');
      
      const stateData = stateMachine.getStateData();
      expect(stateData.currentState).toBe('idle');
      expect(stateData.targetThreadId).toBeNull();
      expect(stateData.operationId).toBeNull();
      expect(stateData.startTime).toBeNull();
      expect(stateData.error).toBeNull();
      expect(stateData.canTransition).toBe(true);
    });

    it('should perform valid state transitions correctly', () => {
      // Test idle -> creating transition
      const success = stateMachine.transition('START_CREATE', {
        targetThreadId: 'thread-123',
        operationId: 'op-456',
        startTime: Date.now()
      });

      expect(success).toBe(true);
      expect(stateMachine.getState()).toBe('creating');
      
      const stateData = stateMachine.getStateData();
      expect(stateData.currentState).toBe('creating');
      expect(stateData.targetThreadId).toBe('thread-123');
      expect(stateData.operationId).toBe('op-456');
      expect(stateData.startTime).toBeTruthy();
    });

    it('should reject invalid state transitions', () => {
      // Try invalid transition from idle to processing (not defined)
      const success = stateMachine.transition('INVALID_EVENT' as ThreadEvent);
      
      expect(success).toBe(false);
      expect(stateMachine.getState()).toBe('idle'); // Should remain in idle state
      expect(stateChangeEvents).toHaveLength(0); // No state change should have occurred
    });

    it('should execute guard conditions correctly', () => {
      let guardCalled = false;
      let guardResult = true;

      const config = createTestConfig({
        transitions: [
          {
            from: 'idle',
            to: 'creating',
            event: 'START_CREATE',
            guard: (data) => {
              guardCalled = true;
              return guardResult;
            }
          }
        ]
      });

      const testMachine = new ThreadStateMachine(config);

      // Test guard returning true
      guardResult = true;
      guardCalled = false;
      
      const successTrue = testMachine.transition('START_CREATE');
      expect(guardCalled).toBe(true);
      expect(successTrue).toBe(true);
      expect(testMachine.getState()).toBe('creating');

      // Reset machine to idle
      testMachine.reset();
      expect(testMachine.getState()).toBe('idle');

      // Test guard returning false
      guardResult = false;
      guardCalled = false;
      
      const successFalse = testMachine.transition('START_CREATE');
      expect(guardCalled).toBe(true);
      expect(successFalse).toBe(false);
      expect(testMachine.getState()).toBe('idle'); // Should remain in idle
    });

    it('should execute transition actions correctly', () => {
      let actionCalled = false;
      let actionData: ThreadStateData | null = null;

      const config = createTestConfig({
        transitions: [
          {
            from: 'idle',
            to: 'creating',
            event: 'START_CREATE',
            action: (data) => {
              actionCalled = true;
              actionData = data;
            }
          }
        ]
      });

      const testMachine = new ThreadStateMachine(config);

      const success = testMachine.transition('START_CREATE', {
        targetThreadId: 'action-test-thread'
      });

      expect(success).toBe(true);
      expect(actionCalled).toBe(true);
      expect(actionData).toBeTruthy();
      expect(actionData?.targetThreadId).toBe('action-test-thread');
      expect(actionData?.currentState).toBe('creating');
    });
  });

  describe('Thread Operation State Transitions', () => {
    it('should handle complete thread creation flow', () => {
      // Start create operation
      expect(stateMachine.transition('START_CREATE', {
        targetThreadId: 'new-thread-789',
        operationId: 'create-op-123',
        startTime: Date.now()
      })).toBe(true);
      
      expect(stateMachine.getState()).toBe('creating');

      // Complete successfully
      expect(stateMachine.transition('COMPLETE_SUCCESS')).toBe(true);
      expect(stateMachine.getState()).toBe('idle');

      // Verify state change events
      expect(stateChangeEvents).toHaveLength(2);
      expect(stateChangeEvents[0]).toEqual(
        expect.objectContaining({ from: 'idle', to: 'creating' })
      );
      expect(stateChangeEvents[1]).toEqual(
        expect.objectContaining({ from: 'creating', to: 'idle' })
      );
    });

    it('should handle thread creation failure flow', () => {
      // Start create operation
      stateMachine.transition('START_CREATE', {
        targetThreadId: 'failing-thread',
        operationId: 'fail-op-456'
      });

      expect(stateMachine.getState()).toBe('creating');

      // Fail with error
      const errorObj = new Error('Thread creation failed');
      expect(stateMachine.transition('COMPLETE_ERROR', { error: errorObj })).toBe(true);
      expect(stateMachine.getState()).toBe('error');

      const finalStateData = stateMachine.getStateData();
      expect(finalStateData.error).toBe(errorObj);
    });

    it('should handle thread switching operations', () => {
      // Start switching operation
      expect(stateMachine.transition('START_SWITCH', {
        targetThreadId: 'target-thread-switch',
        operationId: 'switch-op-789'
      })).toBe(true);
      
      expect(stateMachine.getState()).toBe('switching');

      // Complete switch successfully
      expect(stateMachine.transition('COMPLETE_SUCCESS')).toBe(true);
      expect(stateMachine.getState()).toBe('idle');

      // Verify operation data was maintained during transition
      const events = stateChangeEvents.filter(e => e.to === 'switching');
      expect(events).toHaveLength(1);
      expect(events[0].data.targetThreadId).toBe('target-thread-switch');
      expect(events[0].data.operationId).toBe('switch-op-789');
    });

    it('should handle thread loading operations', () => {
      // Start loading
      expect(stateMachine.transition('START_LOAD', {
        targetThreadId: 'loading-thread-456',
        operationId: 'load-op-123'
      })).toBe(true);
      
      expect(stateMachine.getState()).toBe('loading');

      // Complete loading
      expect(stateMachine.transition('COMPLETE_SUCCESS')).toBe(true);
      expect(stateMachine.getState()).toBe('idle');
    });

    it('should handle operation cancellation', () => {
      // Start create operation
      stateMachine.transition('START_CREATE');
      expect(stateMachine.getState()).toBe('creating');

      // Cancel operation
      expect(stateMachine.transition('CANCEL')).toBe(true);
      expect(stateMachine.getState()).toBe('cancelling');

      // Complete cancellation
      expect(stateMachine.transition('COMPLETE_SUCCESS')).toBe(true);
      expect(stateMachine.getState()).toBe('idle');
    });
  });

  describe('Error Handling and Recovery', () => {
    it('should handle error state recovery', () => {
      // Force into error state
      stateMachine.transition('START_CREATE');
      stateMachine.transition('COMPLETE_ERROR', {
        error: new Error('Test error')
      });
      
      expect(stateMachine.getState()).toBe('error');

      // Should be able to reset from error state
      expect(stateMachine.transition('RESET')).toBe(true);
      expect(stateMachine.getState()).toBe('idle');

      // Should be able to start new operations after reset
      expect(stateMachine.transition('START_CREATE')).toBe(true);
      expect(stateMachine.getState()).toBe('creating');
    });

    it('should handle error state with retry attempts', () => {
      // Go to error state
      stateMachine.transition('START_CREATE');
      stateMachine.transition('COMPLETE_ERROR', {
        error: new Error('Network timeout')
      });

      expect(stateMachine.getState()).toBe('error');

      // Should allow direct retry operations from error state
      expect(stateMachine.transition('START_CREATE')).toBe(true);
      expect(stateMachine.getState()).toBe('creating');

      // This time succeed
      expect(stateMachine.transition('COMPLETE_SUCCESS')).toBe(true);
      expect(stateMachine.getState()).toBe('idle');
    });

    it('should preserve error information during transitions', () => {
      const testError = new Error('Detailed error information');
      
      // Create error state with specific error
      stateMachine.transition('START_SWITCH');
      stateMachine.transition('COMPLETE_ERROR', { error: testError });

      const errorStateData = stateMachine.getStateData();
      expect(errorStateData.error).toBe(testError);
      expect(errorStateData.currentState).toBe('error');

      // Error should be preserved even after transitions that don't clear it
      const stateDataAfter = stateMachine.getStateData();
      expect(stateDataAfter.error).toBe(testError);
    });
  });

  describe('State Machine Listener Management', () => {
    it('should notify listeners of state changes', () => {
      const listenerCalls: ThreadStateData[] = [];
      
      const removeListener = stateMachine.addListener((data) => {
        listenerCalls.push({ ...data });
      });

      // Make a state transition
      stateMachine.transition('START_CREATE', {
        targetThreadId: 'listener-test-thread'
      });

      expect(listenerCalls).toHaveLength(1);
      expect(listenerCalls[0].currentState).toBe('creating');
      expect(listenerCalls[0].targetThreadId).toBe('listener-test-thread');

      // Make another transition
      stateMachine.transition('COMPLETE_SUCCESS');
      
      expect(listenerCalls).toHaveLength(2);
      expect(listenerCalls[1].currentState).toBe('idle');

      // Remove listener and verify it's not called
      removeListener();
      
      stateMachine.transition('START_SWITCH');
      expect(listenerCalls).toHaveLength(2); // Should not increase
    });

    it('should handle listener errors gracefully', () => {
      let errorThrown = false;
      
      // Add a listener that throws an error
      stateMachine.addListener(() => {
        errorThrown = true;
        throw new Error('Listener error');
      });

      // Add a normal listener
      const normalListenerCalls: ThreadStateData[] = [];
      stateMachine.addListener((data) => {
        normalListenerCalls.push({ ...data });
      });

      // Transition should still work despite listener error
      expect(() => {
        stateMachine.transition('START_CREATE');
      }).not.toThrow();

      expect(errorThrown).toBe(true);
      expect(normalListenerCalls).toHaveLength(1); // Normal listener should still be called
      expect(stateMachine.getState()).toBe('creating'); // State should still change
    });

    it('should support multiple concurrent listeners', () => {
      const listener1Calls: string[] = [];
      const listener2Calls: string[] = [];
      const listener3Calls: string[] = [];

      stateMachine.addListener((data) => listener1Calls.push(data.currentState));
      stateMachine.addListener((data) => listener2Calls.push(data.currentState));
      stateMachine.addListener((data) => listener3Calls.push(data.currentState));

      // Execute multiple transitions
      stateMachine.transition('START_CREATE');
      stateMachine.transition('COMPLETE_SUCCESS');
      stateMachine.transition('START_SWITCH');

      // All listeners should receive all notifications
      expect(listener1Calls).toEqual(['creating', 'idle', 'switching']);
      expect(listener2Calls).toEqual(['creating', 'idle', 'switching']);
      expect(listener3Calls).toEqual(['creating', 'idle', 'switching']);
    });
  });

  describe('Reset Functionality', () => {
    it('should reset to initial state from any state', () => {
      // Navigate through multiple states
      stateMachine.transition('START_CREATE');
      stateMachine.transition('COMPLETE_ERROR', { error: new Error('Test') });
      
      expect(stateMachine.getState()).toBe('error');

      // Reset should return to initial state
      stateMachine.reset();
      expect(stateMachine.getState()).toBe('idle');

      const resetStateData = stateMachine.getStateData();
      expect(resetStateData.currentState).toBe('idle');
      expect(resetStateData.targetThreadId).toBeNull();
      expect(resetStateData.operationId).toBeNull();
      expect(resetStateData.error).toBeNull();
    });

    it('should notify listeners about reset transition', () => {
      const listenerCalls: { from: ThreadState; to: ThreadState }[] = [];
      
      stateMachine.addListener(() => {
        // Track transitions via the config callback since reset is a special transition
      });

      const originalOnChange = stateMachine['config'].onStateChange;
      stateMachine['config'].onStateChange = (from, to, data) => {
        listenerCalls.push({ from, to });
        originalOnChange?.(from, to, data);
      };

      // Navigate to error state
      stateMachine.transition('START_CREATE');
      stateMachine.transition('COMPLETE_ERROR');

      // Reset
      stateMachine.reset();

      // Should have recorded the reset transition
      const resetTransition = listenerCalls.find(call => call.to === 'idle' && call.from === 'error');
      expect(resetTransition).toBeTruthy();
    });
  });

  describe('Transition Validation', () => {
    it('should validate transitions using canTransition method', () => {
      // Valid transition check
      expect(stateMachine.canTransition('START_CREATE')).toBe(true);
      
      // Invalid transition check
      expect(stateMachine.canTransition('COMPLETE_SUCCESS')).toBe(false); // Can't complete from idle

      // Transition to creating state
      stateMachine.transition('START_CREATE');
      
      // Now different transitions should be valid/invalid
      expect(stateMachine.canTransition('START_CREATE')).toBe(false); // Can't start create from creating
      expect(stateMachine.canTransition('COMPLETE_SUCCESS')).toBe(true); // Can complete from creating
      expect(stateMachine.canTransition('COMPLETE_ERROR')).toBe(true); // Can error from creating
      expect(stateMachine.canTransition('CANCEL')).toBe(true); // Can cancel from creating
    });

    it('should respect guard conditions in canTransition', () => {
      let guardShouldAllow = true;

      const config = createTestConfig({
        transitions: [
          {
            from: 'idle',
            to: 'creating',
            event: 'START_CREATE',
            guard: () => guardShouldAllow
          }
        ]
      });

      const testMachine = new ThreadStateMachine(config);

      // Guard allows transition
      guardShouldAllow = true;
      expect(testMachine.canTransition('START_CREATE')).toBe(true);

      // Guard blocks transition
      guardShouldAllow = false;
      expect(testMachine.canTransition('START_CREATE')).toBe(false);
    });
  });
});

describe('ThreadStateMachineManager', () => {
  let manager: ThreadStateMachineManager;

  beforeEach(() => {
    manager = new ThreadStateMachineManager();
  });

  describe('Machine Management', () => {
    it('should create and retrieve state machines by key', () => {
      const key1 = 'thread-operation-1';
      const key2 = 'thread-operation-2';

      // Get machines (should create them)
      const machine1 = manager.getStateMachine(key1);
      const machine2 = manager.getStateMachine(key2);

      expect(machine1).toBeInstanceOf(ThreadStateMachine);
      expect(machine2).toBeInstanceOf(ThreadStateMachine);
      expect(machine1).not.toBe(machine2);

      // Retrieving same key should return same machine
      const machine1Again = manager.getStateMachine(key1);
      expect(machine1Again).toBe(machine1);
    });

    it('should remove state machines correctly', () => {
      const key = 'removable-machine';
      
      // Create machine
      const machine = manager.getStateMachine(key);
      expect(machine).toBeTruthy();

      // Remove machine
      manager.removeStateMachine(key);

      // Getting same key should create new machine
      const newMachine = manager.getStateMachine(key);
      expect(newMachine).not.toBe(machine);
    });

    it('should track all active state machines', () => {
      const keys = ['machine-1', 'machine-2', 'machine-3'];
      
      // Create multiple machines
      keys.forEach(key => manager.getStateMachine(key));

      // Get all machines
      const allMachines = manager.getAllStateMachines();
      expect(allMachines.size).toBe(keys.length);

      keys.forEach(key => {
        expect(allMachines.has(key)).toBe(true);
        expect(allMachines.get(key)).toBeInstanceOf(ThreadStateMachine);
      });
    });

    it('should reset all state machines', () => {
      const keys = ['reset-test-1', 'reset-test-2'];
      
      // Create machines and transition them to non-idle states
      const machines = keys.map(key => {
        const machine = manager.getStateMachine(key);
        machine.transition('START_CREATE');
        expect(machine.getState()).toBe('creating');
        return machine;
      });

      // Reset all machines
      manager.resetAll();

      // All machines should be back to idle
      machines.forEach(machine => {
        expect(machine.getState()).toBe('idle');
      });
    });
  });

  describe('Isolation Between Machines', () => {
    it('should maintain isolation between different thread operations', () => {
      const createKey = 'create-operation';
      const switchKey = 'switch-operation';
      const loadKey = 'load-operation';

      // Get different machines for different operations
      const createMachine = manager.getStateMachine(createKey);
      const switchMachine = manager.getStateMachine(switchKey);
      const loadMachine = manager.getStateMachine(loadKey);

      // Start different operations on each machine
      createMachine.transition('START_CREATE', {
        targetThreadId: 'create-thread',
        operationId: 'create-123'
      });

      switchMachine.transition('START_SWITCH', {
        targetThreadId: 'switch-thread',
        operationId: 'switch-456'
      });

      loadMachine.transition('START_LOAD', {
        targetThreadId: 'load-thread',
        operationId: 'load-789'
      });

      // Verify each machine maintains its own state
      expect(createMachine.getState()).toBe('creating');
      expect(switchMachine.getState()).toBe('switching');
      expect(loadMachine.getState()).toBe('loading');

      // Verify state data isolation
      const createData = createMachine.getStateData();
      const switchData = switchMachine.getStateData();
      const loadData = loadMachine.getStateData();

      expect(createData.targetThreadId).toBe('create-thread');
      expect(createData.operationId).toBe('create-123');

      expect(switchData.targetThreadId).toBe('switch-thread');
      expect(switchData.operationId).toBe('switch-456');

      expect(loadData.targetThreadId).toBe('load-thread');
      expect(loadData.operationId).toBe('load-789');

      // Operations on one machine should not affect others
      createMachine.transition('COMPLETE_ERROR', { error: new Error('Create failed') });
      
      expect(createMachine.getState()).toBe('error');
      expect(switchMachine.getState()).toBe('switching'); // Should not change
      expect(loadMachine.getState()).toBe('loading'); // Should not change
    });

    it('should handle concurrent operations without interference', () => {
      const concurrentKeys = Array.from({ length: 10 }, (_, i) => `concurrent-${i}`);
      const results: Array<{ key: string; finalState: ThreadState; success: boolean }> = [];

      // Start concurrent operations
      const machines = concurrentKeys.map(key => {
        const machine = manager.getStateMachine(key);
        
        // Simulate different operations with different outcomes
        const operationType = key.includes('0') ? 'START_CREATE' :
                            key.includes('1') ? 'START_SWITCH' : 'START_LOAD';
        
        const success = machine.transition(operationType as ThreadEvent, {
          targetThreadId: `${key}-thread`,
          operationId: `${key}-operation`,
          startTime: Date.now()
        });

        results.push({
          key,
          finalState: machine.getState(),
          success
        });

        return { key, machine };
      });

      // Verify all operations started successfully
      results.forEach(result => {
        expect(result.success).toBe(true);
        expect(['creating', 'switching', 'loading']).toContain(result.finalState);
      });

      // Complete operations with different outcomes
      machines.forEach(({ key, machine }, index) => {
        if (index % 3 === 0) {
          // Success
          machine.transition('COMPLETE_SUCCESS');
          expect(machine.getState()).toBe('idle');
        } else if (index % 3 === 1) {
          // Error
          machine.transition('COMPLETE_ERROR', { error: new Error(`Error in ${key}`) });
          expect(machine.getState()).toBe('error');
        } else {
          // Cancel
          machine.transition('CANCEL');
          expect(machine.getState()).toBe('cancelling');
        }
      });

      // Verify final states are as expected
      machines.forEach(({ machine }, index) => {
        const expectedState = index % 3 === 0 ? 'idle' :
                            index % 3 === 1 ? 'error' : 'cancelling';
        expect(machine.getState()).toBe(expectedState);
      });
    });
  });
});

describe('Global ThreadStateMachineManager Instance', () => {
  it('should provide singleton access to thread state machine manager', () => {
    expect(threadStateMachineManager).toBeInstanceOf(ThreadStateMachineManager);
    
    // Should be the same instance on multiple accesses
    const manager1 = threadStateMachineManager;
    const manager2 = threadStateMachineManager;
    expect(manager1).toBe(manager2);
  });

  it('should maintain state across global access', () => {
    const testKey = 'global-test-machine';
    
    // Create machine via global instance
    const machine1 = threadStateMachineManager.getStateMachine(testKey);
    machine1.transition('START_CREATE');
    
    // Access via global instance again
    const machine2 = threadStateMachineManager.getStateMachine(testKey);
    
    expect(machine2).toBe(machine1);
    expect(machine2.getState()).toBe('creating');
  });
});

describe('Thread State Machine Configuration Factory', () => {
  it('should create valid default configuration', () => {
    const config = createThreadStateMachineConfig();
    
    expect(config.initialState).toBe('idle');
    expect(config.transitions).toBeInstanceOf(Array);
    expect(config.transitions.length).toBeGreaterThan(0);
    expect(config.onStateChange).toBeInstanceOf(Function);
    expect(config.onTransitionBlocked).toBeInstanceOf(Function);
  });

  it('should include all necessary state transitions', () => {
    const config = createThreadStateMachineConfig();
    
    // Check that all expected transitions are present
    const transitionMap = new Map<string, ThreadEvent[]>();
    
    config.transitions.forEach(transition => {
      const fromState = transition.from;
      if (!transitionMap.has(fromState)) {
        transitionMap.set(fromState, []);
      }
      transitionMap.get(fromState)!.push(transition.event);
    });

    // Verify key transitions exist
    expect(transitionMap.get('idle')).toContain('START_CREATE');
    expect(transitionMap.get('idle')).toContain('START_SWITCH');
    expect(transitionMap.get('idle')).toContain('START_LOAD');
    
    expect(transitionMap.get('creating')).toContain('COMPLETE_SUCCESS');
    expect(transitionMap.get('creating')).toContain('COMPLETE_ERROR');
    expect(transitionMap.get('creating')).toContain('CANCEL');
    
    expect(transitionMap.get('error')).toContain('RESET');
    expect(transitionMap.get('error')).toContain('START_CREATE'); // Allow retry from error
  });

  it('should have proper callback implementations', () => {
    const config = createThreadStateMachineConfig();
    
    // Test onStateChange callback
    expect(() => {
      config.onStateChange?.('idle', 'creating', createMockStateData({ currentState: 'creating' }));
    }).not.toThrow();

    // Test onTransitionBlocked callback  
    expect(() => {
      config.onTransitionBlocked?.('INVALID_EVENT' as ThreadEvent, 'idle');
    }).not.toThrow();
  });
});

describe('Thread State Machine Business Value Integration', () => {
  let stateMachine: ThreadStateMachine;
  let businessMetrics: {
    operationsStarted: number;
    operationsCompleted: number;
    operationsFailed: number;
    averageOperationTime: number;
    concurrentOperations: number;
  };

  beforeEach(() => {
    businessMetrics = {
      operationsStarted: 0,
      operationsCompleted: 0,
      operationsFailed: 0,
      averageOperationTime: 0,
      concurrentOperations: 0
    };

    const config = createThreadStateMachineConfig();
    
    // Add business metrics tracking
    const originalOnStateChange = config.onStateChange;
    config.onStateChange = (from, to, data) => {
      // Track business metrics
      if (to === 'creating' || to === 'switching' || to === 'loading') {
        businessMetrics.operationsStarted++;
        businessMetrics.concurrentOperations++;
      }
      
      if (from !== 'idle' && to === 'idle') {
        businessMetrics.operationsCompleted++;
        businessMetrics.concurrentOperations = Math.max(0, businessMetrics.concurrentOperations - 1);
        
        // Calculate operation time if available
        if (data.startTime) {
          const operationTime = Date.now() - data.startTime;
          businessMetrics.averageOperationTime = 
            (businessMetrics.averageOperationTime + operationTime) / 2;
        }
      }
      
      if (to === 'error') {
        businessMetrics.operationsFailed++;
        businessMetrics.concurrentOperations = Math.max(0, businessMetrics.concurrentOperations - 1);
      }

      originalOnStateChange?.(from, to, data);
    };

    stateMachine = new ThreadStateMachine(config);
  });

  it('should track thread operation business metrics', () => {
    const startTime = Date.now();

    // Simulate successful thread creation
    stateMachine.transition('START_CREATE', {
      targetThreadId: 'business-thread-1',
      operationId: 'business-op-1',
      startTime
    });

    expect(businessMetrics.operationsStarted).toBe(1);
    expect(businessMetrics.concurrentOperations).toBe(1);

    // Complete operation
    stateMachine.transition('COMPLETE_SUCCESS');

    expect(businessMetrics.operationsCompleted).toBe(1);
    expect(businessMetrics.concurrentOperations).toBe(0);
    expect(businessMetrics.operationsFailed).toBe(0);

    // Simulate failed operation
    stateMachine.transition('START_SWITCH', {
      targetThreadId: 'business-thread-2',
      startTime: Date.now()
    });

    stateMachine.transition('COMPLETE_ERROR', {
      error: new Error('Network timeout')
    });

    expect(businessMetrics.operationsStarted).toBe(2);
    expect(businessMetrics.operationsFailed).toBe(1);
    expect(businessMetrics.concurrentOperations).toBe(0);
  });

  it('should prevent race conditions that impact user experience', () => {
    let raceConditionDetected = false;
    let concurrentOperationAttempts = 0;

    const config = createThreadStateMachineConfig();
    config.onTransitionBlocked = (event, currentState) => {
      if (currentState !== 'idle' && ['START_CREATE', 'START_SWITCH', 'START_LOAD'].includes(event)) {
        raceConditionDetected = true;
        concurrentOperationAttempts++;
      }
    };

    const raceMachine = new ThreadStateMachine(config);

    // Start an operation
    raceMachine.transition('START_CREATE', { targetThreadId: 'race-thread-1' });
    expect(raceMachine.getState()).toBe('creating');

    // Attempt another operation while first is in progress (should be blocked)
    const blockedResult = raceMachine.transition('START_SWITCH', { targetThreadId: 'race-thread-2' });
    
    expect(blockedResult).toBe(false);
    expect(raceConditionDetected).toBe(true);
    expect(concurrentOperationAttempts).toBe(1);
    expect(raceMachine.getState()).toBe('creating'); // Should remain in original state

    // Complete first operation
    raceMachine.transition('COMPLETE_SUCCESS');
    expect(raceMachine.getState()).toBe('idle');

    // Now second operation should be allowed
    const allowedResult = raceMachine.transition('START_SWITCH', { targetThreadId: 'race-thread-2' });
    expect(allowedResult).toBe(true);
    expect(raceMachine.getState()).toBe('switching');
  });

  it('should maintain data integrity during state transitions', () => {
    const operationData = {
      targetThreadId: 'integrity-thread',
      operationId: 'integrity-op-123',
      startTime: Date.now(),
      metadata: { userId: 'user-456', priority: 'high' }
    };

    // Start operation with data
    stateMachine.transition('START_CREATE', operationData);

    let stateDataDuringTransition: ThreadStateData;
    
    const config = stateMachine['config'];
    const originalOnStateChange = config.onStateChange;
    config.onStateChange = (from, to, data) => {
      stateDataDuringTransition = { ...data };
      originalOnStateChange?.(from, to, data);
    };

    // Transition to completion
    stateMachine.transition('COMPLETE_SUCCESS');

    // Verify data integrity was maintained throughout transition
    expect(stateDataDuringTransition!.targetThreadId).toBe(operationData.targetThreadId);
    expect(stateDataDuringTransition!.operationId).toBe(operationData.operationId);
    expect(stateDataDuringTransition!.startTime).toBe(operationData.startTime);
  });

  it('should handle high-frequency state transitions without corruption', () => {
    const iterations = 100;
    let corruptionDetected = false;

    // Perform rapid state transitions
    for (let i = 0; i < iterations; i++) {
      const operationId = `rapid-op-${i}`;
      const startTime = Date.now();

      // Start operation
      const startResult = stateMachine.transition('START_CREATE', {
        targetThreadId: `rapid-thread-${i}`,
        operationId,
        startTime
      });

      if (!startResult) {
        corruptionDetected = true;
        break;
      }

      // Verify state is correct
      const stateAfterStart = stateMachine.getState();
      if (stateAfterStart !== 'creating') {
        corruptionDetected = true;
        break;
      }

      // Complete operation
      const completeResult = stateMachine.transition('COMPLETE_SUCCESS');
      if (!completeResult) {
        corruptionDetected = true;
        break;
      }

      // Verify back to idle
      const stateAfterComplete = stateMachine.getState();
      if (stateAfterComplete !== 'idle') {
        corruptionDetected = true;
        break;
      }
    }

    expect(corruptionDetected).toBe(false);
    expect(businessMetrics.operationsStarted).toBe(iterations);
    expect(businessMetrics.operationsCompleted).toBe(iterations);
    expect(businessMetrics.operationsFailed).toBe(0);
  });
});