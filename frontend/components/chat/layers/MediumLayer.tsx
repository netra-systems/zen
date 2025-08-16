"use client";

import React, { useEffect, useState, useRef } from 'react';
import { motion } from 'framer-motion';
import ReactMarkdown from 'react-markdown';
import type { MediumLayerProps } from '@/types/unified-chat';

export const MediumLayer: React.FC<MediumLayerProps> = ({ data }) => {
  const [displayedContent, setDisplayedContent] = useState('');
  const [isStreaming, setIsStreaming] = useState(false);
  const contentRef = useRef<string>('');
  const animationFrameRef = useRef<number>(0);
  const lastUpdateRef = useRef<number>(Date.now());
  
  // Stream content character by character using requestAnimationFrame
  useEffect(() => {
    if (!data?.partialContent) {
      setDisplayedContent('');
      contentRef.current = '';
      return;
    }

    // If content hasn't changed, don't restart streaming
    if (contentRef.current === data.partialContent) {
      return;
    }

    // New content to stream
    const targetContent = data.partialContent;
    let currentIndex = contentRef.current.length;
    
    // If new content is shorter, reset (shouldn't happen but handle it)
    if (targetContent.length < currentIndex) {
      currentIndex = 0;
      contentRef.current = '';
      setDisplayedContent('');
    }
    
    setIsStreaming(true);
    const charactersPerSecond = 30;
    const msPerCharacter = 1000 / charactersPerSecond;
    
    const streamContent = () => {
      const now = Date.now();
      const elapsed = now - lastUpdateRef.current;
      
      if (elapsed >= msPerCharacter && currentIndex < targetContent.length) {
        // Calculate how many characters to add based on elapsed time
        const charactersToAdd = Math.floor(elapsed / msPerCharacter);
        const endIndex = Math.min(currentIndex + charactersToAdd, targetContent.length);
        
        const newContent = targetContent.substring(0, endIndex);
        contentRef.current = newContent;
        setDisplayedContent(newContent);
        
        currentIndex = endIndex;
        lastUpdateRef.current = now;
      }
      
      if (currentIndex < targetContent.length) {
        animationFrameRef.current = requestAnimationFrame(streamContent);
      } else {
        setIsStreaming(false);
      }
    };
    
    animationFrameRef.current = requestAnimationFrame(streamContent);
    
    return () => {
      if (animationFrameRef.current) {
        cancelAnimationFrame(animationFrameRef.current);
      }
    };
  }, [data?.partialContent]);

  if (!data) {
    return (
      <motion.div 
        className="shadow-inner flex items-center justify-center"
        style={{ 
          minHeight: '60px',
          background: 'linear-gradient(180deg, rgba(255, 255, 255, 0.98) 0%, rgba(250, 250, 250, 0.95) 100%)',
          backdropFilter: 'blur(8px)',
          borderTop: '1px solid rgba(255, 255, 255, 0.18)',
          boxShadow: 'inset 0 2px 4px 0 rgba(0, 0, 0, 0.06)'
        }}
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ duration: 0.3 }}
      >
        <div className="text-sm text-zinc-500 italic">Waiting for agent activity...</div>
      </motion.div>
    );
  }

  return (
    <motion.div 
      className="shadow-inner"
      style={{ 
        minHeight: '100px', 
        maxHeight: '400px',
        background: 'linear-gradient(180deg, rgba(255, 255, 255, 0.98) 0%, rgba(250, 250, 250, 0.95) 100%)',
        backdropFilter: 'blur(8px)',
        borderTop: '1px solid rgba(255, 255, 255, 0.18)',
        boxShadow: 'inset 0 2px 4px 0 rgba(0, 0, 0, 0.06)'
      }}
      initial={{ opacity: 0, height: 0 }}
      animate={{ opacity: 1, height: 'auto' }}
      transition={{ duration: 0.3, ease: 'easeOut' }}
    >
      <div className="p-4 overflow-y-auto" style={{ maxHeight: '400px' }}>
        {/* Step Progress with enhanced visual feedback */}
        {data.stepNumber > 0 && data.totalSteps > 0 && (
          <motion.div 
            className="mb-4 p-3 rounded-lg bg-white/60 border border-emerald-200/50"
            whileHover={{ scale: 1.01 }}
            transition={{ duration: 0.2 }}
            initial={{ opacity: 0, y: -5 }}
            animate={{ opacity: 1, y: 0 }}
          >
            <div className="flex items-center justify-between mb-2">
              <span className="font-medium text-zinc-700 text-sm">Step {data.stepNumber} of {data.totalSteps}</span>
              <span className="text-xs font-bold text-emerald-600 bg-emerald-50 px-2 py-1 rounded-full">
                {Math.round((data.stepNumber / data.totalSteps) * 100)}%
              </span>
            </div>
            <div className="w-full h-2 bg-gray-200/50 rounded-full overflow-hidden backdrop-blur-sm">
              <motion.div
                className="h-full bg-gradient-to-r from-emerald-500 to-emerald-600 rounded-full"
                initial={{ width: 0 }}
                animate={{ width: `${(data.stepNumber / data.totalSteps) * 100}%` }}
                transition={{ duration: 0.5, ease: "easeOut" }}
              />
            </div>
            {data.totalSteps > 1 && (
              <div className="mt-1 text-xs text-zinc-500">
                {data.totalSteps - data.stepNumber} steps remaining
              </div>
            )}
          </motion.div>
        )}

        {/* Enhanced Thinking Display */}
        {data.thought && (
          <motion.div 
            className="mb-4 p-3 rounded-lg border-l-4 border-blue-400 bg-blue-50/50"
            initial={{ opacity: 0, x: -10 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.3 }}
          >
            <div className="flex items-start space-x-2">
              <div className="flex-shrink-0 mt-1">
                <motion.div
                  className="w-2 h-2 bg-blue-500 rounded-full"
                  animate={{ opacity: [1, 0.5, 1] }}
                  transition={{ duration: 1.5, repeat: Infinity }}
                />
              </div>
              <div>
                <div className="text-xs font-medium text-blue-700 mb-1">Agent Thinking</div>
                <div className="text-sm text-zinc-700 italic">{data.thought}</div>
              </div>
            </div>
          </motion.div>
        )}

        {/* Enhanced Partial Content with Streaming */}
        {displayedContent && (
          <motion.div
            className="prose prose-sm max-w-none"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.3 }}
          >
            <div className="bg-white/70 rounded-lg p-4 border border-gray-200/50">
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs font-medium text-gray-600">Partial Results</span>
                {isStreaming && (
                  <div className="flex items-center space-x-1 text-xs text-emerald-600">
                    <motion.div
                      className="w-1 h-1 bg-emerald-500 rounded-full"
                      animate={{ opacity: [1, 0, 1] }}
                      transition={{ duration: 0.8, repeat: Infinity }}
                    />
                    <span>Streaming...</span>
                  </div>
                )}
              </div>
              <ReactMarkdown 
                className="text-zinc-800"
                components={{
                  p: ({ children }) => <p className="mb-2 last:mb-0">{children}</p>,
                  code: ({ children }) => (
                    <code className="bg-gray-100 px-1 py-0.5 rounded text-xs font-mono">
                      {children}
                    </code>
                  )
                }}
              >
                {displayedContent}
              </ReactMarkdown>
              {isStreaming && (
                <motion.span
                  className="inline-block w-2 h-4 bg-emerald-500 ml-1 rounded-sm"
                  animate={{ opacity: [1, 0, 1] }}
                  transition={{ duration: 0.8, repeat: Infinity, ease: "easeInOut" }}
                  style={{ verticalAlign: 'text-bottom' }}
                />
              )}
            </div>
          </motion.div>
        )}
        
        {/* Show placeholder when no content yet */}
        {!displayedContent && !data.thought && (
          <motion.div
            className="text-center py-8"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.5 }}
          >
            <div className="text-sm text-zinc-500 italic mb-2">Processing...</div>
            <div className="flex justify-center space-x-1">
              {[0, 1, 2].map((i) => (
                <motion.div
                  key={i}
                  className="w-2 h-2 bg-emerald-400 rounded-full"
                  animate={{ opacity: [0.3, 1, 0.3] }}
                  transition={{ 
                    duration: 1.5, 
                    repeat: Infinity, 
                    delay: i * 0.2 
                  }}
                />
              ))}
            </div>
          </motion.div>
        )}
      </div>
    </motion.div>
  );
};