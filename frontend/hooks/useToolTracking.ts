// Tool tracking hook - Initializes and manages tool tracking service
// Modular hook following 25-line function limits

import { useEffect, useRef } from 'react';
import { 
  createToolTrackingService,
  setGlobalToolTracker,
  type ToolTrackingConfig
} from '@/services/tool-tracking-service';
import { useUnifiedChatStore } from '@/store/unified-chat';

/**
 * Hook to initialize tool tracking with store integration
 */
export const useToolTracking = (config?: Partial<ToolTrackingConfig>) => {
  const serviceRef = useRef<ReturnType<typeof createToolTrackingService> | null>(null);
  const updateFastLayer = useUnifiedChatStore(state => state.updateFastLayer);

  useEffect(() => {
    initializeToolTrackingService(config, updateFastLayer, serviceRef);
    return () => cleanupToolTrackingService(serviceRef);
  }, [config, updateFastLayer]);

  return serviceRef.current;
};

/**
 * Initializes tool tracking service with store callback
 */
const initializeToolTrackingService = (
  config: Partial<ToolTrackingConfig> | undefined,
  updateFastLayer: (data: any) => void,
  serviceRef: React.MutableRefObject<any>
): void => {
  const onToolsUpdated = (tools: string[]) => {
    updateFastLayer({ activeTools: tools });
  };
  
  serviceRef.current = createToolTrackingService(config, onToolsUpdated);
  setGlobalToolTracker(serviceRef.current);
};

/**
 * Cleanup tool tracking service on unmount
 */
const cleanupToolTrackingService = (
  serviceRef: React.MutableRefObject<any>
): void => {
  if (serviceRef.current) {
    serviceRef.current.cleanup();
    serviceRef.current = null;
  }
};

/**
 * Hook for accessing active tools with deduplication
 */
export const useActiveTools = () => {
  const fastLayerData = useUnifiedChatStore(state => state.fastLayerData);
  
  return {
    activeTools: getActiveToolsFromLayer(fastLayerData),
    toolStatuses: fastLayerData?.toolStatuses || [],
    hasActiveTools: hasAnyActiveTools(fastLayerData)
  };
};

/**
 * Extracts active tools from fast layer data
 */
const getActiveToolsFromLayer = (fastLayerData: any): string[] => {
  if (fastLayerData?.toolStatuses) {
    return fastLayerData.toolStatuses
      .filter((status: any) => status.isActive)
      .map((status: any) => status.name);
  }
  return fastLayerData?.activeTools || [];
};

/**
 * Checks if any tools are currently active
 */
const hasAnyActiveTools = (fastLayerData: any): boolean => {
  const activeTools = getActiveToolsFromLayer(fastLayerData);
  return activeTools.length > 0;
};