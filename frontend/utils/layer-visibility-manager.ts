// Layer visibility manager with fixes for specific visibility issues
// Addresses gaps in layer visibility calculations

import type { 
  FastLayerData, 
  MediumLayerData, 
  SlowLayerData 
} from '@/types/layer-types';

// ============================================
// Enhanced Visibility Manager
// ============================================

export interface LayerVisibilityConfig {
  fastLayerData: FastLayerData | null;
  mediumLayerData: MediumLayerData | null;
  slowLayerData: SlowLayerData | null;
  isProcessing: boolean;
  previousVisibility?: LayerVisibilityResult;
}

export interface LayerVisibilityResult {
  showFastLayer: boolean;
  showMediumLayer: boolean;
  showSlowLayer: boolean;
  fastLayerReason: string;
  mediumLayerReason: string;
  slowLayerReason: string;
}

export const calculateEnhancedLayerVisibility = (
  config: LayerVisibilityConfig
): LayerVisibilityResult => {
  const fastResult = calculateFastLayerVisibility(config);
  const mediumResult = calculateMediumLayerVisibility(config);
  const slowResult = calculateSlowLayerVisibility(config);

  return {
    showFastLayer: fastResult.show,
    showMediumLayer: mediumResult.show,
    showSlowLayer: slowResult.show,
    fastLayerReason: fastResult.reason,
    mediumLayerReason: mediumResult.reason,
    slowLayerReason: slowResult.reason
  };
};

// ============================================
// Fast Layer Visibility (Fixed)
// ============================================

interface LayerVisibilityDecision {
  show: boolean;
  reason: string;
}

const calculateFastLayerVisibility = (
  config: LayerVisibilityConfig
): LayerVisibilityDecision => {
  const { fastLayerData, isProcessing, previousVisibility } = config;
  
  // Fix 1: Don't disappear when isProcessing becomes false if tools are active
  if (hasActiveOrRecentTools(fastLayerData)) {
    return { show: true, reason: 'active_tools' };
  }
  
  // Show when processing starts
  if (isProcessing) {
    return { show: true, reason: 'processing' };
  }
  
  // Show when agent data exists
  if (hasAgentName(fastLayerData)) {
    return { show: true, reason: 'agent_data' };
  }
  
  // Persist if was visible and still has meaningful data
  if (shouldPersistFastLayer(fastLayerData, previousVisibility)) {
    return { show: true, reason: 'persisting_data' };
  }
  
  return { show: false, reason: 'no_data' };
};

const hasActiveOrRecentTools = (data: FastLayerData | null): boolean => {
  if (!data) return false;
  
  // Check legacy activeTools array
  if (data.activeTools?.length > 0) return true;
  
  // Check enhanced toolStatuses
  if (data.toolStatuses?.length > 0) {
    return data.toolStatuses.some(status => {
      return status.isActive || isToolRecentlyActive(status);
    });
  }
  
  return false;
};

const isToolRecentlyActive = (status: any): boolean => {
  if (!status?.startTime) return false;
  
  const timeSinceStart = Date.now() - status.startTime;
  const TOOL_PERSISTENCE_TIME = 30000; // 30 seconds
  
  return timeSinceStart < TOOL_PERSISTENCE_TIME;
};

// ============================================
// Medium Layer Visibility (Fixed)
// ============================================

const calculateMediumLayerVisibility = (
  config: LayerVisibilityConfig
): LayerVisibilityDecision => {
  const { mediumLayerData, previousVisibility } = config;
  
  // Fix 2: Show if partialContent arrives before thought
  if (hasPartialContent(mediumLayerData)) {
    return { show: true, reason: 'partial_content' };
  }
  
  // Show if thought exists
  if (hasThought(mediumLayerData)) {
    return { show: true, reason: 'thought' };
  }
  
  // Show if step progress exists
  if (hasStepProgress(mediumLayerData)) {
    return { show: true, reason: 'step_progress' };
  }
  
  // Persist if was visible and still has content
  if (shouldPersistMediumLayer(mediumLayerData, previousVisibility)) {
    return { show: true, reason: 'persisting_content' };
  }
  
  return { show: false, reason: 'no_content' };
};

const hasPartialContent = (data: MediumLayerData | null): boolean => {
  return Boolean(data?.partialContent?.trim());
};

const hasThought = (data: MediumLayerData | null): boolean => {
  return Boolean(data?.thought?.trim());
};

const hasStepProgress = (data: MediumLayerData | null): boolean => {
  return Boolean(data?.stepNumber > 0 && data?.totalSteps > 0);
};

// ============================================
// Slow Layer Visibility (Fixed)
// ============================================

const calculateSlowLayerVisibility = (
  config: LayerVisibilityConfig
): LayerVisibilityDecision => {
  const { slowLayerData, previousVisibility } = config;
  
  // Fix 3: Show if finalReport exists, even without completedAgents
  if (hasFinalReport(slowLayerData)) {
    return { show: true, reason: 'final_report' };
  }
  
  // Show if completed agents exist
  if (hasCompletedAgents(slowLayerData)) {
    return { show: true, reason: 'completed_agents' };
  }
  
  // Show if execution metrics exist
  if (hasExecutionMetrics(slowLayerData)) {
    return { show: true, reason: 'execution_metrics' };
  }
  
  // Persist if was visible and still has results
  if (shouldPersistSlowLayer(slowLayerData, previousVisibility)) {
    return { show: true, reason: 'persisting_results' };
  }
  
  return { show: false, reason: 'no_results' };
};

const hasFinalReport = (data: SlowLayerData | null): boolean => {
  return data?.finalReport !== null && data?.finalReport !== undefined;
};

const hasCompletedAgents = (data: SlowLayerData | null): boolean => {
  return (data?.completedAgents?.length || 0) > 0;
};

const hasExecutionMetrics = (data: SlowLayerData | null): boolean => {
  return Boolean(data?.totalDuration && data.totalDuration > 0);
};

// ============================================
// Persistence Logic
// ============================================

const shouldPersistFastLayer = (
  data: FastLayerData | null,
  previousVisibility?: LayerVisibilityResult
): boolean => {
  if (!previousVisibility?.showFastLayer) return false;
  if (!data) return false;
  
  return hasAgentName(data) || hasActiveOrRecentTools(data);
};

const shouldPersistMediumLayer = (
  data: MediumLayerData | null,
  previousVisibility?: LayerVisibilityResult
): boolean => {
  if (!previousVisibility?.showMediumLayer) return false;
  if (!data) return false;
  
  return hasPartialContent(data) || hasThought(data);
};

const shouldPersistSlowLayer = (
  data: SlowLayerData | null,
  previousVisibility?: LayerVisibilityResult
): boolean => {
  if (!previousVisibility?.showSlowLayer) return false;
  if (!data) return false;
  
  return hasFinalReport(data) || hasCompletedAgents(data);
};

// ============================================
// Helper Functions
// ============================================

const hasAgentName = (data: FastLayerData | null): boolean => {
  return Boolean(data?.agentName);
};

// ============================================
// Debug Utilities
// ============================================

export const debugLayerVisibility = (
  config: LayerVisibilityConfig
): void => {
  if (process.env.NODE_ENV !== 'development') return;
  
  const result = calculateEnhancedLayerVisibility(config);
  
  logger.group('Layer Visibility Debug');
  logger.debug('Fast Layer:', result.showFastLayer, '-', result.fastLayerReason);
  logger.debug('Medium Layer:', result.showMediumLayer, '-', result.mediumLayerReason);
  logger.debug('Slow Layer:', result.showSlowLayer, '-', result.slowLayerReason);
  logger.debug('Data:', {
    fast: config.fastLayerData,
    medium: config.mediumLayerData,
    slow: config.slowLayerData,
    processing: config.isProcessing
  });
  logger.groupEnd();
};