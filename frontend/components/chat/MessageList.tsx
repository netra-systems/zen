import React, { useEffect, useRef, useLayoutEffect } from 'react';
import { useUnifiedChatStore } from '@/store/unified-chat';
import { MessageItem } from './MessageItem';
import { ThinkingIndicator } from './ThinkingIndicator';
import { MessageSkeleton, SkeletonPresets } from '../loading/MessageSkeleton';
import { ScrollArea } from '@/components/ui/scroll-area';
import { motion, AnimatePresence } from 'framer-motion';
import { useProgressiveLoading } from '@/hooks/useProgressiveLoading';

export const MessageList: React.FC = () => {
  const { messages, isProcessing, isThreadLoading, currentRunId } = useUnifiedChatStore();
  const scrollAreaRef = useRef<HTMLDivElement>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const isUserScrolling = useRef(false);
  const lastScrollTop = useRef(0);
  const pendingMessageRef = useRef<string | null>(null);
  
  // Progressive loading for pending messages
  const {
    shouldShowSkeleton,
    shouldShowContent,
    contentOpacity,
    startLoading,
    completeLoading
  } = useProgressiveLoading({
    skeletonDuration: 800,
    revealDuration: 300,
    fadeInDelay: 100
  });

  const scrollToBottom = (smooth = true) => {
    if (messagesEndRef.current && !isUserScrolling.current) {
      messagesEndRef.current.scrollIntoView({ 
        behavior: smooth ? 'smooth' : 'auto',
        block: 'end'
      });
    }
  };

  useEffect(() => {
    const handleScroll = () => {
      if (scrollAreaRef.current) {
        const { scrollTop, scrollHeight, clientHeight } = scrollAreaRef.current;
        const isAtBottom = scrollHeight - scrollTop - clientHeight < 100;
        
        if (scrollTop < lastScrollTop.current && !isAtBottom) {
          isUserScrolling.current = true;
        } else if (isAtBottom) {
          isUserScrolling.current = false;
        }
        
        lastScrollTop.current = scrollTop;
      }
    };

    const scrollElement = scrollAreaRef.current;
    if (scrollElement) {
      scrollElement.addEventListener('scroll', handleScroll);
    }

    return () => {
      if (scrollElement) {
        scrollElement.removeEventListener('scroll', handleScroll);
      }
    };
  }, []);

  useLayoutEffect(() => {
    scrollToBottom();
  }, [messages]);

  // Handle progressive loading for new messages
  useEffect(() => {
    if (isProcessing && !pendingMessageRef.current) {
      pendingMessageRef.current = currentRunId || 'pending';
      startLoading();
    } else if (!isProcessing && pendingMessageRef.current) {
      completeLoading();
      pendingMessageRef.current = null;
    }
  }, [isProcessing, currentRunId, startLoading, completeLoading]);

  // Helper function to determine skeleton type based on processing state
  const determineSkeletonType = () => {
    if (isThreadLoading) return 'ai';
    if (currentRunId) return 'agent-card';
    return 'ai';
  };

  // Render skeleton for pending AI response
  const renderPendingSkeleton = () => {
    if (!shouldShowSkeleton) return null;
    
    return (
      <motion.div
        key="pending-skeleton"
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        exit={{ opacity: 0, y: -20 }}
        transition={{ duration: 0.3 }}
      >
        <MessageSkeleton
          type={determineSkeletonType()}
          phase="content"
          showAvatar={true}
          showTimestamp={false}
          className="animate-pulse"
        />
      </motion.div>
    );
  };

  const safeStringify = (obj: any): string => {
    try {
      return JSON.stringify(obj, (key, value) => {
        if (value && typeof value === 'object') {
          if (value.constructor === Object || Array.isArray(value)) {
            return value;
          }
          // Handle other object types (Date, RegExp, etc.)
          return `[${value.constructor?.name || 'Object'}]`;
        }
        if (typeof value === 'function') {
          return '[Function]';
        }
        if (typeof value === 'symbol') {
          return '[Symbol]';
        }
        return value;
      });
    } catch (error) {
      // Fallback for circular references and other JSON.stringify errors
      return '[Complex Object - Unable to stringify]';
    }
  };

  const displayedMessages = messages.map(msg => ({
    id: msg.id,
    type: msg.role === 'user' ? 'user' : msg.role === 'system' ? 'system' : 'ai',
    content: typeof msg.content === 'string' 
      ? msg.content 
      : (msg.content?.text || safeStringify(msg.content)),
    sub_agent_name: msg.metadata?.agentName || null,
    created_at: (() => {
      try {
        return msg.timestamp ? new Date(msg.timestamp).toISOString() : new Date().toISOString();
      } catch {
        return new Date().toISOString();
      }
    })(),
    displayed_to_user: true,
    tool_info: null,
    raw_data: msg.metadata || null,
    references: [],
    error: null
  }));

  return (
    <ScrollArea ref={scrollAreaRef} className="h-[calc(100vh-250px)] px-6 py-4 overflow-y-auto">
      <AnimatePresence initial={false}>
        {displayedMessages.length === 0 && (
          <motion.div
            key="empty-state"
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.95 }}
            transition={{ duration: 0.3 }}
            className="flex justify-center items-center h-full min-h-[400px]"
          >
            <div className="text-center space-y-3">
              <motion.div
                initial={{ y: -20 }}
                animate={{ y: 0 }}
                transition={{ delay: 0.1 }}
              >
                <h2 className="text-3xl font-bold bg-gradient-to-r from-emerald-600 to-purple-600 bg-clip-text text-transparent">
                  Welcome to Netra AI
                </h2>
              </motion.div>
              <motion.p
                initial={{ y: 20 }}
                animate={{ y: 0 }}
                transition={{ delay: 0.2 }}
                className="text-gray-500 max-w-md mx-auto"
              >
                Start optimizing your AI workloads by typing a message or selecting an example prompt below
              </motion.p>
            </div>
          </motion.div>
        )}
        
        {displayedMessages.map((msg, index) => {
          const isLatestMessage = index === displayedMessages.length - 1;
          const shouldApplyProgressive = isLatestMessage && shouldShowContent;
          
          return (
            <motion.div
              key={msg.id || `msg-${index}`}
              initial={{ opacity: 0, y: 20 }}
              animate={{ 
                opacity: shouldApplyProgressive ? contentOpacity : 1, 
                y: 0 
              }}
              exit={{ opacity: 0, y: -20 }}
              transition={{ 
                duration: shouldApplyProgressive ? 0.6 : 0.3,
                delay: index === displayedMessages.length - 1 ? 0 : 0,
                ease: 'easeOut'
              }}
            >
              <MessageItem message={msg} />
            </motion.div>
          );
        })}
        
        {/* Render skeleton for pending messages */}
        {isProcessing && renderPendingSkeleton()}
        
        {/* Fallback thinking indicator for older browsers or when skeletons are disabled */}
        {isProcessing && !shouldShowSkeleton && (
          <motion.div
            key="thinking-indicator"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
          >
            <ThinkingIndicator type="thinking" />
          </motion.div>
        )}
      </AnimatePresence>
      
      <div ref={messagesEndRef} className="h-4" />
    </ScrollArea>
  );
};