import type { StateCreator } from 'zustand';
import type {
  FastLayerData,
  MediumLayerData,
  SlowLayerData
} from '@/types/unified-chat';
import type { LayerDataState } from './types';

export const createLayerDataSlice: StateCreator<
  LayerDataState,
  [],
  [],
  LayerDataState
> = (set) => ({
  fastLayerData: null,
  mediumLayerData: null,
  slowLayerData: null,

  updateFastLayer: (data) => set((state) => ({
    fastLayerData: state.fastLayerData 
      ? { ...state.fastLayerData, ...data }
      : (data as FastLayerData)
  })),

  updateMediumLayer: (data) => set((state) => {
    const currentData = state.mediumLayerData;
    
    // Handle partial content accumulation
    if (data.partialContent && currentData?.partialContent) {
      return {
        mediumLayerData: {
          ...currentData,
          ...data,
          partialContent: (() => {
            // If new content contains old content, use new only
            if (data.partialContent.includes(currentData.partialContent)) {
              return data.partialContent;
            }
            // Otherwise append new to old
            return currentData.partialContent + data.partialContent;
          })()
        }
      };
    }
    
    return {
      mediumLayerData: currentData
        ? { ...currentData, ...data }
        : (data as MediumLayerData)
    };
  }),

  updateSlowLayer: (data) => set((state) => {
    const currentData = state.slowLayerData;
    
    // Handle adding completed agents
    if (data.completedAgents && currentData?.completedAgents) {
      return {
        slowLayerData: {
          ...currentData,
          ...data,
          completedAgents: [...currentData.completedAgents, ...data.completedAgents]
        }
      };
    }
    
    return {
      slowLayerData: currentData
        ? { ...currentData, ...data }
        : (data as SlowLayerData)
    };
  }),

  resetLayers: () => set({
    fastLayerData: null,
    mediumLayerData: null,
    slowLayerData: null
  })
});