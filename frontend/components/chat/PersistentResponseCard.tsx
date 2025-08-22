"use client";

import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { cn } from '@/lib/utils';
import type { PersistentResponseCardProps } from '@/types/component-props';
import type { SlowLayerData } from '@/types/layer-types';
import { AdminHeader, AdminResults } from '@/components/chat/features/AdminFeatures';
import { CollapsedSummary, CollapseHeader, useAutoCollapse } from '@/components/chat/features/CollapseController';
import { LayerManager } from '@/components/chat/features/LayerManager';
import { DEFAULT_UNIFIED_CHAT_CONFIG } from '@/types/component-props';
import { useUnifiedChatStore } from '@/store/unified-chat';
import AgentStatusIndicator from './AgentStatusIndicator';
import { useAgentUpdates, type UseAgentUpdatesReturn } from '@/hooks/useAgentUpdates';
import { agentUpdateStream } from '@/services/agent-update-stream';

export const PersistentResponseCard: React.FC<PersistentResponseCardProps> = ({
  fastLayerData,
  mediumLayerData,
  slowLayerData,
  isProcessing,
  isCollapsed = false,
  onToggleCollapse,
}) => {
  const { adminConfig, isAdminAction } = useAdminDetection(slowLayerData);
  const hasCompletedAgents = Boolean(slowLayerData?.completedAgents?.length);
  const [progressState, setProgressState] = useState({ progress: 0, isAnimating: false });
  
  // Initialize continuous agent updates
  const agentUpdates = useAgentUpdates({
    enablePerformanceMonitoring: true,
    onUpdate: handleAgentUpdate
  });
  
  // Auto-collapse with proper delay
  useAutoCollapse(
    isProcessing,
    hasCompletedAgents,
    () => onToggleCollapse?.(),
    DEFAULT_UNIFIED_CHAT_CONFIG.autoCollapseDelay
  );
  
  // Handle continuous agent updates
  function handleAgentUpdate(update: any): void {
    if (update.progress) {
      setProgressState({ progress: update.progress, isAnimating: true });
    }
  }
  
  // Sync with WebSocket events for continuous updates
  useEffect(() => {
    if (isProcessing) {
      agentUpdateStream.start();
    }
    
    return () => {
      if (!isProcessing) {
        agentUpdateStream.stop();
      }
    };
  }, [isProcessing]);

  // Show collapsed summary when appropriate
  if (isCollapsed && slowLayerData?.finalReport) {
    return (
      <CollapsedSummary
        slowLayerData={slowLayerData}
        isAdminAction={isAdminAction}
        onToggleCollapse={onToggleCollapse!}
      />
    );
  }

  return (
    <>
      <ResponseCardContainer isAdminAction={isAdminAction} isCollapsed={isCollapsed}>
        <AdminSection
          isAdminAction={isAdminAction}
          adminConfig={adminConfig}
          isProcessing={isProcessing}
          slowLayerData={slowLayerData}
        />
        <ProgressIndicatorSection
          progressState={progressState}
          isProcessing={isProcessing}
          isCollapsed={isCollapsed}
        />
        <CollapseSection
          showHeader={Boolean(slowLayerData?.finalReport && onToggleCollapse)}
          isCollapsed={isCollapsed}
          isAdminAction={isAdminAction}
          onToggleCollapse={onToggleCollapse!}
        />
        <LayersSection
          fastLayerData={fastLayerData}
          mediumLayerData={mediumLayerData}
          slowLayerData={slowLayerData}
          isProcessing={isProcessing}
          isCollapsed={isCollapsed}
        />
      </ResponseCardContainer>
      
      {isProcessing && (
        <AgentStatusIndicator
          position="top-right"
          showProgress={true}
          showToolExecution={true}
          compact={false}
        />
      )}
    </>
  );
};

const ResponseCardContainer: React.FC<{
  isAdminAction: boolean;
  isCollapsed: boolean;
  children: React.ReactNode;
}> = ({ isAdminAction, isCollapsed, children }) => (
  <motion.div
    initial={{ opacity: 0, y: 20 }}
    animate={{ opacity: 1, y: 0 }}
    exit={{ opacity: 0, y: -20 }}
    transition={{ duration: 0.3 }}
    className={cn(
      "bg-white rounded-lg shadow-lg overflow-hidden border",
      isAdminAction ? "border-purple-200" : "border-gray-200"
    )}
    role="region"
    aria-label="response card"
    data-testid="response-card"
    data-collapsed={isCollapsed.toString()}
  >
    {children}
  </motion.div>
);

const AdminSection: React.FC<{
  isAdminAction: boolean;
  adminConfig: any;
  isProcessing: boolean;
  slowLayerData: any;
}> = ({ isAdminAction, adminConfig, isProcessing, slowLayerData }) => {
  if (!isAdminAction) return null;
  
  const adminStatus = getAdminStatus(isProcessing, slowLayerData);
  const adminMetadata = getAdminMetadata(slowLayerData);
  
  return (
    <>
      <AdminHeader
        adminType={adminConfig.type}
        adminStatus={adminStatus}
        adminMetadata={adminMetadata}
      />
      <AdminResults
        adminType={adminConfig.type}
        adminStatus={adminStatus}
        adminMetadata={adminMetadata}
      />
    </>
  );
};

const CollapseSection: React.FC<{
  showHeader: boolean;
  isCollapsed: boolean;
  isAdminAction: boolean;
  onToggleCollapse: () => void;
}> = ({ showHeader, isCollapsed, isAdminAction, onToggleCollapse }) => (
  <CollapseHeader
    showHeader={showHeader}
    isCollapsed={isCollapsed}
    isAdminAction={isAdminAction}
    onToggleCollapse={onToggleCollapse}
  />
);

const ProgressIndicatorSection: React.FC<{
  progressState: { progress: number; isAnimating: boolean };
  isProcessing: boolean;
  isCollapsed: boolean;
}> = ({ progressState, isProcessing, isCollapsed }) => {
  if (isCollapsed || !isProcessing) return null;
  
  return (
    <motion.div
      initial={{ opacity: 0, height: 0 }}
      animate={{ opacity: 1, height: 'auto' }}
      exit={{ opacity: 0, height: 0 }}
      className="px-4 pb-2"
    >
      <ContinuousProgressBar
        progress={progressState.progress}
        isAnimating={progressState.isAnimating}
      />
    </motion.div>
  );
};

const LayersSection: React.FC<{
  fastLayerData: any;
  mediumLayerData: any;
  slowLayerData: any;
  isProcessing: boolean;
  isCollapsed: boolean;
}> = ({ fastLayerData, mediumLayerData, slowLayerData, isProcessing, isCollapsed }) => {
  if (isCollapsed) return null;
  
  return (
    <LayerManager
      fastLayerData={fastLayerData}
      mediumLayerData={mediumLayerData}
      slowLayerData={slowLayerData}
      isProcessing={isProcessing}
      transitions={DEFAULT_UNIFIED_CHAT_CONFIG.layerTransitions}
    />
  );
};

// Custom hooks and utilities
const useAdminDetection = (slowLayerData: any) => {
  const adminAgents = ['corpus_manager', 'synthetic_generator', 'user_admin', 'system_configurator', 'log_analyzer'];
  const isAdminAction = slowLayerData?.completedAgents?.some((agent: any) => 
    agent?.agentName && adminAgents.includes(agent.agentName.toLowerCase())
  ) || false;
  
  const adminConfig = determineAdminConfig(slowLayerData);
  
  return { adminConfig, isAdminAction };
};

const determineAdminConfig = (slowLayerData: any) => {
  if (!slowLayerData?.completedAgents) return null;
  
  const agents = slowLayerData.completedAgents
    .filter((a: any) => a?.agentName)
    .map((a: any) => a.agentName.toLowerCase());
    
  if (agents.includes('corpus_manager')) return { type: 'corpus' };
  if (agents.includes('synthetic_generator')) return { type: 'synthetic' };
  if (agents.includes('user_admin')) return { type: 'users' };
  if (agents.includes('system_configurator')) return { type: 'config' };
  if (agents.includes('log_analyzer')) return { type: 'logs' };
  
  return null;
};

const getAdminStatus = (isProcessing: boolean, slowLayerData: any): string => {
  if (isProcessing) return 'in_progress';
  if (slowLayerData) return 'completed';
  return 'pending';
};

const getAdminMetadata = (slowLayerData: any) => {
  return slowLayerData?.finalReport?.technical_details || null;
};

const ContinuousProgressBar: React.FC<{
  progress: number;
  isAnimating: boolean;
}> = ({ progress, isAnimating }) => {
  return (
    <div className="w-full bg-gray-200 rounded-full h-1 overflow-hidden">
      <motion.div
        className="h-full bg-gradient-to-r from-blue-500 to-purple-600"
        initial={{ width: 0 }}
        animate={{ 
          width: `${Math.min(Math.max(progress, 0), 100)}%`,
          scale: isAnimating ? [1, 1.02, 1] : 1
        }}
        transition={{ 
          width: { duration: 0.5, ease: 'easeOut' },
          scale: { duration: 0.3, ease: 'easeInOut' }
        }}
      />
    </div>
  );
};