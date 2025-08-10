import React, { useEffect, useRef, useLayoutEffect } from 'react';
import { useChatStore } from '@/store/chat';
import { MessageItem } from './MessageItem';
import { ThinkingIndicator } from './ThinkingIndicator';
import { ScrollArea } from '@/components/ui/scroll-area';
import { motion, AnimatePresence } from 'framer-motion';

export const MessageList: React.FC = () => {
  const { messages, isProcessing } = useChatStore();
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

  const displayedMessages = messages.filter((msg) => msg.displayed_to_user);

  return (
    <ScrollArea ref={scrollAreaRef} className="h-[calc(100vh-250px)] px-6 py-4 overflow-y-auto">
      <AnimatePresence initial={false}>
        {displayedMessages.length === 0 && (
          <motion.div
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
                <h2 className="text-3xl font-bold bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent">
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
        
        <div className="space-y-2">
          {displayedMessages.map((msg, index) => (
            <motion.div
              key={msg.id}
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
        </div>
        
        {isProcessing && (
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            className="flex justify-start mt-4"
          >
            <div className="bg-white border border-gray-200 rounded-lg shadow-sm p-4 max-w-xs">
              <div className="flex items-center space-x-3">
                <div className="flex space-x-1">
                  <motion.div
                    animate={{ scale: [1, 1.2, 1] }}
                    transition={{ duration: 0.6, repeat: Infinity, delay: 0 }}
                    className="w-2 h-2 bg-blue-500 rounded-full"
                  />
                  <motion.div
                    animate={{ scale: [1, 1.2, 1] }}
                    transition={{ duration: 0.6, repeat: Infinity, delay: 0.2 }}
                    className="w-2 h-2 bg-blue-500 rounded-full"
                  />
                  <motion.div
                    animate={{ scale: [1, 1.2, 1] }}
                    transition={{ duration: 0.6, repeat: Infinity, delay: 0.4 }}
                    className="w-2 h-2 bg-blue-500 rounded-full"
                  />
                </div>
                <span className="text-sm text-gray-600">Agent is thinking...</span>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
      
      <div ref={messagesEndRef} className="h-4" />
    </ScrollArea>
  );
};