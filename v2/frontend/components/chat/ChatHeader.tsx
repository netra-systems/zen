import React from 'react';
import { useChatStore } from '@/store/chat';
import { Bot, Zap, Activity, Shield, Database, Cpu, Brain } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

export const ChatHeader: React.FC = () => {
  const { subAgentName, subAgentStatus, isProcessing } = useChatStore();

  const getStatusColor = (status: string) => {
    switch (status?.toLowerCase()) {
      case 'running':
      case 'active':
        return 'text-green-500';
      case 'pending':
      case 'waiting':
        return 'text-yellow-500';
      case 'error':
      case 'failed':
        return 'text-red-500';
      default:
        return 'text-gray-500';
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status?.toLowerCase()) {
      case 'running':
      case 'active':
        return <Activity className="w-4 h-4" />;
      case 'analyzing':
        return <Brain className="w-4 h-4" />;
      case 'processing':
        return <Cpu className="w-4 h-4" />;
      default:
        return <Zap className="w-4 h-4" />;
    }
  };

  const getAgentIcon = () => {
    if (subAgentName?.toLowerCase().includes('security')) {
      return <Shield className="w-6 h-6 text-purple-500" />;
    } else if (subAgentName?.toLowerCase().includes('data')) {
      return <Database className="w-6 h-6 text-indigo-500" />;
    } else if (subAgentName?.toLowerCase().includes('optimization')) {
      return <Cpu className="w-6 h-6 text-green-500" />;
    }
    return <Bot className="w-6 h-6 text-blue-500" />;
  };

  return (
    <div className="border-b bg-gradient-to-r from-gray-50 to-white shadow-sm">
      <div className="px-6 py-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-4">
            <motion.div
              initial={{ scale: 0.8, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              transition={{ duration: 0.3 }}
              className="relative"
            >
              {getAgentIcon()}
              {isProcessing && (
                <motion.div
                  animate={{ scale: [1, 1.2, 1] }}
                  transition={{ duration: 1, repeat: Infinity }}
                  className="absolute -top-1 -right-1 w-3 h-3 bg-green-500 rounded-full"
                />
              )}
            </motion.div>
            
            <div>
              <h1 className="text-xl font-bold text-gray-900">
                {subAgentName || 'Netra AI Agent'}
              </h1>
              {subAgentStatus && (
                <motion.p
                  initial={{ opacity: 0, y: -5 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.1 }}
                  className="text-xs text-gray-500 mt-0.5"
                >
                  Intelligent AI Optimization Platform
                </motion.p>
              )}
            </div>
          </div>
          
          <AnimatePresence>
            {subAgentStatus && (
              <motion.div
                initial={{ opacity: 0, x: 20 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: 20 }}
                transition={{ duration: 0.3 }}
                className="flex items-center space-x-6"
              >
                <div className="flex items-center space-x-2 px-3 py-1.5 bg-white rounded-lg border border-gray-200">
                  <div className={`${getStatusColor(typeof subAgentStatus === 'object' && subAgentStatus !== null && 'lifecycle' in subAgentStatus ? subAgentStatus.lifecycle : 'IDLE')}`}>
                    {getStatusIcon(typeof subAgentStatus === 'object' && subAgentStatus !== null && 'lifecycle' in subAgentStatus ? subAgentStatus.lifecycle : 'IDLE')}
                  </div>
                  <span className="text-sm font-medium text-gray-700 capitalize">
                    {(typeof subAgentStatus === 'object' && subAgentStatus !== null && 'lifecycle' in subAgentStatus ? subAgentStatus.lifecycle : subAgentStatus) || 'Ready'}
                  </span>
                  {isProcessing && (
                    <motion.div
                      animate={{ rotate: 360 }}
                      transition={{ duration: 1, repeat: Infinity, ease: "linear" }}
                      className="w-3 h-3"
                    >
                      <Activity className="w-3 h-3 text-blue-500" />
                    </motion.div>
                  )}
                </div>
                
                {/* Tools display commented out - SubAgentState doesn't have tools property
                {subAgentStatus.tools && subAgentStatus.tools.length > 0 && (
                  <div className="flex items-center space-x-2">
                    <Terminal className="w-4 h-4 text-gray-400" />
                    <div className="flex flex-wrap gap-1">
                      {subAgentStatus.tools.slice(0, 3).map((tool, index) => (
                        <motion.span
                          key={tool}
                          initial={{ opacity: 0, scale: 0.8 }}
                          animate={{ opacity: 1, scale: 1 }}
                          transition={{ delay: index * 0.1 }}
                          className="px-2 py-0.5 text-xs font-medium bg-blue-100 text-blue-700 rounded-full"
                        >
                          {tool}
                        </motion.span>
                      ))}
                      {subAgentStatus.tools.length > 3 && (
                        <span className="px-2 py-0.5 text-xs font-medium bg-gray-100 text-gray-600 rounded-full">
                          +{subAgentStatus.tools.length - 3}
                        </span>
                      )}
                    </div>
                  </div>
                )} */}
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </div>
    </div>
  );
};