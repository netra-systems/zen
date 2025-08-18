// Layer visibility utilities for three-layer response card system
// Fixes visibility logic to properly handle all data states

import type { FastLayerData, MediumLayerData, SlowLayerData } from '@/types/layer-types';

// ============================================
// Core Visibility Calculation Types
// ============================================

export interface LayerVisibilityState {
  showFastLayer: boolean;
  showMediumLayer: boolean;
  showSlowLayer: boolean;
}

export interface VisibilityCalculationParams {
  fastLayerData: FastLayerData | null;
  mediumLayerData: MediumLayerData | null;
  slowLayerData: SlowLayerData | null;
  isProcessing: boolean;
}

// ============================================
// Main Visibility Calculator
// ============================================

export const calculateLayerVisibility = (
  params: VisibilityCalculationParams
): LayerVisibilityState => {
  const fastLayerVisible = shouldShowFastLayer(params);
  const mediumLayerVisible = shouldShowMediumLayer(params);
  const slowLayerVisible = shouldShowSlowLayer(params);

  return {
    showFastLayer: fastLayerVisible,
    showMediumLayer: mediumLayerVisible,
    showSlowLayer: slowLayerVisible
  };
};

// ============================================
// Fast Layer Visibility Logic
// ============================================

export const shouldShowFastLayer = (
  params: VisibilityCalculationParams
): boolean => {
  const { fastLayerData, isProcessing } = params;
  
  return hasProcessingActivity(isProcessing) ||
         hasAgentData(fastLayerData) ||
         hasActiveTools(fastLayerData) ||
         hasToolStatuses(fastLayerData);
};

const hasProcessingActivity = (isProcessing: boolean): boolean => {
  return isProcessing;
};

const hasAgentData = (data: FastLayerData | null): boolean => {
  return data !== null && Boolean(data?.agentName);
};

const hasActiveTools = (data: FastLayerData | null): boolean => {
  return data?.activeTools?.length ? data.activeTools.length > 0 : false;
};

// ============================================
// Medium Layer Visibility Logic  
// ============================================

export const shouldShowMediumLayer = (
  params: VisibilityCalculationParams
): boolean => {
  const { mediumLayerData } = params;
  
  return hasThoughtContent(mediumLayerData) ||
         hasPartialContent(mediumLayerData) ||
         hasStepProgress(mediumLayerData);
};

const hasThoughtContent = (data: MediumLayerData | null): boolean => {
  return data !== null && Boolean(data?.thought?.trim());
};

const hasPartialContent = (data: MediumLayerData | null): boolean => {
  return data !== null && Boolean(data?.partialContent?.trim());
};

const hasStepProgress = (data: MediumLayerData | null): boolean => {
  return data !== null && 
         data?.stepNumber > 0 && 
         data?.totalSteps > 0;
};

// ============================================
// Slow Layer Visibility Logic
// ============================================

export const shouldShowSlowLayer = (
  params: VisibilityCalculationParams
): boolean => {
  const { slowLayerData } = params;
  
  return hasCompletedAgents(slowLayerData) ||
         hasFinalReport(slowLayerData) ||
         hasExecutionMetrics(slowLayerData);
};

const hasCompletedAgents = (data: SlowLayerData | null): boolean => {
  return data?.completedAgents?.length ? data.completedAgents.length > 0 : false;
};

const hasFinalReport = (data: SlowLayerData | null): boolean => {
  return data !== null && data?.finalReport !== null;
};

const hasExecutionMetrics = (data: SlowLayerData | null): boolean => {
  return data !== null && 
         data?.totalDuration > 0;
};

// ============================================
// Tool Status Utilities
// ============================================

const hasToolStatuses = (data: FastLayerData | null): boolean => {
  if (!data?.toolStatuses?.length) return false;
  
  return data.toolStatuses.some(status => 
    status.isActive || hasRecentToolActivity(status)
  );
};

const hasRecentToolActivity = (status: any): boolean => {
  if (!status.startTime) return false;
  
  const timeSinceStart = Date.now() - status.startTime;
  const RECENT_ACTIVITY_THRESHOLD = 30000; // 30 seconds
  
  return timeSinceStart < RECENT_ACTIVITY_THRESHOLD;
};

// ============================================
// Data Persistence Checks
// ============================================

export const shouldPersistFastLayer = (
  data: FastLayerData | null,
  wasVisible: boolean
): boolean => {
  if (!wasVisible) return false;
  
  return hasAgentData(data) || 
         hasActiveTools(data) ||
         hasToolStatuses(data);
};

export const shouldPersistMediumLayer = (
  data: MediumLayerData | null,
  wasVisible: boolean
): boolean => {
  if (!wasVisible) return false;
  
  return hasThoughtContent(data) || 
         hasPartialContent(data);
};

export const shouldPersistSlowLayer = (
  data: SlowLayerData | null,
  wasVisible: boolean
): boolean => {
  if (!wasVisible) return false;
  
  return hasCompletedAgents(data) || 
         hasFinalReport(data);
};