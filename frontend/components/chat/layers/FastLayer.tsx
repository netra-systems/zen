"use client";

import React from 'react';
import { motion } from 'framer-motion';
import { Activity, Zap } from 'lucide-react';
import type { FastLayerProps } from '@/types/unified-chat';

export const FastLayer: React.FC<FastLayerProps> = ({ data, isProcessing }) => {
  // Only show presence indicator if processing but no data yet
  const showPresenceIndicator = isProcessing && !data;
  
  return (
    <div 
      className="h-12 flex items-center px-4 bg-gradient-to-r from-blue-500 to-blue-600 text-white"
      style={{ height: '48px' }}
    >
      <div className="flex items-center justify-between w-full">
        {/* Left side - Agent name and presence indicator */}
        <div className="flex items-center space-x-3">
          {/* Presence Indicator - ONLY frontend-generated visual */}
          {showPresenceIndicator && (
            <motion.div
              animate={{ rotate: 360 }}
              transition={{ duration: 1, repeat: Infinity, ease: "linear" }}
            >
              <Activity className="w-4 h-4 opacity-80" />
            </motion.div>
          )}
          
          {/* Agent Name from backend */}
          {data?.agentName && (
            <motion.span
              initial={{ opacity: 0, x: -10 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0 }}
              className="font-semibold text-sm"
            >
              {data.agentName}
            </motion.span>
          )}
        </div>

        {/* Right side - Active Tools */}
        <div className="flex items-center space-x-2">
          {data?.activeTools && data.activeTools.length > 0 && (
            <>
              {data.activeTools.map((tool, index) => (
                <motion.div
                  key={`${tool}-${index}`}
                  initial={{ opacity: 0, scale: 0.8 }}
                  animate={{ opacity: 1, scale: 1 }}
                  exit={{ opacity: 0, scale: 0.8 }}
                  transition={{ duration: 0 }}
                  className="flex items-center space-x-1 bg-white/20 rounded-full px-2 py-1"
                >
                  <Zap className="w-3 h-3" />
                  <span className="text-xs font-medium">{tool}</span>
                </motion.div>
              ))}
            </>
          )}
        </div>
      </div>
    </div>
  );
};