"use client";

import React, { useEffect, useState, useRef } from 'react';
import { motion } from 'framer-motion';
import ReactMarkdown from 'react-markdown';
import type { MediumLayerProps } from '@/types/unified-chat';

export const MediumLayer: React.FC<MediumLayerProps> = ({ data }) => {
  const [displayedContent, setDisplayedContent] = useState('');
  const [isStreaming, setIsStreaming] = useState(false);
  const contentRef = useRef<string>('');
  const animationFrameRef = useRef<number>();
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
    <div 
      className="bg-white border-t border-gray-100"
      style={{ minHeight: '100px', maxHeight: '400px' }}
    >
      <div className="p-4 overflow-y-auto" style={{ maxHeight: '400px' }}>
        {/* Step Progress */}
        {data.stepNumber > 0 && data.totalSteps > 0 && (
          <div className="mb-3 flex items-center space-x-3">
            <div className="flex items-center space-x-2 text-sm text-gray-600">
              <span className="font-medium">Step {data.stepNumber} of {data.totalSteps}</span>
              <div className="w-32 h-2 bg-gray-200 rounded-full overflow-hidden">
                <motion.div
                  className="h-full bg-blue-500"
                  initial={{ width: 0 }}
                  animate={{ width: `${(data.stepNumber / data.totalSteps) * 100}%` }}
                  transition={{ duration: 0.3 }}
                />
              </div>
            </div>
          </div>
        )}

        {/* Thinking/Status Text */}
        {data.thought && (
          <div className="mb-3 text-sm text-gray-700 italic">
            {data.thought}
          </div>
        )}

        {/* Partial Content with Streaming */}
        {displayedContent && (
          <div className="prose prose-sm max-w-none">
            <ReactMarkdown>{displayedContent}</ReactMarkdown>
            {isStreaming && (
              <motion.span
                className="inline-block w-1 h-4 bg-gray-800 ml-0.5"
                animate={{ opacity: [1, 0] }}
                transition={{ duration: 0.5, repeat: Infinity }}
                style={{ verticalAlign: 'text-bottom' }}
              />
            )}
          </div>
        )}
      </div>
    </div>
  );
};