import React, { useState, useEffect, useMemo } from 'react';
import { motion } from 'framer-motion';
import { Brain } from 'lucide-react';
import { useUnifiedChatStore } from '@/store/unified-chat';
import { StatusZone, WorkflowProgress, ToolExecutionStatus } from './types';
import { generateAllStatusZones } from './status-zone-generator';
import { useHumorQuips, useMetricsSimulation, useDataPreview } from './hooks';
import { 
  HumorSection, 
  StatusZoneSection, 
  DataPreviewSection, 
  ConfidenceIndicator 
} from './ui-components';

const AgentStatusPanel: React.FC = () => {
  const { 
    subAgentName, 
    isProcessing, 
    fastLayerData, 
    mediumLayerData, 
    slowLayerData 
  } = useUnifiedChatStore();
  
  const [statusZones, setStatusZones] = useState<StatusZone[]>([]);
  const [expandedPreview, setExpandedPreview] = useState<string | null>(null);

  const activeTools = useMemo(() => 
    fastLayerData?.activeTools || [], 
    [fastLayerData?.activeTools]
  );

  const toolExecutionStatus: ToolExecutionStatus = useMemo(() => 
    activeTools.length > 0 ? 'executing' : 'idle', 
    [activeTools.length]
  );

  const workflowProgress: WorkflowProgress = useMemo(() => ({
    current_step: fastLayerData ? (mediumLayerData ? (slowLayerData ? 3 : 2) : 1) : 0,
    total_steps: 3
  }), [fastLayerData, mediumLayerData, slowLayerData]);

  const currentQuip = useHumorQuips(isProcessing);
  const metrics = useMetricsSimulation(isProcessing);
  const dataPreview = useDataPreview(isProcessing, workflowProgress.current_step);

  useEffect(() => {
    const zones = generateAllStatusZones(
      subAgentName,
      workflowProgress,
      activeTools,
      toolExecutionStatus,
      metrics
    );
    setStatusZones(zones);
  }, [subAgentName, workflowProgress, activeTools, toolExecutionStatus, metrics]);

  if (!isProcessing) return null;

  return (
    <motion.div
      initial={{ opacity: 0, y: -20 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -20 }}
      className="fixed top-20 right-4 w-96 bg-white rounded-lg shadow-2xl border border-gray-200 overflow-hidden z-40"
    >
      {/* Header */}
      <div className="glass-accent-purple backdrop-blur-md text-purple-900 p-4 border-b border-purple-200">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <Brain className="w-5 h-5" />
            <span className="font-semibold">Agent Intelligence Hub</span>
          </div>
          <div className="flex items-center space-x-1">
            <div className="w-2 h-2 bg-green-400 rounded-full animate-pulse" />
            <span className="text-xs">Active</span>
          </div>
        </div>
      </div>

      {/* Content */}
      <div className="p-4 space-y-3">
        <HumorSection currentQuip={currentQuip} />
        <StatusZoneSection statusZones={statusZones} />
        <DataPreviewSection 
          dataPreview={dataPreview}
          expandedPreview={expandedPreview}
          setExpandedPreview={setExpandedPreview}
        />
        <ConfidenceIndicator metrics={metrics} />
      </div>
    </motion.div>
  );
};

export default AgentStatusPanel;