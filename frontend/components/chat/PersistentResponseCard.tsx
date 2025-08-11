"use client";

import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { ChevronUp, ChevronDown } from 'lucide-react';
import { FastLayer } from '@/components/chat/layers/FastLayer';
import { MediumLayer } from '@/components/chat/layers/MediumLayer';
import { SlowLayer } from '@/components/chat/layers/SlowLayer';
import type { PersistentResponseCardProps } from '@/types/unified-chat';

export const PersistentResponseCard: React.FC<PersistentResponseCardProps> = ({
  fastLayerData,
  mediumLayerData,
  slowLayerData,
  isProcessing,
  isCollapsed = false,
  onToggleCollapse,
}) => {
  // Determine which layers to show based on data availability
  const showFastLayer = isProcessing || fastLayerData !== null;
  const showMediumLayer = mediumLayerData !== null;
  const showSlowLayer = slowLayerData !== null;

  // Summary view when collapsed
  if (isCollapsed && slowLayerData?.finalReport) {
    return (
      <motion.div
        initial={{ opacity: 0, height: 0 }}
        animate={{ opacity: 1, height: 'auto' }}
        exit={{ opacity: 0, height: 0 }}
        transition={{ duration: 0.3 }}
        className="bg-white rounded-lg shadow-lg overflow-hidden border border-gray-200"
      >
        <div 
          className="px-4 py-3 bg-gradient-to-r from-blue-500 to-blue-600 text-white cursor-pointer flex items-center justify-between"
          onClick={onToggleCollapse}
        >
          <div className="flex items-center space-x-3">
            <div className="w-2 h-2 bg-green-400 rounded-full animate-pulse" />
            <span className="font-medium">Analysis Complete</span>
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
      className="bg-white rounded-lg shadow-lg overflow-hidden border border-gray-200"
    >
      {/* Collapse/Expand Header (only shown when there's a final report) */}
      {slowLayerData?.finalReport && onToggleCollapse && (
        <div 
          className="px-4 py-2 bg-gray-50 border-b border-gray-200 cursor-pointer flex items-center justify-between hover:bg-gray-100 transition-colors"
          onClick={onToggleCollapse}
        >
          <span className="text-sm text-gray-600">
            {isCollapsed ? 'Expand' : 'Collapse'} Analysis
          </span>
          {isCollapsed ? <ChevronDown className="w-4 h-4" /> : <ChevronUp className="w-4 h-4" />}
        </div>
      )}

      {/* Fast Layer - Immediate Feedback (0-100ms) */}
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

      {/* Medium Layer - Progressive Updates (100ms-1s) */}
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

      {/* Slow Layer - Complete Results (1s+) */}
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
    </motion.div>
  );
};