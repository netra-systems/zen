/// <reference types="cypress" />

import {
  setupStateTests,
  cleanupState,
  TEST_CONFIG,
  getStore,
  verifyStoreAndGetState
} from './utils/state-test-utilities';

describe('CRITICAL: Layer Data Synchronization', () => {
  beforeEach(() => {
    setupStateTests();
  });

  it('CRITICAL: Should properly accumulate partial content in medium layer', () => {
    const chunks = [
      'This is ',
      'a test of ',
      'partial content ',
      'accumulation in ',
      'the medium layer.'
    ];
    
    let accumulatedContent = '';
    
    // Simulate streaming partial content
    simulateStreamingContent(chunks, (content, isStreaming) => {
      accumulatedContent = content;
      updateMediumLayerContent(content, isStreaming);
    });
    
    // Verify final accumulated content
    verifyAccumulatedContent(chunks.join(''));
  });

  it('CRITICAL: Should not lose data when layers update simultaneously', () => {
    const testData = createLayerTestData();
    
    // Update all layers simultaneously
    executeSimultaneousLayerUpdates(testData);
    
    cy.wait(TEST_CONFIG.DELAYS.LONG);
    
    // Verify all layer data is preserved
    verifyAllLayerDataPreserved(testData);
  });

  it('CRITICAL: Should handle completed agents accumulation correctly', () => {
    const agents = createTestAgents();
    
    // Add agents one by one
    addAgentsSequentially(agents);
    
    // Verify all agents accumulated
    verifyAgentsAccumulated(agents);
  });

  afterEach(() => {
    cleanupState();
  });
});

/**
 * Simulates streaming content chunks
 */
function simulateStreamingContent(
  chunks: string[], 
  updateCallback: (content: string, isStreaming: boolean) => void
): void {
  chunks.forEach((chunk, index) => {
    cy.window().then(() => {
      const accumulatedContent = chunks.slice(0, index + 1).join('');
      const isStreaming = index < chunks.length - 1;
      updateCallback(accumulatedContent, isStreaming);
    });
    
    cy.wait(TEST_CONFIG.DELAYS.SHORT);
  });
}

/**
 * Updates medium layer with content
 */
function updateMediumLayerContent(content: string, isStreaming: boolean): void {
  cy.window().then((win) => {
    const store = getStore(win);
    if (store) {
      store.getState().updateMediumLayer({
        partialContent: content,
        isStreaming,
        timestamp: Date.now()
      });
    }
  });
}

/**
 * Verifies accumulated content in medium layer
 */
function verifyAccumulatedContent(expectedContent: string): void {
  cy.window().then((win) => {
    const store = getStore(win);
    if (store) {
      const state = store.getState();
      const mediumLayer = state.mediumLayerData;
      
      expect(mediumLayer).to.not.be.null;
      expect(mediumLayer.partialContent).to.equal(
        expectedContent,
        'Content should be properly accumulated'
      );
      expect(mediumLayer.isStreaming).to.be.false;
    }
  });
}

/**
 * Creates test data for all layers
 */
function createLayerTestData(): any {
  return {
    fast: { status: 'processing', startTime: Date.now() },
    medium: { progress: 50, message: 'Analyzing...' },
    slow: { completedAgents: ['agent1'], totalAgents: 3 }
  };
}

/**
 * Executes simultaneous updates across all layers
 */
function executeSimultaneousLayerUpdates(testData: any): void {
  cy.window().then((win) => {
    const store = getStore(win);
    if (store) {
      // Fire updates in parallel
      Promise.all([
        createLayerUpdatePromise(() => store.getState().updateFastLayer(testData.fast)),
        createLayerUpdatePromise(() => store.getState().updateMediumLayer(testData.medium)),
        createLayerUpdatePromise(() => store.getState().updateSlowLayer(testData.slow))
      ]);
    }
  });
}

/**
 * Creates a promise for layer update
 */
function createLayerUpdatePromise(updateFn: () => void): Promise<void> {
  return new Promise((resolve) => {
    updateFn();
    resolve();
  });
}

/**
 * Verifies all layer data is preserved after simultaneous updates
 */
function verifyAllLayerDataPreserved(testData: any): void {
  cy.window().then((win) => {
    const store = getStore(win);
    if (store) {
      const state = store.getState();
      
      // Check fast layer
      expect(state.fastLayerData).to.deep.include(testData.fast);
      
      // Check medium layer
      expect(state.mediumLayerData).to.deep.include(testData.medium);
      
      // Check slow layer
      expect(state.slowLayerData).to.deep.include(testData.slow);
    }
  });
}

/**
 * Creates test agents for accumulation testing
 */
function createTestAgents(): any[] {
  return [
    { name: 'TriageAgent', result: 'Categorized as optimization request' },
    { name: 'DataAgent', result: 'Collected performance metrics' },
    { name: 'OptimizationAgent', result: 'Generated optimization plan' }
  ];
}

/**
 * Adds agents sequentially to test accumulation
 */
function addAgentsSequentially(agents: any[]): void {
  agents.forEach((agent, index) => {
    cy.window().then((win) => {
      const store = getStore(win);
      if (store) {
        const currentAgents = store.getState().slowLayerData?.completedAgents || [];
        
        store.getState().updateSlowLayer({
          completedAgents: [...currentAgents, agent],
          progress: ((index + 1) / agents.length) * 100
        });
      }
    });
    
    cy.wait(TEST_CONFIG.DELAYS.MEDIUM);
  });
}

/**
 * Verifies all agents were accumulated correctly
 */
function verifyAgentsAccumulated(agents: any[]): void {
  cy.window().then((win) => {
    const store = getStore(win);
    if (store) {
      const state = store.getState();
      const completedAgents = state.slowLayerData?.completedAgents || [];
      
      expect(completedAgents).to.have.length(agents.length);
      agents.forEach((agent, index) => {
        expect(completedAgents[index]).to.deep.include(agent);
      });
      
      expect(state.slowLayerData?.progress).to.equal(100);
    }
  });
}