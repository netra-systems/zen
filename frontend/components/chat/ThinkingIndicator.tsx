import React from 'react';
import { motion } from 'framer-motion';
import { Brain, Sparkles, Cpu, Loader2 } from 'lucide-react';

interface ThinkingIndicatorProps {
  type?: 'thinking' | 'processing' | 'analyzing' | 'optimizing';
  message?: string;
}

export const ThinkingIndicator: React.FC<ThinkingIndicatorProps> = ({ 
  type = 'thinking',
  message 
}) => {
  const getIcon = () => {
    switch (type) {
      case 'processing':
        return <Cpu className="w-5 h-5 text-blue-500" />;
      case 'analyzing':
        return <Sparkles className="w-5 h-5 text-purple-500" />;
      case 'optimizing':
        return <Loader2 className="w-5 h-5 text-green-500 animate-spin" />;
      default:
        return <Brain className="w-5 h-5 text-blue-500" />;
    }
  };

  const getMessage = () => {
    if (message) return message;
    switch (type) {
      case 'processing':
        return 'Processing request...';
      case 'analyzing':
        return 'Analyzing data...';
      case 'optimizing':
        return 'Optimizing solution...';
      default:
        return 'Agent is thinking...';
    }
  };

  const getColorScheme = () => {
    switch (type) {
      case 'processing':
        return 'from-emerald-400 to-teal-400';
      case 'analyzing':
        return 'from-purple-400 to-pink-400';
      case 'optimizing':
        return 'from-green-400 to-emerald-400';
      default:
        return 'from-purple-400 to-indigo-400';
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 10, scale: 0.95 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      exit={{ opacity: 0, y: -10, scale: 0.95 }}
      transition={{ duration: 0.3, ease: 'easeOut' }}
      className="flex justify-start mt-4 mb-4"
      data-testid="thinking-indicator"
    >
      <div className="relative">
        <div className={`absolute inset-0 bg-gradient-to-r opacity-20 blur-xl rounded-2xl ${getColorScheme()}`} />
        
        <div className="relative bg-white border border-gray-200 rounded-2xl shadow-lg p-4 max-w-sm">
          <div className="flex items-center space-x-3">
            <motion.div
              animate={{ rotate: type === 'optimizing' ? 0 : [0, 10, -10, 0] }}
              transition={{ duration: 1.5, repeat: Infinity }}
            >
              {getIcon()}
            </motion.div>
            
            <div className="flex items-center space-x-2">
              <div className="flex space-x-1">
                {[0, 0.2, 0.4].map((delay, i) => (
                  <motion.div
                    key={i}
                    animate={{ 
                      scale: [1, 1.3, 1],
                      opacity: [0.5, 1, 0.5]
                    }}
                    transition={{ 
                      duration: 0.8, 
                      repeat: Infinity, 
                      delay,
                      ease: "easeInOut"
                    }}
                    className={`w-2 h-2 rounded-full bg-gradient-to-r ${getColorScheme()}`}
                  />
                ))}
              </div>
              
              <motion.span
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: 0.2 }}
                className="text-sm font-medium text-gray-700"
              >
                {getMessage()}
              </motion.span>
            </div>
          </div>
          
          <motion.div
            className="mt-2 h-1 bg-gray-100 rounded-full overflow-hidden"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.3 }}
          >
            <motion.div
              className={`h-full bg-gradient-to-r ${getColorScheme()}`}
              animate={{ x: ['-100%', '100%'] }}
              transition={{ 
                duration: 1.5, 
                repeat: Infinity,
                ease: "linear"
              }}
              style={{ width: '50%' }}
            />
          </motion.div>
        </div>
      </div>
    </motion.div>
  );
};