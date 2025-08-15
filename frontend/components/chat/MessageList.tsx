import React, { useEffect, useRef, useLayoutEffect } from 'react';
import { useUnifiedChatStore } from '@/store/unified-chat';
import { MessageItem } from './MessageItem';
import { ThinkingIndicator } from './ThinkingIndicator';
import { ScrollArea } from '@/components/ui/scroll-area';
import { motion, AnimatePresence } from 'framer-motion';

export const MessageList: React.FC = () => {
  const { messages, isProcessing } = useUnifiedChatStore();
  const scrollAreaRef = useRef<HTMLDivElement>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const isUserScrolling = useRef(false);
  const lastScrollTop = useRef(0);

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

  const displayedMessages = messages.map(msg => ({
    ...msg,
    type: msg.role === 'user' ? 'user' : msg.role === 'system' ? 'system' : 'ai',
    created_at: new Date(msg.timestamp).toISOString(),
    displayed_to_user: true
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
        
        {displayedMessages.map((msg, index) => (
          <motion.div
            key={msg.id || `msg-${index}`}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -20 }}
            transition={{ 
              duration: 0.3,
              delay: index === displayedMessages.length - 1 ? 0 : 0
            }}
          >
            <MessageItem message={msg} />
          </motion.div>
        ))}
        
        {isProcessing && (
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