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
      className="h-12 flex items-center px-4 bg-white/95 backdrop-blur-md border-b border-gray-200 text-zinc-800"
      style={{ height: '48px' }}
    >
      <div className="flex items-center justify-between w-full">
        {/* Left side - Agent name and presence indicator */}
        <div className="flex items-center space-x-3">
          {/* Presence Indicator - ONLY frontend-generated visual */}
          {showPresenceIndicator && (
            <motion.div
              animate={{ scale: [1, 1.2, 1] }}
              transition={{ duration: 1.5, repeat: Infinity, ease: "easeInOut" }}
              className="flex items-center"
            >
              <div className="w-2 h-2 bg-emerald-500 rounded-full" />
              <div className="w-2 h-2 bg-emerald-500 rounded-full absolute animate-ping" />
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
                  className="flex items-center space-x-1 bg-white border border-emerald-500/30 rounded-full px-3 py-1 shadow-sm hover:shadow-md transition-shadow duration-200"
                >
                  <Zap className="w-3 h-3 text-emerald-600" />
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