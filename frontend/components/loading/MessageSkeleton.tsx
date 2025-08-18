/**
 * MessageSkeleton - Message skeleton component with shimmer effects
 * 
 * Provides immediate visual feedback during content loading.
 * Supports different skeleton types (user, AI, agent card) with progressive content revelation.
 * 
 * @compliance conventions.xml - Max 8 lines per function, under 150 lines
 * @compliance type_safety.xml - Strongly typed with clear interfaces
 */

import React from 'react';
import { motion } from 'framer-motion';
import { Card, CardContent, CardHeader } from '@/components/ui/card';
import { Avatar, AvatarFallback } from '@/components/ui/avatar';
import { SkeletonShimmer, ShimmerPresets } from './SkeletonShimmer';

/**
 * Skeleton type variants
 */
export type SkeletonType = 'user' | 'ai' | 'agent-card' | 'thinking' | 'tool-execution';

/**
 * Progressive loading phases
 */
export type LoadingPhase = 'structure' | 'header' | 'content' | 'complete';

/**
 * Component props interface
 */
interface MessageSkeletonProps {
  readonly type: SkeletonType;
  readonly phase?: LoadingPhase;
  readonly showAvatar?: boolean;
  readonly showTimestamp?: boolean;
  readonly className?: string;
}

/**
 * Creates skeleton layout configuration by type
 */
const createSkeletonConfig = (type: SkeletonType) => ({
  user: { alignment: 'justify-end', bgColor: 'bg-white/95', borderColor: 'border-emerald-200' },
  ai: { alignment: 'justify-start', bgColor: 'bg-white', borderColor: 'border-gray-200' },
  'agent-card': { alignment: 'justify-start', bgColor: 'bg-blue-50', borderColor: 'border-blue-200' },
  thinking: { alignment: 'justify-start', bgColor: 'bg-purple-50', borderColor: 'border-purple-200' },
  'tool-execution': { alignment: 'justify-start', bgColor: 'bg-yellow-50', borderColor: 'border-yellow-200' }
}[type]);

/**
 * Creates avatar configuration by type
 */
const createAvatarConfig = (type: SkeletonType) => ({
  user: { fallback: 'U', bgColor: 'bg-emerald-500' },
  ai: { fallback: 'AI', bgColor: 'bg-gradient-to-r from-purple-600 to-pink-600' },
  'agent-card': { fallback: 'A', bgColor: 'bg-blue-500' },
  thinking: { fallback: 'T', bgColor: 'bg-purple-500' },
  'tool-execution': { fallback: 'T', bgColor: 'bg-yellow-500' }
}[type]);

/**
 * Creates content lines configuration by skeleton type
 */
const createContentLines = (type: SkeletonType) => {
  const configs = {
    user: [{ width: '80%' }, { width: '60%' }],
    ai: [{ width: '95%' }, { width: '85%' }, { width: '70%' }],
    'agent-card': [{ width: '90%' }, { width: '75%' }, { width: '85%' }, { width: '60%' }],
    thinking: [{ width: '70%' }, { width: '50%' }],
    'tool-execution': [{ width: '85%' }, { width: '75%' }, { width: '65%' }]
  };
  return configs[type] || configs.ai;
};

/**
 * Renders skeleton avatar with shimmer effect
 */
const renderSkeletonAvatar = (type: SkeletonType, showAvatar: boolean) => {
  if (!showAvatar) return null;
  const config = createAvatarConfig(type);
  
  return (
    <Avatar className="w-9 h-9 border-2 border-white shadow-sm">
      <AvatarFallback className={`${config.bgColor} text-white opacity-50`}>
        <SkeletonShimmer 
          width="100%" 
          height="100%" 
          borderRadius="50%" 
          config={ShimmerPresets.fast}
        />
      </AvatarFallback>
    </Avatar>
  );
};

/**
 * Renders skeleton header section
 */
const renderSkeletonHeader = (type: SkeletonType, showAvatar: boolean, showTimestamp: boolean) => (
  <div className="flex items-start justify-between">
    <div className="flex items-center space-x-3">
      {renderSkeletonAvatar(type, showAvatar)}
      <div className="space-y-2">
        <SkeletonShimmer width="120px" height="16px" config={ShimmerPresets.normal} />
        {type === 'agent-card' && (
          <SkeletonShimmer width="80px" height="12px" config={ShimmerPresets.normal} />
        )}
      </div>
    </div>
    {showTimestamp && (
      <SkeletonShimmer width="60px" height="12px" config={ShimmerPresets.slow} />
    )}
  </div>
);

/**
 * Renders skeleton content lines
 */
const renderSkeletonContent = (type: SkeletonType) => {
  const lines = createContentLines(type);
  
  return (
    <div className="space-y-3">
      {lines.map((line, index) => (
        <SkeletonShimmer
          key={`line-${index}`}
          width={line.width}
          height="16px"
          config={{
            ...ShimmerPresets.normal,
            duration: 1.5 + (index * 0.3)
          }}
        />
      ))}
    </div>
  );
};

/**
 * Creates animation variants for skeleton entrance
 */
const createSkeletonAnimation = () => ({
  initial: { opacity: 0, y: 20, scale: 0.95 },
  animate: { opacity: 1, y: 0, scale: 1 },
  exit: { opacity: 0, y: -20, scale: 0.95 },
  transition: { duration: 0.4, ease: 'easeOut' }
});

/**
 * Main MessageSkeleton component
 * Renders skeleton placeholder for messages during loading
 */
export const MessageSkeleton: React.FC<MessageSkeletonProps> = ({
  type,
  phase = 'structure',
  showAvatar = true,
  showTimestamp = true,
  className = ''
}) => {
  const skeletonConfig = createSkeletonConfig(type);
  const animationProps = createSkeletonAnimation();
  
  return (
    <motion.div
      {...animationProps}
      className={`mb-4 flex ${skeletonConfig.alignment} ${className}`}
    >
      <Card className={`
        w-full max-w-3xl shadow-sm 
        ${skeletonConfig.bgColor} ${skeletonConfig.borderColor}
        border animate-pulse
      `}>
        <CardHeader className="pb-3 pt-4 px-5">
          {renderSkeletonHeader(type, showAvatar, showTimestamp)}
        </CardHeader>
        
        <CardContent className="px-5 pb-4">
          {phase !== 'structure' && renderSkeletonContent(type)}
          
          {type === 'agent-card' && phase === 'content' && (
            <div className="mt-4 pt-3 border-t border-gray-100">
              <SkeletonShimmer width="150px" height="14px" config={ShimmerPresets.slow} />
            </div>
          )}
        </CardContent>
      </Card>
    </motion.div>
  );
};

/**
 * Preset skeleton configurations for common scenarios
 */
export const SkeletonPresets = {
  userMessage: { type: 'user' as const, showAvatar: true, showTimestamp: true },
  aiResponse: { type: 'ai' as const, showAvatar: true, showTimestamp: true },
  agentCard: { type: 'agent-card' as const, showAvatar: true, showTimestamp: false },
  thinking: { type: 'thinking' as const, showAvatar: false, showTimestamp: false },
  toolExecution: { type: 'tool-execution' as const, showAvatar: false, showTimestamp: true }
} as const;

export default MessageSkeleton;