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

  if (!data) return null;

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
        {/* Step Progress with micro-interactions */}
        {data.stepNumber > 0 && data.totalSteps > 0 && (
          <motion.div 
            className="mb-3 flex items-center space-x-3"
            whileHover={{ scale: 1.02 }}
            transition={{ duration: 0.2 }}
          >
            <div className="flex items-center space-x-2 text-sm">
              <span className="font-medium text-zinc-700">Step {data.stepNumber} of {data.totalSteps}</span>
              <div className="w-32 h-2 bg-gray-200/50 rounded-full overflow-hidden backdrop-blur-sm">
                <motion.div
                  className="h-full bg-gradient-to-r from-emerald-500 to-emerald-600"
                  initial={{ width: 0 }}
                  animate={{ width: `${(data.stepNumber / data.totalSteps) * 100}%` }}
                  transition={{ duration: 0.3, ease: "easeOut" }}
                />
              </div>
              <span className="text-xs font-medium text-emerald-600">
                {Math.round((data.stepNumber / data.totalSteps) * 100)}%
              </span>
            </div>
          </motion.div>
        )}

        {/* Thinking/Status Text with fade animation */}
        {data.thought && (
          <motion.div 
            className="mb-3 text-sm text-zinc-600 italic"
            initial={{ opacity: 0, y: -5 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.3 }}
          >
            {data.thought}
          </motion.div>
        )}

        {/* Partial Content with Streaming */}
        {displayedContent && (
          <div className="prose prose-sm max-w-none">
            <ReactMarkdown>{displayedContent}</ReactMarkdown>
            {isStreaming && (
              <motion.span
                className="inline-block w-2 h-4 bg-emerald-500 ml-0.5 rounded-sm"
                animate={{ opacity: [1, 0, 1] }}
                transition={{ duration: 0.8, repeat: Infinity, ease: "easeInOut" }}
                style={{ verticalAlign: 'text-bottom' }}
              />
            )}
          </div>
        )}
      </div>
    </motion.div>
  );
};