'use client';

import { motion } from 'framer-motion';
import WorkloadSelector from '@/components/demo/WorkloadSelector';

interface WorkloadScreenProps {
  onWorkloadSelect: (workloadId: string) => void;
}

const WorkloadScreen = ({ onWorkloadSelect }: WorkloadScreenProps) => {
  return (
    <motion.div
      key="workload"
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -20 }}
    >
      <WorkloadSelector 
        onSelect={onWorkloadSelect}
        showAdvancedOptions={true}
      />
    </motion.div>
  );
};

export default WorkloadScreen;