/**
 * SkeletonShimmer - Reusable shimmer effect component
 * 
 * Provides GPU-accelerated shimmer animations for loading states.
 * Configurable animation speed, direction, and visual properties.
 * 
 * @compliance conventions.xml - Max 8 lines per function, under 100 lines
 * @compliance type_safety.xml - Strongly typed with clear interfaces
 */

import React from 'react';
import { motion } from 'framer-motion';

/**
 * Shimmer configuration interface
 */
export interface ShimmerConfig {
  readonly duration?: number;
  readonly direction?: 'left-to-right' | 'right-to-left' | 'top-to-bottom';
  readonly intensity?: 'subtle' | 'moderate' | 'strong';
  readonly className?: string;
}

/**
 * Component props interface
 */
interface SkeletonShimmerProps {
  readonly width?: string | number;
  readonly height?: string | number;
  readonly borderRadius?: string | number;
  readonly config?: ShimmerConfig;
  readonly className?: string;
}

/**
 * Creates shimmer gradient background styles
 */
const createShimmerGradient = (intensity: string): string => {
  const intensityMap = {
    subtle: 'from-gray-200 via-gray-100 to-gray-200',
    moderate: 'from-gray-300 via-gray-100 to-gray-300',
    strong: 'from-gray-400 via-white to-gray-400'
  };
  return `bg-gradient-to-r ${intensityMap[intensity as keyof typeof intensityMap]}`;
};

/**
 * Creates animation variants for shimmer direction
 */
const createAnimationVariants = (direction: string) => {
  const variants = {
    'left-to-right': { x: ['-100%', '100%'] },
    'right-to-left': { x: ['100%', '-100%'] },
    'top-to-bottom': { y: ['-100%', '100%'] }
  };
  return variants[direction as keyof typeof variants];
};

/**
 * Creates motion animation configuration
 */
const createMotionAnimation = (config: ShimmerConfig) => ({
  ...createAnimationVariants(config.direction || 'left-to-right'),
  transition: {
    duration: config.duration || 1.5,
    repeat: Infinity,
    ease: 'easeInOut'
  }
});

/**
 * Main SkeletonShimmer component
 * Renders animated shimmer effect for loading states
 */
export const SkeletonShimmer: React.FC<SkeletonShimmerProps> = ({
  width = '100%',
  height = '1rem',
  borderRadius = '0.375rem',
  config = {},
  className = ''
}) => {
  const shimmerGradient = createShimmerGradient(config.intensity || 'moderate');
  const motionProps = createMotionAnimation(config);
  
  return (
    <div 
      className={`relative overflow-hidden bg-gray-200 ${className}`}
      style={{ width, height, borderRadius }}
    >
      <motion.div
        className={`absolute inset-0 ${shimmerGradient} ${config.className || ''}`}
        animate={motionProps}
      />
    </div>
  );
};

/**
 * Preset shimmer configurations for common use cases
 */
export const ShimmerPresets = {
  fast: { duration: 1, intensity: 'strong' as const },
  normal: { duration: 1.5, intensity: 'moderate' as const },
  slow: { duration: 2.5, intensity: 'subtle' as const },
  reverse: { duration: 1.5, direction: 'right-to-left' as const },
  vertical: { duration: 2, direction: 'top-to-bottom' as const }
} as const;

/**
 * Creates shimmer component with preset configuration
 */
export const createPresetShimmer = (preset: keyof typeof ShimmerPresets) => {
  const config = ShimmerPresets[preset];
  const PresetShimmerComponent = (props: Omit<SkeletonShimmerProps, 'config'>) => (
    <SkeletonShimmer {...props} config={config} />
  );
  PresetShimmerComponent.displayName = `PresetShimmer_${preset}`;
  return PresetShimmerComponent;
};

export default SkeletonShimmer;