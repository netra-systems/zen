import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { WorkloadSelectorProps, CustomizationParams } from './WorkloadTypes';
import { workloadProfiles } from './WorkloadData';
import WorkloadCard from './WorkloadCard';
import CustomizationPanel from './CustomizationPanel';
import ActionButtons from './ActionButtons';

const WorkloadSelector: React.FC<WorkloadSelectorProps> = ({ 
  onSelect, 
  showAdvancedOptions = false 
}) => {
  const [selectedWorkload, setSelectedWorkload] = useState<string | null>(null);
  const [customizing, setCustomizing] = useState(false);
  const [customParams, setCustomParams] = useState<CustomizationParams>({
    volume: 10000,
    timeRange: 30,
    peakMultiplier: 3
  });

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
      const customWorkloadId = 
        `${selectedWorkload}_custom_${customParams.volume}_${customParams.timeRange}_${customParams.peakMultiplier}`;
      onSelect(customWorkloadId);
    }
  };

  const renderHeader = () => {
    return (
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
    );
  };

  const renderWorkloadGrid = () => {
    return (
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 mb-8">
        {workloadProfiles.map((profile, index) => (
          <WorkloadCard
            key={profile.id}
            profile={profile}
            isSelected={selectedWorkload === profile.id}
            onSelect={handleWorkloadSelect}
            index={index}
          />
        ))}
      </div>
    );
  };

  return (
    <div className="w-full max-w-6xl mx-auto p-6">
      {renderHeader()}
      {renderWorkloadGrid()}
      
      <CustomizationPanel
        selectedWorkload={selectedWorkload}
        showAdvancedOptions={showAdvancedOptions}
        customParams={customParams}
        setCustomParams={setCustomParams}
        customizing={customizing}
        setCustomizing={setCustomizing}
      />
      
      <ActionButtons
        selectedWorkload={selectedWorkload}
        showAdvancedOptions={showAdvancedOptions}
        onSelect={onSelect}
        onCustomSubmit={handleCustomSubmit}
      />
    </div>
  );
};

export default WorkloadSelector;