/**
 * useProgressiveLoading Hook - Progressive content loading management
 * 
 * Manages skeleton to content transition with performance optimization.
 * Provides smooth fade-in transitions and loading phase management.
 * 
 * @compliance conventions.xml - Max 8 lines per function, under 100 lines
 * @compliance type_safety.xml - Strongly typed hook with clear interfaces
 */

import { useState, useEffect, useCallback, useRef } from 'react';

/**
 * Progressive loading phases
 */
export type ProgressivePhase = 'skeleton' | 'loading' | 'revealing' | 'complete';

/**
 * Loading state configuration
 */
export interface LoadingConfig {
  readonly skeletonDuration?: number;
  readonly revealDuration?: number;
  readonly fadeInDelay?: number;
  readonly enablePerformanceOptimization?: boolean;
}

/**
 * Hook return interface
 */
export interface UseProgressiveLoadingResult {
  readonly phase: ProgressivePhase;
  readonly isLoading: boolean;
  readonly shouldShowSkeleton: boolean;
  readonly shouldShowContent: boolean;
  readonly contentOpacity: number;
  readonly startLoading: () => void;
  readonly completeLoading: () => void;
  readonly resetLoading: () => void;
}

/**
 * Default configuration values
 */
const DEFAULT_CONFIG: Required<LoadingConfig> = {
  skeletonDuration: 800,
  revealDuration: 400,
  fadeInDelay: 200,
  enablePerformanceOptimization: true
};

/**
 * Creates merged configuration with defaults
 */
const createConfig = (userConfig?: LoadingConfig): Required<LoadingConfig> => ({
  ...DEFAULT_CONFIG,
  ...userConfig
});

/**
 * Manages phase transitions with timeout cleanup
 */
const usePhaseTransition = (
  phase: ProgressivePhase,
  setPhase: (phase: ProgressivePhase) => void,
  config: Required<LoadingConfig>
) => {
  const timeoutRef = useRef<NodeJS.Timeout>();
  
  const scheduleTransition = useCallback((nextPhase: ProgressivePhase, delay: number) => {
    clearTimeout(timeoutRef.current);
    timeoutRef.current = setTimeout(() => setPhase(nextPhase), delay);
  }, [setPhase]);
  
  useEffect(() => {
    return () => clearTimeout(timeoutRef.current);
  }, []);
  
  return scheduleTransition;
};

/**
 * Calculates content opacity based on phase and timing
 */
const calculateContentOpacity = (phase: ProgressivePhase, revealStarted: boolean): number => {
  if (phase === 'complete') return 1;
  if (phase === 'revealing' && revealStarted) return 1;
  return 0;
};

/**
 * Determines if skeleton should be visible
 */
const shouldShowSkeleton = (phase: ProgressivePhase): boolean => {
  return ['skeleton', 'loading'].includes(phase);
};

/**
 * Determines if content should be rendered
 */
const shouldShowContent = (phase: ProgressivePhase): boolean => {
  return ['revealing', 'complete'].includes(phase);
};

/**
 * Main progressive loading hook
 * Manages skeleton to content transition with smooth animations
 */
export const useProgressiveLoading = (config?: LoadingConfig): UseProgressiveLoadingResult => {
  const mergedConfig = createConfig(config);
  const [phase, setPhase] = useState<ProgressivePhase>('skeleton');
  const [revealStarted, setRevealStarted] = useState(false);
  
  const scheduleTransition = usePhaseTransition(phase, setPhase, mergedConfig);
  
  const startLoading = useCallback(() => {
    setPhase('loading');
    setRevealStarted(false);
  }, []);
  
  const completeLoading = useCallback(() => {
    scheduleTransition('revealing', mergedConfig.fadeInDelay);
    setTimeout(() => setRevealStarted(true), mergedConfig.fadeInDelay + 50);
    scheduleTransition('complete', mergedConfig.fadeInDelay + mergedConfig.revealDuration);
  }, [scheduleTransition, mergedConfig]);
  
  const resetLoading = useCallback(() => {
    setPhase('skeleton');
    setRevealStarted(false);
  }, []);
  
  return {
    phase,
    isLoading: phase === 'loading',
    shouldShowSkeleton: shouldShowSkeleton(phase),
    shouldShowContent: shouldShowContent(phase),
    contentOpacity: calculateContentOpacity(phase, revealStarted),
    startLoading,
    completeLoading,
    resetLoading
  };
};

/**
 * Hook for managing multiple progressive loading instances
 */
export const useMultiProgressiveLoading = (count: number, config?: LoadingConfig) => {
  const instances = Array.from({ length: count }, () => useProgressiveLoading(config));
  
  const startAll = useCallback(() => {
    instances.forEach(instance => instance.startLoading());
  }, [instances]);
  
  const completeAll = useCallback(() => {
    instances.forEach(instance => instance.completeLoading());
  }, [instances]);
  
  const resetAll = useCallback(() => {
    instances.forEach(instance => instance.resetLoading());
  }, [instances]);
  
  return { instances, startAll, completeAll, resetAll };
};

export default useProgressiveLoading;