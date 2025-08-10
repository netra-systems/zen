"use client";

import React from 'react';
import { ChatHeader } from '@/components/chat/ChatHeader';
import { MessageList } from '@/components/chat/MessageList';
import { MessageInput } from '@/components/chat/MessageInput';
import { StopButton } from '@/components/chat/StopButton';
import { ExamplePrompts } from '@/components/chat/ExamplePrompts';
import { useChatStore } from '@/store/chat';
import { useChatWebSocket } from '@/hooks/useChatWebSocket';
import { motion, AnimatePresence } from 'framer-motion';

const MainChat: React.FC = () => {
  const { isProcessing, messages } = useChatStore();
  
  // Connect WebSocket messages to chat store
  useChatWebSocket();

  const hasMessages = messages.filter(m => m.displayed_to_user).length > 0;

  return (
    <div className="flex h-screen bg-gradient-to-br from-gray-50 via-white to-gray-50">
      <div className="flex flex-col flex-1 max-w-full">
        <ChatHeader />
        
        <div className="flex-grow overflow-hidden relative">
          <div className="absolute inset-0 bg-gradient-to-b from-transparent via-transparent to-white/50 pointer-events-none z-10" />
          
          <div className="h-full overflow-y-auto">
            <AnimatePresence mode="wait">
              {!hasMessages && (
                <motion.div
                  initial={{ opacity: 1 }}
                  exit={{ opacity: 0, y: -20 }}
                  transition={{ duration: 0.3 }}
                >
                  <ExamplePrompts />
                </motion.div>
              )}
            </AnimatePresence>
            
            <MessageList />
          </div>
        </div>
        
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
          className="border-t bg-white/95 backdrop-blur-sm shadow-lg"
        >
          <div className="px-6 py-4 max-w-5xl mx-auto w-full">
            <div className="space-y-3">
              <MessageInput />
              
              {isProcessing && (
                <motion.div
                  initial={{ opacity: 0, scale: 0.95 }}
                  animate={{ opacity: 1, scale: 1 }}
                  exit={{ opacity: 0, scale: 0.95 }}
                  transition={{ duration: 0.2 }}
                  className="flex justify-center"
                >
                  <StopButton />
                </motion.div>
              )}
            </div>
          </div>
        </motion.div>
      </div>
    </div>
  );
};

export default MainChat;