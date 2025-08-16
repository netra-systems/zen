"use client";

import React, { useEffect } from 'react';
import { motion } from 'framer-motion';
import { ChevronUp, ChevronDown } from 'lucide-react';
import { cn } from '@/lib/utils';
import type { CollapseFeatureProps } from '@/types/component-props';
import type { SlowLayerData } from '@/types/layer-types';

interface CollapsedSummaryProps {
  slowLayerData: SlowLayerData;
  isAdminAction: boolean;
  onToggleCollapse: () => void;
}

export const CollapsedSummary: React.FC<CollapsedSummaryProps> = ({
  slowLayerData,
  isAdminAction,
  onToggleCollapse
}) => {
  if (!slowLayerData?.finalReport) return null;

  return (
    <motion.div
      initial={{ opacity: 0, height: 0 }}
      animate={{ opacity: 1, height: 'auto' }}
      exit={{ opacity: 0, height: 0 }}
      transition={{ duration: 0.3 }}
      className={cn(
        "bg-white rounded-lg shadow-lg overflow-hidden border",
        isAdminAction ? "border-purple-200" : "border-gray-200"
      )}
    >
      <SummaryHeader
        isAdminAction={isAdminAction}
        slowLayerData={slowLayerData}
        onToggleCollapse={onToggleCollapse}
      />
    </motion.div>
  );
};

const SummaryHeader: React.FC<{
  isAdminAction: boolean;
  slowLayerData: SlowLayerData;
  onToggleCollapse: () => void;
}> = ({ isAdminAction, slowLayerData, onToggleCollapse }) => (
  <div 
    className={cn(
      "px-4 py-3 backdrop-blur-md cursor-pointer flex items-center justify-between transition-colors duration-200",
      isAdminAction 
        ? "glass-accent-purple hover:bg-purple-50/30 border-b border-purple-200"
        : "bg-white/95 border-b border-emerald-500/20 hover:bg-emerald-50/50"
    )}
    onClick={onToggleCollapse}
  >
    <SummaryContent isAdminAction={isAdminAction} slowLayerData={slowLayerData} />
    <ChevronDown className="w-5 h-5" />
  </div>
);

const SummaryContent: React.FC<{
  isAdminAction: boolean;
  slowLayerData: SlowLayerData;
}> = ({ isAdminAction, slowLayerData }) => (
  <div className="flex items-center space-x-3">
    <AdminBadge isAdminAction={isAdminAction} />
    <StatusIndicator />
    <SummaryText isAdminAction={isAdminAction} slowLayerData={slowLayerData} />
  </div>
);

const AdminBadge: React.FC<{ isAdminAction: boolean }> = ({ isAdminAction }) => {
  if (!isAdminAction) return null;
  
  return (
    <div className="flex items-center space-x-2 px-2 py-1 bg-purple-100 rounded-md">
      <span className="text-xs font-medium text-purple-700">Admin</span>
    </div>
  );
};

const StatusIndicator: React.FC = () => (
  <div className="w-2 h-2 bg-emerald-500 rounded-full animate-pulse" />
);

const SummaryText: React.FC<{
  isAdminAction: boolean;
  slowLayerData: SlowLayerData;
}> = ({ isAdminAction, slowLayerData }) => (
  <>
    <span className="font-medium text-zinc-900">
      {isAdminAction ? 'Admin Operation Complete' : 'Analysis Complete'}
    </span>
    <span className="text-sm opacity-90">
      {slowLayerData.completedAgents.length} agents • {formatDuration(slowLayerData.totalDuration)}
    </span>
  </>
);

interface CollapseHeaderProps {
  isCollapsed: boolean;
  isAdminAction: boolean;
  onToggleCollapse: () => void;
  showHeader: boolean;
}

export const CollapseHeader: React.FC<CollapseHeaderProps> = ({
  isCollapsed,
  isAdminAction,
  onToggleCollapse,
  showHeader
}) => {
  if (!showHeader) return null;

  return (
    <div 
      className="px-4 py-2 bg-gray-50 border-b border-gray-200 cursor-pointer flex items-center justify-between hover:bg-gray-100 transition-colors"
      onClick={onToggleCollapse}
    >
      <HeaderText isCollapsed={isCollapsed} isAdminAction={isAdminAction} />
      <HeaderIcon isCollapsed={isCollapsed} />
    </div>
  );
};

const HeaderText: React.FC<{
  isCollapsed: boolean;
  isAdminAction: boolean;
}> = ({ isCollapsed, isAdminAction }) => (
  <span className="text-sm text-gray-600">
    {isCollapsed ? 'Expand' : 'Collapse'} {isAdminAction ? 'Admin Operation' : 'Analysis'}
  </span>
);

const HeaderIcon: React.FC<{ isCollapsed: boolean }> = ({ isCollapsed }) => (
  isCollapsed ? <ChevronDown className="w-4 h-4" /> : <ChevronUp className="w-4 h-4" />
);

// Auto-collapse hook with proper delay
export const useAutoCollapse = (
  isProcessing: boolean,
  hasCompletedAgents: boolean,
  onCollapse: () => void,
  delay: number = 2000
) => {
  useEffect(() => {
    if (!isProcessing && hasCompletedAgents) {
      const timer = setTimeout(() => {
        onCollapse();
      }, delay);
      
      return () => clearTimeout(timer);
    }
  }, [isProcessing, hasCompletedAgents, onCollapse, delay]);
};

// Utility function
const formatDuration = (ms: number): string => {
  if (ms < 1000) return `${ms}ms`;
  return `${Math.round(ms / 1000)}s`;
};
