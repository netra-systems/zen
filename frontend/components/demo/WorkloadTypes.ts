import React from 'react';

export interface WorkloadProfile {
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

export interface WorkloadSelectorProps {
  onSelect: (workloadId: string) => void;
  showAdvancedOptions?: boolean;
}

export interface CustomizationParams {
  volume: number;
  timeRange: number;
  peakMultiplier: number;
}

export interface WorkloadCardProps {
  profile: WorkloadProfile;
  isSelected: boolean;
  onSelect: (workloadId: string) => void;
  index: number;
}

export interface CustomizationPanelProps {
  selectedWorkload: string | null;
  showAdvancedOptions: boolean;
  customParams: CustomizationParams;
  setCustomParams: (params: CustomizationParams) => void;
  customizing: boolean;
  setCustomizing: (customizing: boolean) => void;
}

export interface ActionButtonsProps {
  selectedWorkload: string | null;
  showAdvancedOptions: boolean;
  onSelect: (workloadId: string) => void;
  onCustomSubmit: () => void;
}