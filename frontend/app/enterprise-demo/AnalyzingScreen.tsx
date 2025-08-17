'use client';

import { Card, CardContent } from '@/components/ui/card';
import { Brain } from 'lucide-react';
import { motion } from 'framer-motion';

const AnalyzingScreen = () => {
  const renderStatusGrid = () => (
    <div className="grid grid-cols-4 gap-4 pt-4">
      <div className="text-center">
        <div className="text-lg font-bold text-purple-600">Triage</div>
        <div className="text-xs text-gray-500">Complete</div>
      </div>
      <div className="text-center">
        <div className="text-lg font-bold text-blue-600">Analysis</div>
        <div className="text-xs text-gray-500">In Progress</div>
      </div>
      <div className="text-center">
        <div className="text-lg font-bold text-gray-400">Optimize</div>
        <div className="text-xs text-gray-400">Pending</div>
      </div>
      <div className="text-center">
        <div className="text-lg font-bold text-gray-400">Report</div>
        <div className="text-xs text-gray-400">Pending</div>
      </div>
    </div>
  );

  const renderLogOutput = () => (
    <div className="bg-gray-50 rounded-lg p-4 font-mono text-xs text-left max-h-40 overflow-y-auto">
      <div className="text-green-600">[TRIAGE] Request categorized: Cost Optimization</div>
      <div className="text-blue-600">[DATA] Analyzing 10,000 workload events...</div>
      <div className="text-purple-600">[PATTERN] Detected peak usage: 10AM-2PM, 7PM-9PM</div>
      <div className="text-yellow-600">[INSIGHT] Opportunity: 42% cost reduction via model routing</div>
    </div>
  );

  return (
    <motion.div
      key="analyzing"
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -20 }}
      className="max-w-4xl mx-auto py-20"
    >
      <Card className="border-2 border-blue-200">
        <CardContent className="p-12 text-center space-y-6">
          <motion.div
            animate={{ scale: [1, 1.1, 1] }}
            transition={{ duration: 1.5, repeat: Infinity }}
            className="w-20 h-20 mx-auto"
          >
            <Brain className="w-20 h-20 text-blue-600" />
          </motion.div>
          
          <h2 className="text-2xl font-bold text-gray-900">
            Analyzing & Optimizing
          </h2>
          <p className="text-gray-600 max-w-2xl mx-auto">
            Our AI agents are analyzing your workload patterns and identifying
            optimization opportunities...
          </p>
          
          {renderStatusGrid()}
          {renderLogOutput()}
        </CardContent>
      </Card>
    </motion.div>
  );
};

export default AnalyzingScreen;