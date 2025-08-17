import React from 'react';

export interface StatusZone {
  type: 'slow' | 'medium' | 'fast';
  label: string;
  content: string | number | React.ReactNode;
  icon: React.ReactNode;
  lastUpdate: number;
  color: string;
}

export interface Metrics {
  recordsProcessed: number;
  processingRate: number;
  estimatedTimeRemaining: number;
  confidenceScore: number;
}

export interface WorkflowProgress {
  current_step: number;
  total_steps: number;
}

export type ZoneType = 'slow' | 'medium' | 'fast';

export interface DataPreviewItem {
  id: string;
  model: string;
  latency: number;
  tokens: number;
  cost: string;
}

export type ToolExecutionStatus = 'executing' | 'idle' | 'completed';