import React from 'react';
import { motion } from 'framer-motion';
import { Settings } from 'lucide-react';
import { CustomizationPanelProps } from './WorkloadTypes';

const CustomizationPanel: React.FC<CustomizationPanelProps> = ({
  selectedWorkload,
  showAdvancedOptions,
  customParams,
  setCustomParams,
  customizing,
  setCustomizing
}) => {
  const handleVolumeChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setCustomParams({ 
      ...customParams, 
      volume: parseInt(e.target.value) 
    });
  };

  const handleTimeRangeChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setCustomParams({ 
      ...customParams, 
      timeRange: parseInt(e.target.value) 
    });
  };

  const handlePeakMultiplierChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setCustomParams({ 
      ...customParams, 
      peakMultiplier: parseFloat(e.target.value) 
    });
  };

  const toggleCustomizing = () => {
    setCustomizing(!customizing);
  };

  const renderInputField = (
    label: string,
    value: number,
    onChange: (e: React.ChangeEvent<HTMLInputElement>) => void,
    unit: string,
    min: string,
    max: string,
    step?: string
  ) => {
    return (
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">
          {label}
        </label>
        <input
          type="number"
          value={value}
          onChange={onChange}
          className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-purple-500"
          min={min}
          max={max}
          step={step}
        />
        <span className="text-xs text-gray-500">{unit}</span>
      </div>
    );
  };

  if (!showAdvancedOptions || !selectedWorkload) {
    return null;
  }

  return (
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
          onClick={toggleCustomizing}
          className="text-sm text-purple-600 hover:text-purple-700"
        >
          {customizing ? 'Use Defaults' : 'Customize'}
        </button>
      </div>

      {customizing && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {renderInputField(
            'Request Volume',
            customParams.volume,
            handleVolumeChange,
            'requests/day',
            '100',
            '1000000'
          )}
          
          {renderInputField(
            'Time Range',
            customParams.timeRange,
            handleTimeRangeChange,
            'days',
            '1',
            '365'
          )}
          
          {renderInputField(
            'Peak Multiplier',
            customParams.peakMultiplier,
            handlePeakMultiplierChange,
            'x baseline',
            '1',
            '10',
            '0.5'
          )}
        </div>
      )}
    </motion.div>
  );
};

export default CustomizationPanel;