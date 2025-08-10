"use client";

import React from 'react';
import { ChatHeader } from '@/components/chat/ChatHeader';
import { MessageList } from '@/components/chat/MessageList';
import { MessageInput } from '@/components/chat/MessageInput';
import { StopButton } from '@/components/chat/StopButton';
import { ThreadSidebar } from '@/components/chat/ThreadSidebar';
import { useChatStore } from '@/store/chat';
import { useChatWebSocket } from '@/hooks/useChatWebSocket';
import { useAgent } from '@/hooks/useAgent';
import { motion, AnimatePresence } from 'framer-motion';
import { Shield, Database, Sparkles, AlertTriangle, CheckCircle } from 'lucide-react';

const AdminChat: React.FC = () => {
  const { isProcessing, messages } = useChatStore();
  const { sendUserMessage } = useAgent();
  
  // Connect WebSocket messages to chat store with admin context
  const { pendingApproval, setPendingApproval } = useChatWebSocket();

  const hasMessages = messages.filter(m => m.displayed_to_user).length > 0;

  const handleApproval = (approved: boolean) => {
    if (pendingApproval) {
      const approvalMessage = approved ? 'approve' : 'cancel';
      sendUserMessage(approvalMessage);
      setPendingApproval(null);
    }
  };

  const adminPrompts = [
    {
      icon: <Sparkles className="w-5 h-5" />,
      title: "Generate Synthetic Data",
      prompt: "Generate synthetic e-commerce workload data for the last 30 days",
      category: "synthetic"
    },
    {
      icon: <Database className="w-5 h-5" />,
      title: "Manage Corpus",
      prompt: "Search the knowledge base corpus for optimization strategies",
      category: "corpus"
    },
    {
      icon: <Sparkles className="w-5 h-5" />,
      title: "Financial Workload",
      prompt: "Generate synthetic financial services workload with high compliance requirements",
      category: "synthetic"
    },
    {
      icon: <Database className="w-5 h-5" />,
      title: "Create New Corpus",
      prompt: "Create a new corpus for product documentation",
      category: "corpus"
    }
  ];

  return (
    <div className="flex h-screen bg-gradient-to-br from-purple-50 via-white to-purple-50">
      <ThreadSidebar />
      <div className="flex flex-col flex-1 max-w-full">
        {/* Admin Header */}
        <div className="bg-gradient-to-r from-purple-600 to-indigo-600 text-white">
          <div className="px-6 py-4 flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <Shield className="w-6 h-6" />
              <h1 className="text-xl font-bold">Admin Mode</h1>
              <span className="px-2 py-1 bg-white/20 rounded-full text-xs">
                Enhanced Privileges
              </span>
            </div>
            <div className="flex items-center space-x-4 text-sm">
              <span className="flex items-center space-x-1">
                <Database className="w-4 h-4" />
                <span>Corpus Admin</span>
              </span>
              <span className="flex items-center space-x-1">
                <Sparkles className="w-4 h-4" />
                <span>Data Generation</span>
              </span>
            </div>
          </div>
        </div>
        
        <ChatHeader />
        
        <div className="flex-grow overflow-hidden relative">
          {/* Approval Banner */}
          <AnimatePresence>
            {pendingApproval && (
              <motion.div
                initial={{ height: 0, opacity: 0 }}
                animate={{ height: 'auto', opacity: 1 }}
                exit={{ height: 0, opacity: 0 }}
                className="bg-amber-50 border-b border-amber-200"
              >
                <div className="px-6 py-4">
                  <div className="flex items-start space-x-3">
                    <AlertTriangle className="w-5 h-5 text-amber-600 mt-0.5" />
                    <div className="flex-1">
                      <h3 className="font-semibold text-amber-900">Approval Required</h3>
                      <p className="text-sm text-amber-700 mt-1">
                        {pendingApproval.message}
                      </p>
                      <div className="mt-3 flex space-x-3">
                        <button
                          onClick={() => handleApproval(true)}
                          className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors flex items-center space-x-2"
                        >
                          <CheckCircle className="w-4 h-4" />
                          <span>Approve</span>
                        </button>
                        <button
                          onClick={() => handleApproval(false)}
                          className="px-4 py-2 bg-gray-600 text-white rounded-lg hover:bg-gray-700 transition-colors"
                        >
                          Cancel
                        </button>
                      </div>
                    </div>
                  </div>
                </div>
              </motion.div>
            )}
          </AnimatePresence>
          
          <div className="h-full overflow-y-auto">
            <AnimatePresence mode="wait">
              {!hasMessages && (
                <motion.div
                  initial={{ opacity: 1 }}
                  exit={{ opacity: 0, y: -20 }}
                  transition={{ duration: 0.3 }}
                  className="px-6 py-12"
                >
                  <div className="max-w-4xl mx-auto">
                    <div className="text-center mb-8">
                      <h2 className="text-2xl font-bold text-gray-900 mb-2">
                        Admin Operations Center
                      </h2>
                      <p className="text-gray-600">
                        Manage synthetic data generation and corpus administration
                      </p>
                    </div>
                    
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      {adminPrompts.map((prompt, index) => (
                        <motion.button
                          key={index}
                          initial={{ opacity: 0, y: 20 }}
                          animate={{ opacity: 1, y: 0 }}
                          transition={{ delay: index * 0.1 }}
                          onClick={() => sendUserMessage(prompt.prompt)}
                          className="p-4 bg-white rounded-lg shadow-sm hover:shadow-md transition-all border border-gray-200 hover:border-purple-300 text-left group"
                        >
                          <div className="flex items-start space-x-3">
                            <div className={`p-2 rounded-lg ${
                              prompt.category === 'synthetic' 
                                ? 'bg-purple-100 text-purple-600' 
                                : 'bg-blue-100 text-blue-600'
                            } group-hover:scale-110 transition-transform`}>
                              {prompt.icon}
                            </div>
                            <div className="flex-1">
                              <h3 className="font-semibold text-gray-900 mb-1">
                                {prompt.title}
                              </h3>
                              <p className="text-sm text-gray-600">
                                {prompt.prompt}
                              </p>
                            </div>
                          </div>
                        </motion.button>
                      ))}
                    </div>
                    
                    <div className="mt-8 p-4 bg-purple-50 rounded-lg border border-purple-200">
                      <div className="flex items-center space-x-2 text-purple-700">
                        <Shield className="w-5 h-5" />
                        <span className="font-semibold">Admin Notice</span>
                      </div>
                      <p className="text-sm text-purple-600 mt-2">
                        Operations that modify data or consume significant resources will require explicit approval.
                        All admin actions are logged for audit purposes.
                      </p>
                    </div>
                  </div>
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
              <div className="flex items-center space-x-2 text-xs text-purple-600 mb-2">
                <Shield className="w-3 h-3" />
                <span>Admin mode active - Enhanced capabilities enabled</span>
              </div>
              <MessageInput placeholder="Enter admin command or query..." />
              
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

export default AdminChat;