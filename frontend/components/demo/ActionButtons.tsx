import React from 'react';
import { motion } from 'framer-motion';
import { Sparkles, ArrowRight, Info } from 'lucide-react';
import { ActionButtonsProps } from './WorkloadTypes';

const ActionButtons: React.FC<ActionButtonsProps> = ({
  selectedWorkload,
  showAdvancedOptions,
  onSelect,
  onCustomSubmit
}) => {
  const handleButtonClick = () => {
    if (showAdvancedOptions) {
      onCustomSubmit();
    } else if (selectedWorkload) {
      onSelect(selectedWorkload);
    }
  };

  const renderActionButton = () => {
    return (
      <button
        onClick={handleButtonClick}
        className="flex items-center space-x-2 px-6 py-3 bg-gradient-to-r from-purple-600 to-indigo-600 text-white rounded-lg hover:shadow-lg transition-all"
      >
        <Sparkles className="w-5 h-5" />
        <span>Generate Synthetic Data</span>
        <ArrowRight className="w-5 h-5" />
      </button>
    );
  };

  const renderInfoBox = () => {
    return (
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
    );
  };

  if (!selectedWorkload) {
    return renderInfoBox();
  }

  return (
    <>
      {/* Action buttons */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="flex justify-center"
      >
        {renderActionButton()}
      </motion.div>

      {/* Info box */}
      {renderInfoBox()}
    </>
  );
};

export default ActionButtons;