"use client";

import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { ChevronUp, ChevronDown, Shield, Database, Sparkles, Users, Settings, FileText, CheckCircle, Loader2 } from 'lucide-react';
import { FastLayer } from '@/components/chat/layers/FastLayer';
import { MediumLayer } from '@/components/chat/layers/MediumLayer';
import { SlowLayer } from '@/components/chat/layers/SlowLayer';
import type { PersistentResponseCardProps } from '@/types/unified-chat';
import { cn } from '@/lib/utils';

// Extended props for admin features are now part of the base PersistentResponseCardProps
// Admin features are conditionally shown based on message metadata and user permissions

const ADMIN_TYPE_CONFIG = {
  corpus: {
    icon: Database,
    color: 'purple',
    label: 'Corpus Management'
  },
  synthetic: {
    icon: Sparkles,
    color: 'indigo',
    label: 'Synthetic Data'
  },
  users: {
    icon: Users,
    color: 'blue',
    label: 'User Management'
  },
  config: {
    icon: Settings,
    color: 'gray',
    label: 'System Configuration'
  },
  logs: {
    icon: FileText,
    color: 'green',
    label: 'Log Analysis'
  }
};

export const PersistentResponseCard: React.FC<PersistentResponseCardProps> = ({
  fastLayerData,
  mediumLayerData,
  slowLayerData,
  isProcessing,
  isCollapsed = false,
  onToggleCollapse,
}) => {
  // Admin features are now integrated through the agent system
  // Check if this is an admin operation based on agent names
  const adminAgents = ['corpus_manager', 'synthetic_generator', 'user_admin', 'system_configurator', 'log_analyzer'];
  const isAdminAction = slowLayerData?.completedAgents?.some(agent => 
    adminAgents.includes(agent.agentName.toLowerCase())
  ) || false;
  
  // Determine admin type from agent names
  const getAdminType = () => {
    if (!slowLayerData?.completedAgents) return undefined;
    const agents = slowLayerData.completedAgents.map(a => a.agentName.toLowerCase());
    if (agents.includes('corpus_manager')) return 'corpus';
    if (agents.includes('synthetic_generator')) return 'synthetic';
    if (agents.includes('user_admin')) return 'users';
    if (agents.includes('system_configurator')) return 'config';
    if (agents.includes('log_analyzer')) return 'logs';
    return undefined;
  };
  
  const adminType = getAdminType();
  const adminStatus = isProcessing ? 'in_progress' : slowLayerData ? 'completed' : 'pending';
  const adminMetadata = slowLayerData?.finalReport?.technical_details;
  const showFastLayer = isProcessing || fastLayerData !== null;
  const showMediumLayer = mediumLayerData !== null;
  const showSlowLayer = slowLayerData !== null;

  const adminConfig = adminType ? ADMIN_TYPE_CONFIG[adminType] : null;
  const AdminIcon = adminConfig?.icon || Shield;

  // Summary view when collapsed
  if (isCollapsed && slowLayerData?.finalReport) {
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
        <div 
          className={cn(
            "px-4 py-3 backdrop-blur-md cursor-pointer flex items-center justify-between transition-colors duration-200",
            isAdminAction 
              ? "bg-gradient-to-r from-purple-50 to-indigo-50 hover:from-purple-100 hover:to-indigo-100 border-b border-purple-200"
              : "bg-white/95 border-b border-emerald-500/20 hover:bg-emerald-50/50"
          )}
          onClick={onToggleCollapse}
        >
          <div className="flex items-center space-x-3">
            {isAdminAction && (
              <div className="flex items-center space-x-2 px-2 py-1 bg-purple-100 rounded-md">
                <AdminIcon className="w-4 h-4 text-purple-600" />
                <span className="text-xs font-medium text-purple-700">Admin</span>
              </div>
            )}
            <div className="w-2 h-2 bg-emerald-500 rounded-full animate-pulse" />
            <span className="font-medium text-zinc-900">
              {isAdminAction ? `${adminConfig?.label} Complete` : 'Analysis Complete'}
            </span>
            <span className="text-sm opacity-90">
              {slowLayerData.completedAgents.length} agents • {Math.round(slowLayerData.totalDuration / 1000)}s
            </span>
          </div>
          <ChevronDown className="w-5 h-5" />
        </div>
      </motion.div>
    );
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -20 }}
      transition={{ duration: 0.3 }}
      className={cn(
        "bg-white rounded-lg shadow-lg overflow-hidden border",
        isAdminAction ? "border-purple-200" : "border-gray-200"
      )}
    >
      {/* Admin Header Badge */}
      {isAdminAction && (
        <div className="bg-gradient-to-r from-purple-600 to-indigo-600 text-white px-4 py-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <div className="flex items-center space-x-2 px-3 py-1 bg-white/20 rounded-full">
                <AdminIcon className="w-4 h-4" />
                <span className="text-sm font-medium">{adminConfig?.label}</span>
              </div>
              <Shield className="w-4 h-4 opacity-60" />
              <span className="text-xs opacity-80">Admin Operation</span>
            </div>
            
            {/* Status Indicator */}
            <div className="flex items-center space-x-2">
              {adminStatus === 'in_progress' && (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  <span className="text-sm">Processing...</span>
                </>
              )}
              {adminStatus === 'completed' && (
                <>
                  <CheckCircle className="w-4 h-4" />
                  <span className="text-sm">Completed</span>
                </>
              )}
            </div>
          </div>

          {/* Progress Bar for Admin Operations */}
          {adminMetadata?.totalRecords && adminMetadata?.recordsProcessed && (
            <div className="mt-3">
              <div className="flex items-center justify-between text-xs mb-1">
                <span>Progress</span>
                <span>{adminMetadata.recordsProcessed} / {adminMetadata.totalRecords}</span>
              </div>
              <div className="w-full bg-white/20 rounded-full h-2">
                <motion.div
                  initial={{ width: 0 }}
                  animate={{ width: `${(adminMetadata.recordsProcessed / adminMetadata.totalRecords) * 100}%` }}
                  transition={{ duration: 0.5 }}
                  className="bg-white rounded-full h-2"
                />
              </div>
              {adminMetadata.estimatedTime && (
                <p className="text-xs mt-1 opacity-80">ETA: {adminMetadata.estimatedTime}</p>
              )}
            </div>
          )}
        </div>
      )}

      {/* Collapse/Expand Header */}
      {slowLayerData?.finalReport && onToggleCollapse && (
        <div 
          className="px-4 py-2 bg-gray-50 border-b border-gray-200 cursor-pointer flex items-center justify-between hover:bg-gray-100 transition-colors"
          onClick={onToggleCollapse}
        >
          <span className="text-sm text-gray-600">
            {isCollapsed ? 'Expand' : 'Collapse'} {isAdminAction ? 'Admin Operation' : 'Analysis'}
          </span>
          {isCollapsed ? <ChevronDown className="w-4 h-4" /> : <ChevronUp className="w-4 h-4" />}
        </div>
      )}

      {/* Fast Layer */}
      <AnimatePresence>
        {showFastLayer && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 48 }}
            exit={{ opacity: 0, height: 0 }}
            transition={{ duration: 0 }}
          >
            <FastLayer 
              data={fastLayerData} 
              isProcessing={isProcessing}
            />
          </motion.div>
        )}
      </AnimatePresence>

      {/* Medium Layer */}
      <AnimatePresence>
        {showMediumLayer && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            transition={{ duration: 0.3, ease: 'easeOut' }}
          >
            <MediumLayer data={mediumLayerData} />
          </motion.div>
        )}
      </AnimatePresence>

      {/* Slow Layer */}
      <AnimatePresence>
        {showSlowLayer && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            transition={{ duration: 0.4, ease: 'easeOut', delay: 0.1 }}
          >
            <SlowLayer 
              data={slowLayerData} 
              isCollapsed={isCollapsed}
            />
          </motion.div>
        )}
      </AnimatePresence>

      {/* Admin Action Results and Options */}
      {isAdminAction && adminMetadata && adminStatus === 'completed' && (
        <div className="p-4 bg-purple-50 border-t border-purple-200">
          <div className="space-y-3">
            {/* Audit Trail */}
            {adminMetadata.auditInfo && (
              <div className="text-xs text-purple-700">
                <p>Performed by: {adminMetadata.auditInfo.user}</p>
                <p>At: {adminMetadata.auditInfo.timestamp}</p>
                <p>Action: {adminMetadata.auditInfo.action}</p>
              </div>
            )}

            {/* Action Buttons */}
            <div className="flex items-center space-x-2">
              {adminMetadata.rollbackAvailable && (
                <button className="px-3 py-1 text-xs bg-white text-purple-600 border border-purple-300 rounded-md hover:bg-purple-50 transition-colors">
                  Rollback
                </button>
              )}
              <button className="px-3 py-1 text-xs bg-white text-purple-600 border border-purple-300 rounded-md hover:bg-purple-50 transition-colors">
                View Details
              </button>
              <button className="px-3 py-1 text-xs bg-white text-purple-600 border border-purple-300 rounded-md hover:bg-purple-50 transition-colors">
                Export Log
              </button>
            </div>

            {/* Next Steps Suggestions */}
            <div className="pt-2 border-t border-purple-200">
              <p className="text-xs font-medium text-purple-900 mb-1">Suggested Next Steps:</p>
              <ul className="text-xs text-purple-700 space-y-1">
                {adminType === 'corpus' && (
                  <>
                    <li>• Validate corpus integrity</li>
                    <li>• Generate test queries</li>
                    <li>• Review corpus coverage</li>
                  </>
                )}
                {adminType === 'synthetic' && (
                  <>
                    <li>• Analyze generated patterns</li>
                    <li>• Run performance tests</li>
                    <li>• Export data for analysis</li>
                  </>
                )}
                {adminType === 'users' && (
                  <>
                    <li>• Send welcome emails</li>
                    <li>• Review permission assignments</li>
                    <li>• Generate access report</li>
                  </>
                )}
              </ul>
            </div>
          </div>
        </div>
      )}
    </motion.div>
  );
};