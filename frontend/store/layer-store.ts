// Layer-specific store for three-layer response card system
// Focused module handling Fast/Medium/Slow layer data

import { create } from 'zustand';
import { devtools } from 'zustand/middleware';
import type {
  FastLayerData,
  MediumLayerData,
  SlowLayerData,
  LayerUpdateEvent
} from '@/types/layer-types';

// ============================================
// Layer Store State
// ============================================

interface LayerStoreState {
  // Layer data
  fastLayerData: FastLayerData | null;
  mediumLayerData: MediumLayerData | null;
  slowLayerData: SlowLayerData | null;
  
  // Layer actions
  updateFastLayer: (data: Partial<FastLayerData>) => void;
  updateMediumLayer: (data: Partial<MediumLayerData>) => void;
  updateSlowLayer: (data: Partial<SlowLayerData>) => void;
  updateLayer: (event: LayerUpdateEvent) => void;
  resetLayers: () => void;
  
  // Layer visibility
  getLayerVisibility: () => {
    showFastLayer: boolean;
    showMediumLayer: boolean;
    showSlowLayer: boolean;
  };
}

// ============================================
// Layer Store Implementation
// ============================================

export const useLayerStore = create<LayerStoreState>()(devtools(
  (set, get) => ({
    // Initial state
    fastLayerData: null,
    mediumLayerData: null,
    slowLayerData: null,
    
    // Fast layer updates
    updateFastLayer: (data) => {
      set((state) => ({
        fastLayerData: mergeFastLayerData(state.fastLayerData, data)
      }));
    },
    
    // Medium layer updates with content accumulation
    updateMediumLayer: (data) => {
      set((state) => ({
        mediumLayerData: mergeMediumLayerData(state.mediumLayerData, data)
      }));
    },
    
    // Slow layer updates with agent accumulation
    updateSlowLayer: (data) => {
      set((state) => ({
        slowLayerData: mergeSlowLayerData(state.slowLayerData, data)
      }));
    },
    
    // Generic layer update dispatcher
    updateLayer: (event) => {
      const handlers = getLayerUpdateHandlers(get());
      handlers[event.layer](event.data as any);
    },
    
    // Reset all layers
    resetLayers: () => {
      set({ fastLayerData: null, mediumLayerData: null, slowLayerData: null });
    },
    
    // Calculate layer visibility
    getLayerVisibility: () => {
      const state = get();
      return calculateLayerVisibility(state);
    }
  }),
  { name: 'layer-store' }
));

// ============================================
// Layer Data Merging Functions
// ============================================

const mergeFastLayerData = (
  current: FastLayerData | null,
  update: Partial<FastLayerData>
): FastLayerData => {
  if (!current) return update as FastLayerData;
  return { ...current, ...update };
};

const mergeMediumLayerData = (
  current: MediumLayerData | null,
  update: Partial<MediumLayerData>
): MediumLayerData => {
  if (!current) return update as MediumLayerData;
  return {
    ...current,
    ...update,
    partialContent: mergePartialContent(current, update)
  };
};

const mergePartialContent = (
  current: MediumLayerData,
  update: Partial<MediumLayerData>
): string => {
  if (!update.partialContent) return current.partialContent;
  if (!current.partialContent) return update.partialContent;
  
  // Smart content merging - avoid duplication
  if (update.partialContent.includes(current.partialContent)) {
    return update.partialContent;
  }
  
  return current.partialContent + update.partialContent;
};

const mergeSlowLayerData = (
  current: SlowLayerData | null,
  update: Partial<SlowLayerData>
): SlowLayerData => {
  if (!current) return update as SlowLayerData;
  return {
    ...current,
    ...update,
    completedAgents: mergeCompletedAgents(current, update)
  };
};

const mergeCompletedAgents = (
  current: SlowLayerData,
  update: Partial<SlowLayerData>
) => {
  if (!update.completedAgents) return current.completedAgents;
  if (!current.completedAgents) return update.completedAgents;
  
  return [...current.completedAgents, ...update.completedAgents];
};

// ============================================
// Layer Update Handlers
// ============================================

const getLayerUpdateHandlers = (state: LayerStoreState) => ({
  fast: state.updateFastLayer,
  medium: state.updateMediumLayer,
  slow: state.updateSlowLayer
});

// ============================================
// Layer Visibility Calculation
// ============================================

const calculateLayerVisibility = (state: {
  fastLayerData: FastLayerData | null;
  mediumLayerData: MediumLayerData | null;
  slowLayerData: SlowLayerData | null;
}) => {
  const showFastLayer = shouldShowFastLayer(state.fastLayerData);
  const showMediumLayer = shouldShowMediumLayer(state.mediumLayerData);
  const showSlowLayer = shouldShowSlowLayer(state.slowLayerData);
  
  return { showFastLayer, showMediumLayer, showSlowLayer };
};

const shouldShowFastLayer = (data: FastLayerData | null): boolean => {
  return data !== null && Boolean(data.agentName);
};

const shouldShowMediumLayer = (data: MediumLayerData | null): boolean => {
  return data !== null && (Boolean(data.thought) || Boolean(data.partialContent));
};

const shouldShowSlowLayer = (data: SlowLayerData | null): boolean => {
  return data !== null && (
    (data.completedAgents?.length > 0) || Boolean(data.finalReport)
  );
};

// ============================================
// Layer Store Utilities
// ============================================

export const layerStoreSelectors = {
  fastLayerData: (state: LayerStoreState) => state.fastLayerData,
  mediumLayerData: (state: LayerStoreState) => state.mediumLayerData,
  slowLayerData: (state: LayerStoreState) => state.slowLayerData,
  layerVisibility: (state: LayerStoreState) => state.getLayerVisibility(),
  hasAnyLayerData: (state: LayerStoreState) => {
    return Boolean(state.fastLayerData || state.mediumLayerData || state.slowLayerData);
  }
};
