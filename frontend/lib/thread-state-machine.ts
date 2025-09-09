/**
 * Thread State Machine
 * 
 * Manages thread operations as a finite state machine to prevent race conditions.
 * Ensures atomic transitions and proper state isolation between operations.
 * 
 * @compliance conventions.xml - Single responsibility, under 750 lines
 * @compliance type_safety.xml - Strongly typed state machine with clear interfaces
 */

import { logger } from '@/lib/logger';

/**
 * Thread operation states
 */
export type ThreadState = 
  | 'idle'
  | 'creating'
  | 'switching'
  | 'loading'
  | 'error'
  | 'cancelling';

/**
 * Thread operation events
 */
export type ThreadEvent = 
  | 'START_CREATE'
  | 'START_SWITCH'
  | 'START_LOAD'
  | 'COMPLETE_SUCCESS'
  | 'COMPLETE_ERROR'
  | 'CANCEL'
  | 'RESET';

/**
 * Thread state data
 */
export interface ThreadStateData {
  readonly currentState: ThreadState;
  readonly targetThreadId: string | null;
  readonly operationId: string | null;
  readonly startTime: number | null;
  readonly error: Error | null;
  readonly canTransition: boolean;
}

/**
 * Thread state transition
 */
export interface ThreadTransition {
  readonly from: ThreadState;
  readonly to: ThreadState;
  readonly event: ThreadEvent;
  readonly guard?: (data: ThreadStateData) => boolean;
  readonly action?: (data: ThreadStateData) => void;
}

/**
 * Thread state machine configuration
 */
export interface ThreadStateMachineConfig {
  readonly initialState: ThreadState;
  readonly transitions: ThreadTransition[];
  readonly onStateChange?: (from: ThreadState, to: ThreadState, data: ThreadStateData) => void;
  readonly onTransitionBlocked?: (event: ThreadEvent, currentState: ThreadState) => void;
}

/**
 * Thread state machine
 */
export class ThreadStateMachine {
  private currentState: ThreadState;
  private stateData: ThreadStateData;
  private readonly config: ThreadStateMachineConfig;
  private readonly listeners = new Set<(data: ThreadStateData) => void>();

  constructor(config: ThreadStateMachineConfig) {
    this.config = config;
    this.currentState = config.initialState;
    this.stateData = this.createInitialStateData();
  }

  /**
   * Gets current state
   */
  public getState(): ThreadState {
    return this.currentState;
  }

  /**
   * Gets state data
   */
  public getStateData(): ThreadStateData {
    return { ...this.stateData };
  }

  /**
   * Checks if transition is allowed
   */
  public canTransition(event: ThreadEvent): boolean {
    const transition = this.findTransition(this.currentState, event);
    if (!transition) return false;
    
    return !transition.guard || transition.guard(this.stateData);
  }

  /**
   * Performs state transition
   */
  public transition(event: ThreadEvent, data?: Partial<ThreadStateData>): boolean {
    const transition = this.findTransition(this.currentState, event);
    
    if (!transition) {
      logger.warn(`No transition found for event ${event} in state ${this.currentState}`);
      this.config.onTransitionBlocked?.(event, this.currentState);
      return false;
    }

    if (transition.guard && !transition.guard(this.stateData)) {
      logger.warn(`Transition guard blocked ${event} in state ${this.currentState}`);
      this.config.onTransitionBlocked?.(event, this.currentState);
      return false;
    }

    const previousState = this.currentState;
    this.currentState = transition.to;
    
    // Update state data
    this.stateData = {
      ...this.stateData,
      ...data,
      currentState: this.currentState
    };

    // Execute transition action
    if (transition.action) {
      transition.action(this.stateData);
    }

    // Notify listeners
    this.config.onStateChange?.(previousState, this.currentState, this.stateData);
    this.notifyListeners();

    logger.debug(`State transition: ${previousState} -> ${this.currentState} (${event})`);
    return true;
  }

  /**
   * Adds state change listener
   */
  public addListener(listener: (data: ThreadStateData) => void): () => void {
    this.listeners.add(listener);
    return () => this.listeners.delete(listener);
  }

  /**
   * Resets state machine
   */
  public reset(): void {
    const previousState = this.currentState;
    this.currentState = this.config.initialState;
    this.stateData = this.createInitialStateData();
    
    // Notify listeners of reset
    this.config.onStateChange?.(previousState, this.currentState, this.stateData);
    this.notifyListeners();
    
    logger.debug(`State machine reset: ${previousState} -> ${this.currentState}`);
  }

  /**
   * Finds transition for current state and event
   */
  private findTransition(state: ThreadState, event: ThreadEvent): ThreadTransition | undefined {
    return this.config.transitions.find(t => t.from === state && t.event === event);
  }

  /**
   * Creates initial state data
   */
  private createInitialStateData(): ThreadStateData {
    return {
      currentState: this.config.initialState,
      targetThreadId: null,
      operationId: null,
      startTime: null,
      error: null,
      canTransition: true
    };
  }

  /**
   * Notifies all listeners
   */
  private notifyListeners(): void {
    this.listeners.forEach(listener => {
      try {
        listener(this.stateData);
      } catch (error) {
        logger.error('State machine listener error:', error);
      }
    });
  }
}

/**
 * Creates default thread state machine configuration
 */
export const createThreadStateMachineConfig = (): ThreadStateMachineConfig => {
  return {
    initialState: 'idle',
    transitions: [
      // From idle
      { from: 'idle', to: 'creating', event: 'START_CREATE' },
      { from: 'idle', to: 'switching', event: 'START_SWITCH' },
      { from: 'idle', to: 'loading', event: 'START_LOAD' },
      
      // From creating
      { from: 'creating', to: 'idle', event: 'COMPLETE_SUCCESS' },
      { from: 'creating', to: 'error', event: 'COMPLETE_ERROR' },
      { from: 'creating', to: 'cancelling', event: 'CANCEL' },
      
      // From switching
      { from: 'switching', to: 'idle', event: 'COMPLETE_SUCCESS' },
      { from: 'switching', to: 'error', event: 'COMPLETE_ERROR' },
      { from: 'switching', to: 'cancelling', event: 'CANCEL' },
      
      // From loading
      { from: 'loading', to: 'idle', event: 'COMPLETE_SUCCESS' },
      { from: 'loading', to: 'error', event: 'COMPLETE_ERROR' },
      { from: 'loading', to: 'cancelling', event: 'CANCEL' },
      
      // From error
      { from: 'error', to: 'idle', event: 'RESET' },
      { from: 'error', to: 'idle', event: 'COMPLETE_ERROR' }, // Allow error -> idle for cleanup
      { from: 'error', to: 'creating', event: 'START_CREATE' },
      { from: 'error', to: 'switching', event: 'START_SWITCH' },
      
      // From cancelling
      { from: 'cancelling', to: 'idle', event: 'COMPLETE_SUCCESS' },
      { from: 'cancelling', to: 'idle', event: 'COMPLETE_ERROR' },
      
      // Global reset
      { from: 'creating', to: 'idle', event: 'RESET' },
      { from: 'switching', to: 'idle', event: 'RESET' },
      { from: 'loading', to: 'idle', event: 'RESET' },
      { from: 'cancelling', to: 'idle', event: 'RESET' }
    ],
    onStateChange: (from, to, data) => {
      logger.debug(`Thread state: ${from} -> ${to}`, { 
        threadId: data.targetThreadId, 
        operationId: data.operationId 
      });
    },
    onTransitionBlocked: (event, currentState) => {
      logger.warn(`Thread transition blocked: ${event} in state ${currentState}`);
    }
  };
};

/**
 * Thread state machine manager
 */
export class ThreadStateMachineManager {
  private readonly machines = new Map<string, ThreadStateMachine>();

  /**
   * Gets or creates state machine for thread
   */
  public getStateMachine(key: string): ThreadStateMachine {
    let machine = this.machines.get(key);
    if (!machine) {
      machine = new ThreadStateMachine(createThreadStateMachineConfig());
      this.machines.set(key, machine);
    }
    return machine;
  }

  /**
   * Removes state machine
   */
  public removeStateMachine(key: string): void {
    this.machines.delete(key);
  }

  /**
   * Gets all active state machines
   */
  public getAllStateMachines(): Map<string, ThreadStateMachine> {
    return new Map(this.machines);
  }

  /**
   * Resets all state machines
   */
  public resetAll(): void {
    this.machines.forEach(machine => machine.reset());
  }
}

// Export singleton instance
export const threadStateMachineManager = new ThreadStateMachineManager();