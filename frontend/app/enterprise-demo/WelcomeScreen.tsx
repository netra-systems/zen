'use client';

import { Button } from '@/components/ui/button';
import { ArrowRight, Rocket } from 'lucide-react';
import { motion } from 'framer-motion';
import { getMetrics } from './demoConfig';

interface WelcomeScreenProps {
  onStartDemo: () => void;
}

const WelcomeScreen = ({ onStartDemo }: WelcomeScreenProps) => {
  const metrics = getMetrics();

  const renderMetricsSection = () => (
    <div className="flex items-center justify-center space-x-8 py-8">
      <div className="text-center">
        <div className="text-3xl font-bold text-purple-600">{metrics.savings}</div>
        <div className="text-sm text-gray-500">Annual Savings</div>
      </div>
      <div className="text-center">
        <div className="text-3xl font-bold text-green-600">{metrics.performance}</div>
        <div className="text-sm text-gray-500">Faster Response</div>
      </div>
      <div className="text-center">
        <div className="text-3xl font-bold text-blue-600">{metrics.uptime}</div>
        <div className="text-sm text-gray-500">Uptime SLA</div>
      </div>
    </div>
  );

  return (
    <motion.div
      key="welcome"
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -20 }}
      className="max-w-4xl mx-auto py-20 text-center"
    >
      <motion.div
        initial={{ scale: 0.9 }}
        animate={{ scale: 1 }}
        transition={{ delay: 0.2 }}
        className="space-y-6"
      >
        <h1 className="text-5xl font-bold bg-gradient-to-r from-emerald-600 to-purple-600 bg-clip-text text-transparent">
          Experience AI Optimization in Action
        </h1>
        <p className="text-xl text-gray-600 max-w-2xl mx-auto">
          See how Netra can reduce your AI costs by 40-60% while improving performance by 2-3x.
          Start with your industry-specific workload profile.
        </p>
        
        {renderMetricsSection()}
        
        <Button
          size="lg"
          onClick={onStartDemo}
          className="glass-button-primary hover:shadow-lg"
        >
          <Rocket className="mr-2 h-5 w-5" />
          Start Interactive Demo
          <ArrowRight className="ml-2 h-5 w-5" />
        </Button>
      </motion.div>
    </motion.div>
  );
};

export default WelcomeScreen;