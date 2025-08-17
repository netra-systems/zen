import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Check } from 'lucide-react';
import { WorkloadCardProps } from './WorkloadTypes';

const WorkloadCard: React.FC<WorkloadCardProps> = ({ 
  profile, 
  isSelected, 
  onSelect, 
  index 
}) => {
  const handleCardClick = () => {
    onSelect(profile.id);
  };

  const renderModelTags = () => {
    return profile.metrics.models.map(model => (
      <span key={model} className="bg-gray-100 px-2 py-0.5 rounded text-xs">
        {model}
      </span>
    ));
  };

  const renderMetricsRow = (label: string, value: string) => {
    return (
      <div className="flex justify-between text-xs">
        <span className="text-gray-500">{label}:</span>
        <span className="font-mono text-gray-900">{value}</span>
      </div>
    );
  };

  const getCardClasses = () => {
    return `relative cursor-pointer rounded-xl border-2 transition-all ${
      isSelected
        ? 'border-purple-500 shadow-xl'
        : 'border-gray-200 hover:border-gray-300 hover:shadow-lg'
    }`;
  };

  const getHeaderClasses = () => {
    return `p-3 rounded-lg bg-gradient-to-br ${profile.gradient} text-white`;
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.1 }}
      whileHover={{ scale: 1.02 }}
      whileTap={{ scale: 0.98 }}
      onClick={handleCardClick}
      className={getCardClasses()}
    >
      {/* Selected indicator */}
      <AnimatePresence>
        {isSelected && (
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
          <div className={getHeaderClasses()}>
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
          {renderMetricsRow('Volume', profile.metrics.volume)}
          {renderMetricsRow('Latency', profile.metrics.avgLatency)}
          {renderMetricsRow('Cost/Inference', profile.metrics.costPerInference)}
          
          <div className="text-xs mt-2">
            <span className="text-gray-500">Models:</span>
            <div className="flex flex-wrap gap-1 mt-1">
              {renderModelTags()}
            </div>
          </div>
        </div>
      </div>
    </motion.div>
  );
};

export default WorkloadCard;