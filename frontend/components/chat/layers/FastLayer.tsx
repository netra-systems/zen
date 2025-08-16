"use client";

import React, { useMemo } from 'react';
import { motion } from 'framer-motion';
import { Zap } from 'lucide-react';
import { useToolTracking } from '@/hooks/useToolTracking';
import type { FastLayerProps } from '@/types/component-props';
import type { ToolStatus } from '@/types/layer-types';

export const FastLayer: React.FC<FastLayerProps> = ({ data, isProcessing }) => {
  // Initialize tool tracking service
  useToolTracking({ autoRemovalTimeoutMs: 30000 });
  
  // Show presence indicator if processing, agent name when available
  const showPresenceIndicator = isProcessing && !data;
  const showAgentName = data?.agentName;
  const showActivityIndicator = isProcessing && data;
  
  return (
    <div 
      className="h-12 flex items-center px-4 text-zinc-800"
      style={{ 
        height: '48px',
        background: 'rgba(255, 255, 255, 0.95)',
        backdropFilter: 'blur(12px)',
        borderBottom: '1px solid rgba(255, 255, 255, 0.18)',
        boxShadow: '0 2px 8px 0 rgba(31, 38, 135, 0.07)'
      }}
    >
      <div className="flex items-center justify-between w-full">
        {/* Left side - Agent name and presence indicator */}
        <div className="flex items-center space-x-3">
          {/* Activity Indicator - Shows when agent is active */}
          {(showPresenceIndicator || showActivityIndicator) && (
            <motion.div
              animate={{ scale: [1, 1.2, 1] }}
              transition={{ duration: 1.5, repeat: Infinity, ease: "easeInOut" }}
              className="flex items-center relative"
            >
              <div className="w-2 h-2 bg-emerald-500 rounded-full" />
              <div className="w-2 h-2 bg-emerald-500 rounded-full absolute animate-ping" />
            </motion.div>
          )}
          
          {/* Agent Name - Always show if available */}
          {showAgentName && (
            <motion.span
              initial={{ opacity: 0, x: -10 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.3 }}
              className="font-semibold text-sm text-zinc-800"
            >
              {data.agentName}
            </motion.span>
          )}
          
          {/* Fallback indicator when processing but no agent name yet */}
          {isProcessing && !showAgentName && (
            <motion.span
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ duration: 0.3 }}
              className="text-sm text-zinc-600 italic"
            >
              Starting agent...
            </motion.span>
          )}
        </div>

        {/* Right side - Active Tools with Enhanced Display */}
        <div className="flex items-center space-x-2">
          <ToolDisplay data={data} />
          
        </div>
      </div>
    </div>
  );
};

/**
 * Gets active tools from enhanced tool statuses or legacy array
 */
const getActiveTools = (data: any): string[] => {
  if (data?.toolStatuses) {
    return data.toolStatuses
      .filter((status: ToolStatus) => status.isActive)
      .map((status: ToolStatus) => status.name);
  }
  return data?.activeTools || [];
};

/**
 * Calculates tool duration for display
 */
const getToolDuration = (status: ToolStatus): string => {
  const duration = Date.now() - status.startTime;
  if (duration < 1000) return '< 1s';
  return `${Math.floor(duration / 1000)}s`;
};

/**
 * Tool display component with enhanced lifecycle info
 */
const ToolDisplay: React.FC<{ data: any }> = ({ data }) => {
  const activeTools = useMemo(() => getActiveTools(data), [data]);
  const uniqueTools = useMemo(() => Array.from(new Set(activeTools)), [activeTools]);
  
  if (uniqueTools.length === 0) {
    return <ProcessingIndicator data={data} />;
  }
  
  return (
    <>
      {uniqueTools.map((tool) => (
        <ToolBadge
          key={tool}
          tool={tool}
          count={activeTools.filter(t => t === tool).length}
          status={data?.toolStatuses?.find((s: ToolStatus) => s.name === tool)}
        />
      ))}
    </>
  );
};

/**
 * Individual tool badge component
 */
const ToolBadge: React.FC<{ 
  tool: string; 
  count: number; 
  status?: ToolStatus; 
}> = ({ tool, count, status }) => {
  return (
    <motion.div
      key={tool}
      initial={{ opacity: 0, scale: 0.8, x: 10 }}
      animate={{ opacity: 1, scale: 1, x: 0 }}
      exit={{ opacity: 0, scale: 0.8, x: 10 }}
      transition={{ duration: 0.2 }}
      className="flex items-center space-x-1 bg-white/90 backdrop-blur-sm border border-purple-500/30 rounded-full px-3 py-1 shadow-sm hover:shadow-md transition-all duration-200 hover:scale-105"
    >
      <Zap className="w-3 h-3 text-purple-600" />
      <span className="text-xs font-medium text-zinc-700">{tool}</span>
      {status && (
        <span className="text-xs text-purple-400 ml-1">
          {getToolDuration(status)}
        </span>
      )}
      {count > 1 && (
        <span className="text-xs text-purple-500 font-bold ml-1">
          ×{count}
        </span>
      )}
    </motion.div>
  );
};

/**
 * Processing indicator when no tools active
 */
const ProcessingIndicator: React.FC<{ data: any }> = ({ data }) => {
  if (!data || (!data.activeTools?.length && !data.toolStatuses?.length)) {
    return (
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        className="flex items-center space-x-1 text-xs text-zinc-500"
      >
        <div className="w-1 h-1 bg-zinc-400 rounded-full animate-pulse" />
        <span>Initializing...</span>
      </motion.div>
    );
  }
  return null;
};