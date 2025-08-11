"use client";

import React from 'react';
import { motion } from 'framer-motion';
import { Zap } from 'lucide-react';
import type { FastLayerProps } from '@/types/unified-chat';

export const FastLayer: React.FC<FastLayerProps> = ({ data, isProcessing }) => {
  // Only show presence indicator if processing but no data yet
  const showPresenceIndicator = isProcessing && !data;
  
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

        {/* Right side - Active Tools with Deduplication */}
        <div className="flex items-center space-x-2">
          {data?.activeTools && data.activeTools.length > 0 && (
            <>
              {/* Deduplicate tools and show unique ones */}
              {Array.from(new Set(data.activeTools)).map((tool) => (
                <motion.div
                  key={tool}
                  initial={{ opacity: 0, scale: 0.8 }}
                  animate={{ opacity: 1, scale: 1 }}
                  exit={{ opacity: 0, scale: 0.8 }}
                  transition={{ duration: 0 }}
                  className="flex items-center space-x-1 bg-white/90 backdrop-blur-sm border border-purple-500/30 rounded-full px-3 py-1 shadow-sm hover:shadow-md transition-all duration-200 hover:scale-105"
                >
                  <Zap className="w-3 h-3 text-purple-600" />
                  <span className="text-xs font-medium text-zinc-700">{tool}</span>
                  {/* Show count if tool appears multiple times */}
                  {data.activeTools.filter(t => t === tool).length > 1 && (
                    <span className="text-xs text-purple-500 font-bold ml-1">
                      ×{data.activeTools.filter(t => t === tool).length}
                    </span>
                  )}
                </motion.div>
              ))}
            </>
          )}
        </div>
      </div>
    </div>
  );
};