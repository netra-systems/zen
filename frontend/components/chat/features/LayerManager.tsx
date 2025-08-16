"use client";

import React, { useState, useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { FastLayer } from '@/components/chat/layers/FastLayer';
import { MediumLayer } from '@/components/chat/layers/MediumLayer';
import { SlowLayer } from '@/components/chat/layers/SlowLayer';
import type { LayerManagerProps } from '@/types/component-props';
import { 
  calculateEnhancedLayerVisibility,
  debugLayerVisibility,
  type LayerVisibilityResult
} from '@/utils/layer-visibility-manager';

export const LayerManager: React.FC<LayerManagerProps> = ({
  fastLayerData,
  mediumLayerData,
  slowLayerData,
  isProcessing,
  transitions
}) => {
  const previousVisibility = useRef<LayerVisibilityResult | undefined>();
  const [debugMode] = useState(process.env.NODE_ENV === 'development');
  
  const layerVisibility = calculateEnhancedLayerVisibility({
    fastLayerData,
    mediumLayerData,
    slowLayerData,
    isProcessing,
    previousVisibility: previousVisibility.current
  });
  
  useEffect(() => {
    previousVisibility.current = layerVisibility;
  }, [layerVisibility]);
  
  if (debugMode) {
    debugLayerVisibility({
      fastLayerData,
      mediumLayerData,
      slowLayerData,
      isProcessing,
      previousVisibility: previousVisibility.current
    });
  }

  return (
    <>
      <FastLayerRenderer
        show={layerVisibility.showFastLayer}
        data={fastLayerData}
        isProcessing={isProcessing}
        transition={transitions.fast}
      />
      <MediumLayerRenderer
        show={layerVisibility.showMediumLayer}
        data={mediumLayerData}
        showFastLayer={layerVisibility.showFastLayer}
        transition={transitions.medium}
      />
      <SlowLayerRenderer
        show={layerVisibility.showSlowLayer}
        data={slowLayerData}
        showPreviousLayers={layerVisibility.showFastLayer || layerVisibility.showMediumLayer}
        transition={transitions.slow}
      />
    </>
  );
};

// Removed legacy visibility logic - now using enhanced visibility manager

interface FastLayerRendererProps {
  show: boolean;
  data: any;
  isProcessing: boolean;
  transition: any;
}

const FastLayerRenderer: React.FC<FastLayerRendererProps> = ({
  show,
  data,
  isProcessing,
  transition
}) => (
  <AnimatePresence mode="wait">
    {show && (
      <motion.div
        key="fast-layer"
        initial={{ opacity: 0, height: 0, y: -10 }}
        animate={{ opacity: 1, height: 48, y: 0 }}
        exit={{ opacity: 0, height: 0, y: -10 }}
        transition={getFastLayerTransition()}
      >
        <FastLayer data={data} isProcessing={isProcessing} />
      </motion.div>
    )}
  </AnimatePresence>
);

interface MediumLayerRendererProps {
  show: boolean;
  data: any;
  showFastLayer: boolean;
  transition: any;
}

const MediumLayerRenderer: React.FC<MediumLayerRendererProps> = ({
  show,
  data,
  showFastLayer,
  transition
}) => (
  <AnimatePresence mode="wait">
    {show && (
      <motion.div
        key="medium-layer"
        initial={{ opacity: 0, height: 0, y: -8 }}
        animate={{ opacity: 1, height: 'auto', y: 0 }}
        exit={{ opacity: 0, height: 0, y: -8 }}
        transition={getMediumLayerTransition(showFastLayer)}
      >
        <MediumLayer data={data} />
      </motion.div>
    )}
  </AnimatePresence>
);

interface SlowLayerRendererProps {
  show: boolean;
  data: any;
  showPreviousLayers: boolean;
  transition: any;
}

const SlowLayerRenderer: React.FC<SlowLayerRendererProps> = ({
  show,
  data,
  showPreviousLayers,
  transition
}) => (
  <AnimatePresence mode="wait">
    {show && (
      <motion.div
        key="slow-layer"
        initial={{ opacity: 0, height: 0, y: -6 }}
        animate={{ opacity: 1, height: 'auto', y: 0 }}
        exit={{ opacity: 0, height: 0, y: -6 }}
        transition={getSlowLayerTransition(showPreviousLayers)}
      >
        <SlowLayer data={data} />
      </motion.div>
    )}
  </AnimatePresence>
);

// Transition configurations for each layer
const getFastLayerTransition = () => ({
  duration: 0.15,
  ease: 'easeOut',
  height: { duration: 0.1 },
  opacity: { duration: 0.15 }
});

const getMediumLayerTransition = (showFastLayer: boolean) => ({
  duration: 0.25,
  ease: 'easeOut',
  delay: showFastLayer ? 0.1 : 0,
  height: { duration: 0.2 },
  opacity: { duration: 0.25 }
});

const getSlowLayerTransition = (showPreviousLayers: boolean) => ({
  duration: 0.35,
  ease: 'easeOut',
  delay: showPreviousLayers ? 0.15 : 0,
  height: { duration: 0.3 },
  opacity: { duration: 0.35 }
});
