/**
 * Error classification utilities
 * Determines severity and recovery strategy for errors
 */

import { EventError, ErrorClassification, DEFAULT_ERROR_CLASSIFICATIONS } from './event-error-types';

export class ErrorClassifier {
  private classifications: ErrorClassification[];

  constructor(classifications: ErrorClassification[] = DEFAULT_ERROR_CLASSIFICATIONS) {
    this.classifications = classifications;
  }

  /**
   * Classify error severity based on type and content
   */
  classifyError(error: Error, eventType: string): EventError['severity'] {
    const message = error.message.toLowerCase();
    
    // Check custom classifications first
    for (const classification of this.classifications) {
      const regex = new RegExp(classification.pattern, 'i');
      if (regex.test(message) || regex.test(eventType)) {
        return classification.severity;
      }
    }
    
    // Default to low severity
    return 'low';
  }

  /**
   * Determine if error is recoverable
   */
  isRecoverable(error: Error, eventType: string): boolean {
    const message = error.message.toLowerCase();
    
    // Check classifications for recoverability
    for (const classification of this.classifications) {
      const regex = new RegExp(classification.pattern, 'i');
      if (regex.test(message) || regex.test(eventType)) {
        return classification.recoverable;
      }
    }
    
    // Default to recoverable
    return true;
  }

  /**
   * Get error category
   */
  getErrorCategory(error: Error): string {
    const message = error.message.toLowerCase();
    
    if (message.includes('network') || message.includes('connection')) {
      return 'network';
    }
    
    if (message.includes('timeout')) {
      return 'timeout';
    }
    
    if (message.includes('parse') || message.includes('json')) {
      return 'parsing';
    }
    
    if (message.includes('validation') || message.includes('type')) {
      return 'validation';
    }
    
    return 'unknown';
  }

  /**
   * Add custom classification
   */
  addClassification(classification: ErrorClassification): void {
    this.classifications.push(classification);
  }

  /**
   * Remove classification by pattern
   */
  removeClassification(pattern: string): void {
    this.classifications = this.classifications.filter(c => c.pattern !== pattern);
  }

  /**
   * Get all classifications
   */
  getClassifications(): ErrorClassification[] {
    return [...this.classifications];
  }
}