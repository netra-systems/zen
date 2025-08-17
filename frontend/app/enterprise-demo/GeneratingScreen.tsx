'use client';

import { Card, CardContent } from '@/components/ui/card';
import { Progress } from '@/components/ui/progress';
import { Sparkles } from 'lucide-react';
import { motion } from 'framer-motion';

interface GeneratingScreenProps {
  selectedWorkload: string | null;
}

const GeneratingScreen = ({ selectedWorkload }: GeneratingScreenProps) => {
  const renderProgressSection = () => (
    <div className="space-y-2 max-w-md mx-auto">
      <div className="flex justify-between text-sm">
        <span>Data Generation</span>
        <span className="font-mono">10,000 records</span>
      </div>
      <Progress value={75} className="h-2" />
    </div>
  );

  const renderStatsGrid = () => (
    <div className="grid grid-cols-3 gap-4 pt-4">
      <div className="text-center">
        <div className="text-2xl font-bold text-purple-600">10K</div>
        <div className="text-xs text-gray-500">Records Generated</div>
      </div>
      <div className="text-center">
        <div className="text-2xl font-bold text-green-600">100%</div>
        <div className="text-xs text-gray-500">GDPR Compliant</div>
      </div>
      <div className="text-center">
        <div className="text-2xl font-bold text-blue-600">30</div>
        <div className="text-xs text-gray-500">Days Simulated</div>
      </div>
    </div>
  );

  return (
    <motion.div
      key="generating"
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -20 }}
      className="max-w-4xl mx-auto py-20"
    >
      <Card className="border-2 border-purple-200">
        <CardContent className="p-12 text-center space-y-6">
          <motion.div
            animate={{ rotate: 360 }}
            transition={{ duration: 2, repeat: Infinity, ease: "linear" }}
            className="w-20 h-20 mx-auto"
          >
            <Sparkles className="w-20 h-20 text-purple-600" />
          </motion.div>
          
          <h2 className="text-2xl font-bold text-gray-900">
            Generating Synthetic Data
          </h2>
          <p className="text-gray-600 max-w-2xl mx-auto">
            Creating realistic {selectedWorkload} workload patterns with temporal variations,
            edge cases, and failure scenarios...
          </p>
          
          {renderProgressSection()}
          {renderStatsGrid()}
        </CardContent>
      </Card>
    </motion.div>
  );
};

export default GeneratingScreen;