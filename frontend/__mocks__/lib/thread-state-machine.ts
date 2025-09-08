/**
 * Mock for thread-state-machine
 * 
 * Provides a complete functional mock implementation that maintains state
 * and supports proper transitions for testing thread operations.
 */

import { logger } from '@/lib/logger';

export type ThreadState = 
  | 'idle'
  | 'creating'
  | 'switching'
  | 'loading'
  | 'error'
  | 'cancelling';

export type ThreadEvent = 
  | 'START_CREATE'
  | 'START_SWITCH'
  | 'START_LOAD'
  | 'COMPLETE_SUCCESS'
  | 'COMPLETE_ERROR'
  | 'CANCEL'
  | 'RESET';

export interface ThreadStateData {
  readonly currentState: ThreadState;
  readonly targetThreadId: string | null;
  readonly operationId: string | null;
  readonly startTime: number | null;
  readonly error: Error | null;
  readonly canTransition: boolean;
}

/**
 * Mock ThreadStateMachine that maintains state properly
 */
class MockThreadStateMachine {
  private currentState: ThreadState = 'idle';
  private stateData: ThreadStateData = {
    currentState: 'idle',
    targetThreadId: null,
    operationId: null,
    startTime: null,
    error: null,
    canTransition: true
  };

  public getState(): ThreadState {
    return this.currentState;
  }

  public getStateData(): ThreadStateData {
    return { ...this.stateData };
  }

  public canTransition(event: ThreadEvent): boolean {
    // Allow all transitions for testing - prevents blocking
    return true;
  }

  public transition(event: ThreadEvent, data?: Partial<ThreadStateData>): boolean {
    const previousState = this.currentState;
    
    // Handle state transitions
    switch (event) {
      case 'START_CREATE':
        this.currentState = 'creating';
        break;
      case 'START_SWITCH':
        this.currentState = 'switching';
        break;
      case 'START_LOAD':
        this.currentState = 'loading';
        break;
      case 'COMPLETE_SUCCESS':
        this.currentState = 'idle';
        break;
      case 'COMPLETE_ERROR':
        this.currentState = 'error';
        break;
      case 'CANCEL':
        this.currentState = 'cancelling';
        break;
      case 'RESET':
        this.currentState = 'idle';
        break;
      default:
        logger.warn(`Unknown transition event: ${event}`);
        return false;
    }

    // Update state data
    this.stateData = {
      ...this.stateData,
      ...data,
      currentState: this.currentState
    };

    logger.debug(`Mock state transition: ${previousState} -> ${this.currentState} (${event})`);
    return true;
  }

  public addListener(listener: (data: ThreadStateData) => void): () => void {
    // Return empty unsubscribe function for testing
    return () => {};
  }

  public reset(): void {
    this.transition('RESET');
  }
}

/**
 * Mock ThreadStateMachineManager that manages multiple state machines
 */
class MockThreadStateMachineManager {
  private readonly machines = new Map<string, MockThreadStateMachine>();

  public getStateMachine(key: string): MockThreadStateMachine {
    let machine = this.machines.get(key);
    if (!machine) {
      machine = new MockThreadStateMachine();
      this.machines.set(key, machine);
    }
    return machine;
  }

  public removeStateMachine(key: string): void {
    this.machines.delete(key);
  }

  public getAllStateMachines(): Map<string, MockThreadStateMachine> {
    return new Map(this.machines);
  }

  public resetAll(): void {
    this.machines.forEach(machine => machine.reset());
  }

  // Legacy support for old test patterns
  public transition(event: ThreadEvent, data?: any): boolean {
    // Use default machine for backward compatibility
    const defaultMachine = this.getStateMachine('default');
    return defaultMachine.transition(event, data);
  }

  public getState(): ThreadState {
    // Use default machine for backward compatibility
    const defaultMachine = this.getStateMachine('default');
    return defaultMachine.getState();
  }
}

// Export the mock manager instance
export const threadStateMachineManager = new MockThreadStateMachineManager();

// Export other classes for testing
export { MockThreadStateMachine as ThreadStateMachine };
export const createThreadStateMachineConfig = () => ({
  initialState: 'idle' as ThreadState,
  transitions: [],
  onStateChange: () => {},
  onTransitionBlocked: () => {}
});