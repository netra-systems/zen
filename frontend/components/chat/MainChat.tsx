"use client";

import React, { useState, useEffect } from 'react';
import { ChatHeader } from '@/components/chat/ChatHeader';
import { MessageList } from '@/components/chat/MessageList';
import { MessageInput } from '@/components/chat/MessageInput';
import { PersistentResponseCard } from '@/components/chat/PersistentResponseCard';
import { ExamplePrompts } from '@/components/chat/ExamplePrompts';
import { useUnifiedChatStore } from '@/store/unified-chat';
import { useChatWebSocket } from '@/hooks/useChatWebSocket';
import { motion, AnimatePresence } from 'framer-motion';

const MainChat: React.FC = () => {
  const { 
    isProcessing, 
    messages,
    fastLayerData,
    mediumLayerData,
    slowLayerData,
    currentRunId
  } = useUnifiedChatStore();
  
  const [isCardCollapsed, setIsCardCollapsed] = useState(false);
  
  // Connect WebSocket messages to unified chat store
  useChatWebSocket();

  const hasMessages = messages.length > 0;
  const showResponseCard = currentRunId !== null || isProcessing;

  // Auto-collapse card after completion
  useEffect(() => {
    if (slowLayerData?.finalReport && !isProcessing) {
      const timer = setTimeout(() => {
        setIsCardCollapsed(true);
      }, 2000); // 2 seconds after completion
      
      return () => clearTimeout(timer);
    }
  }, [slowLayerData?.finalReport, isProcessing]);

  // Reset collapse state when new processing starts
  useEffect(() => {
    if (isProcessing) {
      setIsCardCollapsed(false);
    }
  }, [isProcessing]);

  return (
    <div className="flex flex-col h-full bg-gradient-to-br from-gray-50 via-white to-gray-50">
      <div className="flex flex-col flex-1 max-w-full">
        {/* Chat Header */}
        <ChatHeader />
        
        {/* Main Content Area */}
        <div className="flex-grow overflow-hidden relative">
          <div className="h-full overflow-y-auto">
            {/* Example Prompts - shown when no messages */}
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
            
            {/* Message History */}
            <MessageList />
            
            {/* Persistent Response Card - Shows current processing */}
            <AnimatePresence>
              {showResponseCard && (
                <motion.div
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -20 }}
                  transition={{ duration: 0.3 }}
                  className="px-6 py-4 max-w-5xl mx-auto"
                >
                  <PersistentResponseCard
                    fastLayerData={fastLayerData}
                    mediumLayerData={mediumLayerData}
                    slowLayerData={slowLayerData}
                    isProcessing={isProcessing}
                    isCollapsed={isCardCollapsed}
                    onToggleCollapse={() => setIsCardCollapsed(!isCardCollapsed)}
                  />
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        </div>
        
        {/* Chat Input */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
          className="border-t bg-white/95 backdrop-blur-sm shadow-lg"
        >
          <div className="px-6 py-4 max-w-5xl mx-auto w-full">
            <MessageInput />
          </div>
        </motion.div>
      </div>
    </div>
  );
};

export default MainChat;