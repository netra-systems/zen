/**
 * Circuit breaker implementation for error handling
 * Prevents cascading failures during high error rates
 */

import { logger } from '@/lib/logger';

export interface CircuitBreakerConfig {
  failureThreshold: number;
  timeWindowMs: number;
  recoveryTimeoutMs: number;
}

export interface CircuitBreakerState {
  isOpen: boolean;
  failureCount: number;
  lastFailureTime: number;
  openedAt: number;
}

export class CircuitBreaker {
  private state: CircuitBreakerState;
  private config: CircuitBreakerConfig;
  private failureWindow: number[] = [];
  private recoveryTimer?: NodeJS.Timeout;

  constructor(config: Partial<CircuitBreakerConfig> = {}) {
    this.config = {
      failureThreshold: 10,
      timeWindowMs: 60000,
      recoveryTimeoutMs: 30000,
      ...config
    };
    
    this.state = {
      isOpen: false,
      failureCount: 0,
      lastFailureTime: 0,
      openedAt: 0
    };
  }

  /**
   * Record a failure
   */
  recordFailure(): void {
    const now = Date.now();
    this.failureWindow.push(now);
    
    // Clean old failures outside window
    this.cleanFailureWindow(now);
    
    this.state.failureCount = this.failureWindow.length;
    this.state.lastFailureTime = now;
    
    // Check if threshold exceeded
    if (this.shouldOpenCircuit()) {
      this.openCircuit();
    }
  }

  /**
   * Record a success
   */
  recordSuccess(): void {
    if (this.state.isOpen) {
      this.closeCircuit();
    }
    // Don't reset failure count on success - let time window handle it
  }

  /**
   * Check if circuit should open
   */
  private shouldOpenCircuit(): boolean {
    return this.failureWindow.length >= this.config.failureThreshold;
  }

  /**
   * Open the circuit
   */
  private openCircuit(): void {
    if (this.state.isOpen) return;
    
    this.state.isOpen = true;
    this.state.openedAt = Date.now();
    
    logger.warn('Circuit breaker opened', {
      component: 'CircuitBreaker',
      failureCount: this.state.failureCount,
      threshold: this.config.failureThreshold
    });
    
    // Set recovery timer
    this.scheduleRecovery();
  }

  /**
   * Close the circuit
   */
  private closeCircuit(): void {
    this.state.isOpen = false;
    this.state.openedAt = 0;
    this.failureWindow = [];
    this.state.failureCount = 0;
    
    if (this.recoveryTimer) {
      clearTimeout(this.recoveryTimer);
      this.recoveryTimer = undefined;
    }
    
    logger.info('Circuit breaker closed', {
      component: 'CircuitBreaker'
    });
  }

  /**
   * Schedule automatic recovery
   */
  private scheduleRecovery(): void {
    if (this.recoveryTimer) {
      clearTimeout(this.recoveryTimer);
    }
    
    this.recoveryTimer = setTimeout(() => {
      this.closeCircuit();
    }, this.config.recoveryTimeoutMs);
  }

  /**
   * Clean failures outside time window
   */
  private cleanFailureWindow(currentTime: number): void {
    const cutoff = currentTime - this.config.timeWindowMs;
    this.failureWindow = this.failureWindow.filter(time => time > cutoff);
  }

  /**
   * Check if circuit is open
   */
  isOpen(): boolean {
    return this.state.isOpen;
  }

  /**
   * Get circuit state
   */
  getState(): CircuitBreakerState {
    return { ...this.state };
  }

  /**
   * Get failure rate
   */
  getFailureRate(): number {
    return this.failureWindow.length;
  }

  /**
   * Reset circuit breaker
   */
  reset(): void {
    this.closeCircuit();
  }

  /**
   * Cleanup resources
   */
  destroy(): void {
    if (this.recoveryTimer) {
      clearTimeout(this.recoveryTimer);
      this.recoveryTimer = undefined;
    }
    this.failureWindow = [];
  }
}