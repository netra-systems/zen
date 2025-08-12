import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  ShoppingCart, TrendingUp, Heart, Gamepad, Microscope,
  Check, ArrowRight, Sparkles, Info, Settings
} from 'lucide-react';

interface WorkloadProfile {
  id: string;
  name: string;
  industry: string;
  icon: React.ReactNode;
  description: string;
  metrics: {
    volume: string;
    models: string[];
    avgLatency: string;
    costPerInference: string;
  };
  color: string;
  gradient: string;
}

interface WorkloadSelectorProps {
  onSelect: (workloadId: string) => void;
  showAdvancedOptions?: boolean;
}

const WorkloadSelector: React.FC<WorkloadSelectorProps> = ({ 
  onSelect, 
  showAdvancedOptions = false 
}) => {
  const [selectedWorkload, setSelectedWorkload] = useState<string | null>(null);
  const [customizing, setCustomizing] = useState(false);
  const [customParams, setCustomParams] = useState({
    volume: 10000,
    timeRange: 30,
    peakMultiplier: 3
  });

  const workloadProfiles: WorkloadProfile[] = [
    {
      id: 'ecommerce',
      name: 'E-Commerce Platform',
      industry: 'Retail',
      icon: <ShoppingCart className="w-6 h-6" />,
      description: 'Product recommendations, search, and customer support',
      metrics: {
        volume: '10K requests/day',
        models: ['GPT-4', 'Claude-2', 'Ada'],
        avgLatency: '200ms',
        costPerInference: '$0.002'
      },
      color: 'text-purple-600',
      gradient: 'from-purple-500 to-pink-500'
    },
    {
      id: 'financial',
      name: 'Financial Services',
      industry: 'Finance',
      icon: <TrendingUp className="w-6 h-6" />,
      description: 'Risk analysis, fraud detection, and compliance',
      metrics: {
        volume: '50K requests/day',
        models: ['GPT-4-Turbo', 'Claude-3-Opus'],
        avgLatency: '500ms',
        costPerInference: '$0.005'
      },
      color: 'text-emerald-600',
      gradient: 'from-emerald-500 to-cyan-500'
    },
    {
      id: 'healthcare',
      name: 'Healthcare AI',
      industry: 'Healthcare',
      icon: <Heart className="w-6 h-6" />,
      description: 'Diagnosis assistance, medical Q&A, report generation',
      metrics: {
        volume: '25K requests/day',
        models: ['Med-PaLM-2', 'GPT-4', 'Bio-GPT'],
        avgLatency: '800ms',
        costPerInference: '$0.008'
      },
      color: 'text-red-600',
      gradient: 'from-red-500 to-orange-500'
    },
    {
      id: 'gaming',
      name: 'Gaming Platform',
      industry: 'Entertainment',
      icon: <Gamepad className="w-6 h-6" />,
      description: 'NPC dialogue, story generation, player assistance',
      metrics: {
        volume: '100K requests/day',
        models: ['GPT-3.5-Turbo', 'Llama-2-7B'],
        avgLatency: '100ms',
        costPerInference: '$0.001'
      },
      color: 'text-green-600',
      gradient: 'from-green-500 to-emerald-500'
    },
    {
      id: 'research',
      name: 'Research Lab',
      industry: 'Science',
      icon: <Microscope className="w-6 h-6" />,
      description: 'Paper analysis, hypothesis generation, data synthesis',
      metrics: {
        volume: '5K requests/day',
        models: ['GPT-4', 'Claude-3-Opus', 'PaLM-2'],
        avgLatency: '2000ms',
        costPerInference: '$0.015'
      },
      color: 'text-indigo-600',
      gradient: 'from-indigo-500 to-purple-500'
    }
  ];

  const handleWorkloadSelect = (workloadId: string) => {
    setSelectedWorkload(workloadId);
    setTimeout(() => {
      if (!showAdvancedOptions) {
        onSelect(workloadId);
      }
    }, 300);
  };

  const handleCustomSubmit = () => {
    if (selectedWorkload) {
      // Include custom parameters in the selection
      const customWorkloadId = `${selectedWorkload}_custom_${customParams.volume}_${customParams.timeRange}_${customParams.peakMultiplier}`;
      onSelect(customWorkloadId);
    }
  };

  return (
    <div className="w-full max-w-6xl mx-auto p-6">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="text-center mb-8"
      >
        <h2 className="text-3xl font-bold text-gray-900 mb-3">
          Select Your Workload Profile
        </h2>
        <p className="text-gray-600 max-w-2xl mx-auto">
          Choose an industry-specific workload to see how Netra AI can optimize your AI infrastructure.
          Each profile includes realistic data patterns and performance characteristics.
        </p>
      </motion.div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 mb-8">
        {workloadProfiles.map((profile, index) => (
          <motion.div
            key={profile.id}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: index * 0.1 }}
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
            onClick={() => handleWorkloadSelect(profile.id)}
            className={`relative cursor-pointer rounded-xl border-2 transition-all ${
              selectedWorkload === profile.id
                ? 'border-purple-500 shadow-xl'
                : 'border-gray-200 hover:border-gray-300 hover:shadow-lg'
            }`}
          >
            {/* Selected indicator */}
            <AnimatePresence>
              {selectedWorkload === profile.id && (
                <motion.div
                  initial={{ scale: 0 }}
                  animate={{ scale: 1 }}
                  exit={{ scale: 0 }}
                  className="absolute -top-3 -right-3 bg-purple-500 text-white rounded-full p-2 z-10"
                >
                  <Check className="w-4 h-4" />
                </motion.div>
              )}
            </AnimatePresence>

            {/* Card content */}
            <div className="p-6">
              {/* Header */}
              <div className="flex items-start justify-between mb-4">
                <div className={`p-3 rounded-lg bg-gradient-to-br ${profile.gradient} text-white`}>
                  {profile.icon}
                </div>
                <span className="text-xs bg-gray-100 text-gray-600 px-2 py-1 rounded">
                  {profile.industry}
                </span>
              </div>

              {/* Title and description */}
              <h3 className="text-lg font-semibold text-gray-900 mb-2">
                {profile.name}
              </h3>
              <p className="text-sm text-gray-600 mb-4">
                {profile.description}
              </p>

              {/* Metrics */}
              <div className="space-y-2 pt-4 border-t">
                <div className="flex justify-between text-xs">
                  <span className="text-gray-500">Volume:</span>
                  <span className="font-mono text-gray-900">{profile.metrics.volume}</span>
                </div>
                <div className="flex justify-between text-xs">
                  <span className="text-gray-500">Latency:</span>
                  <span className="font-mono text-gray-900">{profile.metrics.avgLatency}</span>
                </div>
                <div className="flex justify-between text-xs">
                  <span className="text-gray-500">Cost/Inference:</span>
                  <span className="font-mono text-gray-900">{profile.metrics.costPerInference}</span>
                </div>
                <div className="text-xs mt-2">
                  <span className="text-gray-500">Models:</span>
                  <div className="flex flex-wrap gap-1 mt-1">
                    {profile.metrics.models.map(model => (
                      <span key={model} className="bg-gray-100 px-2 py-0.5 rounded text-xs">
                        {model}
                      </span>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          </motion.div>
        ))}
      </div>

      {/* Advanced customization */}
      {showAdvancedOptions && selectedWorkload && (
        <motion.div
          initial={{ opacity: 0, height: 0 }}
          animate={{ opacity: 1, height: 'auto' }}
          exit={{ opacity: 0, height: 0 }}
          className="bg-gray-50 rounded-xl p-6 mb-8"
        >
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center space-x-2">
              <Settings className="w-5 h-5 text-gray-600" />
              <h3 className="text-lg font-semibold text-gray-900">
                Customize Parameters
              </h3>
            </div>
            <button
              onClick={() => setCustomizing(!customizing)}
              className="text-sm text-purple-600 hover:text-purple-700"
            >
              {customizing ? 'Use Defaults' : 'Customize'}
            </button>
          </div>

          {customizing && (
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Request Volume
                </label>
                <input
                  type="number"
                  value={customParams.volume}
                  onChange={(e) => setCustomParams({ ...customParams, volume: parseInt(e.target.value) })}
                  className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-purple-500"
                  min="100"
                  max="1000000"
                />
                <span className="text-xs text-gray-500">requests/day</span>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Time Range
                </label>
                <input
                  type="number"
                  value={customParams.timeRange}
                  onChange={(e) => setCustomParams({ ...customParams, timeRange: parseInt(e.target.value) })}
                  className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-purple-500"
                  min="1"
                  max="365"
                />
                <span className="text-xs text-gray-500">days</span>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Peak Multiplier
                </label>
                <input
                  type="number"
                  value={customParams.peakMultiplier}
                  onChange={(e) => setCustomParams({ ...customParams, peakMultiplier: parseFloat(e.target.value) })}
                  className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-purple-500"
                  min="1"
                  max="10"
                  step="0.5"
                />
                <span className="text-xs text-gray-500">x baseline</span>
              </div>
            </div>
          )}
        </motion.div>
      )}

      {/* Action buttons */}
      {selectedWorkload && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="flex justify-center"
        >
          <button
            onClick={showAdvancedOptions ? handleCustomSubmit : () => onSelect(selectedWorkload)}
            className="flex items-center space-x-2 px-6 py-3 bg-gradient-to-r from-purple-600 to-indigo-600 text-white rounded-lg hover:shadow-lg transition-all"
          >
            <Sparkles className="w-5 h-5" />
            <span>Generate Synthetic Data</span>
            <ArrowRight className="w-5 h-5" />
          </button>
        </motion.div>
      )}

      {/* Info box */}
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.5 }}
        className="mt-8 p-4 bg-blue-50 rounded-lg border border-blue-200"
      >
        <div className="flex items-start space-x-3">
          <Info className="w-5 h-5 text-blue-600 mt-0.5" />
          <div className="text-sm text-blue-900">
            <p className="font-semibold mb-1">About Synthetic Data Generation</p>
            <p className="text-blue-700">
              Our synthetic data generator creates realistic AI workload patterns based on your selected profile.
              The data includes temporal patterns, seasonality, edge cases, and failure scenarios - all while
              maintaining GDPR compliance without any PII.
            </p>
          </div>
        </div>
      </motion.div>
    </div>
  );
};

export default WorkloadSelector;