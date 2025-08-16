// Layer state management for handling layer data persistence and transitions
// Ensures layers persist when they have valid data

import type { 
  FastLayerData, 
  MediumLayerData, 
  SlowLayerData 
} from '@/types/layer-types';

// ============================================
// Layer State Types
// ============================================

export interface LayerState {
  isVisible: boolean;
  wasVisible: boolean;
  hasData: boolean;
  shouldPersist: boolean;
}

export interface LayerStateManager {
  fastLayer: LayerState;
  mediumLayer: LayerState;
  slowLayer: LayerState;
}

export interface LayerStateUpdateParams {
  fastLayerData: FastLayerData | null;
  mediumLayerData: MediumLayerData | null;
  slowLayerData: SlowLayerData | null;
  isProcessing: boolean;
  previousState?: LayerStateManager;
}

// ============================================
// State Manager Factory
// ============================================

export const createLayerStateManager = (
  params: LayerStateUpdateParams
): LayerStateManager => {
  const fastLayerState = createFastLayerState(params);
  const mediumLayerState = createMediumLayerState(params);
  const slowLayerState = createSlowLayerState(params);

  return {
    fastLayer: fastLayerState,
    mediumLayer: mediumLayerState,
    slowLayer: slowLayerState
  };
};

// ============================================
// Fast Layer State Management
// ============================================

const createFastLayerState = (
  params: LayerStateUpdateParams
): LayerState => {
  const hasData = evaluateFastLayerData(params.fastLayerData);
  const wasVisible = params.previousState?.fastLayer?.isVisible || false;
  const shouldPersist = calculateFastLayerPersistence(params, wasVisible);
  const isVisible = hasData || shouldPersist || params.isProcessing;

  return { isVisible, wasVisible, hasData, shouldPersist };
};

const evaluateFastLayerData = (data: FastLayerData | null): boolean => {
  if (!data) return false;
  
  return Boolean(data.agentName) ||
         hasValidTools(data) ||
         hasValidToolStatuses(data);
};

const hasValidTools = (data: FastLayerData): boolean => {
  return data.activeTools?.length > 0;
};

const hasValidToolStatuses = (data: FastLayerData): boolean => {
  return data.toolStatuses?.some(status => 
    status.isActive || isRecentToolActivity(status)
  ) || false;
};

// ============================================
// Medium Layer State Management
// ============================================

const createMediumLayerState = (
  params: LayerStateUpdateParams
): LayerState => {
  const hasData = evaluateMediumLayerData(params.mediumLayerData);
  const wasVisible = params.previousState?.mediumLayer?.isVisible || false;
  const shouldPersist = calculateMediumLayerPersistence(params, wasVisible);
  const isVisible = hasData || shouldPersist;

  return { isVisible, wasVisible, hasData, shouldPersist };
};

const evaluateMediumLayerData = (data: MediumLayerData | null): boolean => {
  if (!data) return false;
  
  return hasValidThought(data) ||
         hasValidPartialContent(data) ||
         hasValidStepProgress(data);
};

const hasValidThought = (data: MediumLayerData): boolean => {
  return Boolean(data.thought?.trim());
};

const hasValidPartialContent = (data: MediumLayerData): boolean => {
  return Boolean(data.partialContent?.trim());
};

const hasValidStepProgress = (data: MediumLayerData): boolean => {
  return data.stepNumber > 0 && data.totalSteps > 0;
};

// ============================================
// Slow Layer State Management
// ============================================

const createSlowLayerState = (
  params: LayerStateUpdateParams
): LayerState => {
  const hasData = evaluateSlowLayerData(params.slowLayerData);
  const wasVisible = params.previousState?.slowLayer?.isVisible || false;
  const shouldPersist = calculateSlowLayerPersistence(params, wasVisible);
  const isVisible = hasData || shouldPersist;

  return { isVisible, wasVisible, hasData, shouldPersist };
};

const evaluateSlowLayerData = (data: SlowLayerData | null): boolean => {
  if (!data) return false;
  
  return hasValidCompletedAgents(data) ||
         hasValidFinalReport(data) ||
         hasValidMetrics(data);
};

const hasValidCompletedAgents = (data: SlowLayerData): boolean => {
  return data.completedAgents?.length > 0;
};

const hasValidFinalReport = (data: SlowLayerData): boolean => {
  return data.finalReport !== null;
};

const hasValidMetrics = (data: SlowLayerData): boolean => {
  return data.totalDuration > 0;
};

// ============================================
// Persistence Calculation
// ============================================

const calculateFastLayerPersistence = (
  params: LayerStateUpdateParams,
  wasVisible: boolean
): boolean => {
  if (!wasVisible) return false;
  
  const data = params.fastLayerData;
  if (!data) return false;
  
  return Boolean(data.agentName) || 
         hasValidTools(data) ||
         hasValidToolStatuses(data);
};

const calculateMediumLayerPersistence = (
  params: LayerStateUpdateParams,
  wasVisible: boolean
): boolean => {
  if (!wasVisible) return false;
  
  const data = params.mediumLayerData;
  if (!data) return false;
  
  return hasValidThought(data) || hasValidPartialContent(data);
};

const calculateSlowLayerPersistence = (
  params: LayerStateUpdateParams,
  wasVisible: boolean
): boolean => {
  if (!wasVisible) return false;
  
  const data = params.slowLayerData;
  if (!data) return false;
  
  return hasValidCompletedAgents(data) || hasValidFinalReport(data);
};

// ============================================
// Utility Functions
// ============================================

const isRecentToolActivity = (status: any): boolean => {
  if (!status?.startTime) return false;
  
  const timeSinceStart = Date.now() - status.startTime;
  const RECENT_ACTIVITY_THRESHOLD = 30000; // 30 seconds
  
  return timeSinceStart < RECENT_ACTIVITY_THRESHOLD;
};

// ============================================
// State Transition Helpers
// ============================================

export const shouldShowLayerTransition = (
  currentState: LayerState,
  previousState?: LayerState
): boolean => {
  if (!previousState) return currentState.isVisible;
  
  return currentState.isVisible !== previousState.isVisible;
};

export const getLayerTransitionDirection = (
  currentState: LayerState,
  previousState?: LayerState
): 'show' | 'hide' | 'none' => {
  if (!previousState) {
    return currentState.isVisible ? 'show' : 'none';
  }
  
  if (currentState.isVisible && !previousState.isVisible) return 'show';
  if (!currentState.isVisible && previousState.isVisible) return 'hide';
  return 'none';
};