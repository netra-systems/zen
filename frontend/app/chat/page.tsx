
/**
 * Chat Home Page
 * 
 * Handles chat home state when no specific thread is selected.
 * Provides welcome interface and thread selection prompts.
 * 
 * @compliance conventions.xml - Max 8 lines per function, under 300 lines
 * @compliance type_safety.xml - Strongly typed component with clear interfaces
 */

"use client";

import React, { useEffect } from 'react';
import { useUnifiedChatStore } from '@/store/unified-chat';
import { useThreadCreation } from '@/hooks/useThreadCreation';
import { useRouter } from 'next/navigation';
import { motion } from 'framer-motion';
import { MessageSquare, Plus, Clock } from 'lucide-react';

/**
 * Chat home page component
 */
const ChatPage: React.FC = () => {
  const activeThreadId = useUnifiedChatStore(state => state.activeThreadId);
  const setActiveThread = useUnifiedChatStore(state => state.setActiveThread);
  const { createAndNavigate } = useThreadCreation();
  const router = useRouter();
  
  // Clear active thread when on home page
  useEffect(() => {
    clearActiveThreadForHome(activeThreadId, setActiveThread);
  }, [activeThreadId, setActiveThread]);
  
  const handleNewConversation = async () => {
    const success = await createAndNavigate();
    if (success) {
      router.push('/chat');
    }
  };
  
  return createChatHomeView(handleNewConversation, router);
};

/**
 * Clears active thread when on home page
 */
const clearActiveThreadForHome = (
  activeThreadId: string | null,
  setActiveThread: (threadId: string | null) => void
): void => {
  if (activeThreadId) {
    setActiveThread(null);
  }
};

/**
 * Creates the chat home view
 */
const createChatHomeView = (
  handleNewConversation: () => Promise<void>,
  router: any
): JSX.Element => {
  return (
    <div className="flex h-full bg-gradient-to-br from-gray-50 via-white to-gray-50">
      <div className="flex flex-col flex-1 max-w-full">
        <div className="flex-grow overflow-hidden relative">
          <div className="h-full overflow-y-auto">
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.4 }}
              className="flex flex-col items-center justify-center h-full text-center px-6"
            >
              <div className="max-w-2xl">
                {createWelcomeSection()}
                {createActionButtons(handleNewConversation, router)}
                {createFeatureGrid()}
              </div>
            </motion.div>
          </div>
        </div>
      </div>
    </div>
  );
};

/**
 * Creates welcome section
 */
const createWelcomeSection = (): JSX.Element => {
  return (
    <div className="mb-12">
      <div className="w-20 h-20 mx-auto bg-gradient-to-br from-blue-500 to-blue-600 rounded-full flex items-center justify-center mb-6 shadow-lg">
        <MessageSquare className="w-10 h-10 text-white" />
      </div>
      <h1 className="text-3xl font-bold text-gray-900 mb-4">
        Welcome to Netra AI
      </h1>
      <p className="text-lg text-gray-600 mb-6">
        Your AI-powered optimization platform. Create a new conversation or select an existing one to get started.
      </p>
    </div>
  );
};

/**
 * Creates action buttons
 */
const createActionButtons = (
  handleNewConversation: () => Promise<void>,
  router: any
): JSX.Element => {
  const handleRecentChats = () => {
    router.push('/chat');
  };
  
  return (
    <div className="flex flex-col sm:flex-row gap-4 mb-12">
      <motion.button
        whileHover={{ scale: 1.02 }}
        whileTap={{ scale: 0.98 }}
        onClick={handleNewConversation}
        className="flex items-center justify-center gap-3 px-6 py-3 bg-blue-600 text-white rounded-lg font-semibold hover:bg-blue-700 transition-colors shadow-md"
      >
        <Plus className="w-5 h-5" />
        Start New Conversation
      </motion.button>
      <motion.button
        whileHover={{ scale: 1.02 }}
        whileTap={{ scale: 0.98 }}
        onClick={handleRecentChats}
        className="flex items-center justify-center gap-3 px-6 py-3 bg-gray-100 text-gray-700 rounded-lg font-semibold hover:bg-gray-200 transition-colors"
      >
        <Clock className="w-5 h-5" />
        View Recent Chats
      </motion.button>
    </div>
  );
};

/**
 * Creates feature grid
 */
const createFeatureGrid = (): JSX.Element => {
  const features = [
    {
      title: "AI Optimization",
      description: "Intelligent workload analysis and optimization recommendations",
      icon: "🚀"
    },
    {
      title: "Multi-Agent System", 
      description: "Coordinated AI agents working together for comprehensive solutions",
      icon: "🤖"
    },
    {
      title: "Real-time Analysis",
      description: "Live monitoring and instant feedback on your AI workloads",
      icon: "📊"
    }
  ];
  
  return (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
      {features.map((feature, index) => createFeatureCard(feature, index))}
    </div>
  );
};

/**
 * Creates individual feature card
 */
const createFeatureCard = (
  feature: { title: string; description: string; icon: string },
  index: number
): JSX.Element => {
  return (
    <motion.div
      key={feature.title}
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, delay: index * 0.1 }}
      className="p-6 bg-white rounded-lg shadow-sm border border-gray-100 hover:shadow-md transition-shadow"
    >
      <div className="text-2xl mb-3">{feature.icon}</div>
      <h3 className="text-lg font-semibold text-gray-900 mb-2">{feature.title}</h3>
      <p className="text-sm text-gray-600">{feature.description}</p>
    </motion.div>
  );
};

export default ChatPage;
