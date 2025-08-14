/**
 * Configuration Builder UI Components
 * 
 * Modular UI components for corpus configuration.
 * Each function ≤8 lines. Glassmorphic design. No blue gradients.
 */

import React from 'react';
import { CheckCircle, Zap, AlertCircle } from 'lucide-react';
import { generateUniqueId, cn } from '../../../lib/utils';
import type {
  WorkloadType,
  CorpusConfiguration,
  GenerationParams,
  OptimizationFocus,
  ValidationResult,
  ComplexityLevel,
  DistributionType
} from './ConfigurationBuilder.types';

// Component props interfaces
interface WorkloadTypesProps {
  workloadTypes: WorkloadType[];
  onToggle: (workloadId: string) => void;
}

interface ParametersProps {
  parameters: GenerationParams;
  onChange: (key: keyof GenerationParams, value: any) => void;
}

interface OptimizationProps {
  selectedFocus: OptimizationFocus;
  onChange: (focus: OptimizationFocus) => void;
}

interface ValidationDisplayProps {
  validation: ValidationResult;
}

// ≤8 lines: Render workload type selection
export const WorkloadTypesSection: React.FC<WorkloadTypesProps> = ({ workloadTypes, onToggle }) => (
  <div className="space-y-2">
    <label className="block text-sm font-medium mb-2">Workload Types</label>
    <div className="grid grid-cols-2 gap-2">
      {workloadTypes.map(workload => (
        <WorkloadTypeButton key={workload.id} workload={workload} onToggle={onToggle} />
      ))}
    </div>
  </div>
);

// ≤8 lines: Individual workload type button
const WorkloadTypeButton: React.FC<{ workload: WorkloadType; onToggle: (id: string) => void }> = ({ 
  workload, 
  onToggle 
}) => (
  <button
    onClick={() => onToggle(workload.id)}
    className={cn(
      "p-3 rounded-lg transition-all text-left border backdrop-blur-sm",
      workload.selected
        ? "bg-emerald-500/20 border-emerald-500/50"
        : "bg-white/5 border-white/10 hover:bg-white/10"
    )}
  >
    <div className="flex items-center gap-2">
      {workload.selected && <CheckCircle className="w-4 h-4 text-emerald-400" />}
      <span className="text-sm">{workload.name}</span>
    </div>
  </button>
);

// ≤8 lines: Parameters configuration section
export const ParametersSection: React.FC<ParametersProps> = ({ parameters, onChange }) => (
  <div className="space-y-4">
    <label className="block text-sm font-medium mb-2">Generation Parameters</label>
    <RecordCountInput value={parameters.recordCount} onChange={onChange} />
    <ComplexitySelect value={parameters.complexity} onChange={onChange} />
    <ErrorRateInput value={parameters.errorRate} onChange={onChange} />
  </div>
);

// ≤8 lines: Record count input
const RecordCountInput: React.FC<{ 
  value: number; 
  onChange: (key: keyof GenerationParams, value: any) => void; 
}> = ({ value, onChange }) => (
  <div>
    <label className="block text-xs text-gray-400 mb-1">Record Count</label>
    <input
      type="number"
      value={value}
      onChange={(e) => onChange('recordCount', parseInt(e.target.value))}
      className={cn(
        "w-full px-3 py-2 rounded-lg bg-white/5 backdrop-blur-sm",
        "border border-white/10 focus:border-white/20 focus:outline-none"
      )}
    />
  </div>
);

// ≤8 lines: Complexity selection
const ComplexitySelect: React.FC<{ 
  value: ComplexityLevel; 
  onChange: (key: keyof GenerationParams, value: any) => void; 
}> = ({ value, onChange }) => (
  <div>
    <label className="block text-xs text-gray-400 mb-1">Complexity</label>
    <select
      value={value}
      onChange={(e) => onChange('complexity', e.target.value)}
      className={cn(
        "w-full px-3 py-2 rounded-lg bg-white/5 backdrop-blur-sm",
        "border border-white/10 focus:border-white/20 focus:outline-none"
      )}
    >
      <option value="low">Low</option>
      <option value="medium">Medium</option>
      <option value="high">High</option>
    </select>
  </div>
);

// ≤8 lines: Error rate input
const ErrorRateInput: React.FC<{ 
  value: number; 
  onChange: (key: keyof GenerationParams, value: any) => void; 
}> = ({ value, onChange }) => (
  <div>
    <label className="block text-xs text-gray-400 mb-1">Error Rate</label>
    <input
      type="number"
      step="0.001"
      value={value}
      onChange={(e) => onChange('errorRate', parseFloat(e.target.value))}
      className={cn(
        "w-full px-3 py-2 rounded-lg bg-white/5 backdrop-blur-sm",
        "border border-white/10 focus:border-white/20 focus:outline-none"
      )}
    />
  </div>
);

// ≤8 lines: Optimization focus section
export const OptimizationSection: React.FC<OptimizationProps> = ({ selectedFocus, onChange }) => (
  <div className="space-y-2">
    <label className="block text-sm font-medium mb-2">Optimization Focus</label>
    <div className="grid grid-cols-3 gap-2">
      {(['performance', 'quality', 'balanced'] as const).map(focus => (
        <OptimizationButton key={focus} focus={focus} selected={selectedFocus === focus} onChange={onChange} />
      ))}
    </div>
  </div>
);

// ≤8 lines: Individual optimization button
const OptimizationButton: React.FC<{ 
  focus: OptimizationFocus; 
  selected: boolean; 
  onChange: (focus: OptimizationFocus) => void; 
}> = ({ focus, selected, onChange }) => (
  <button
    onClick={() => onChange(focus)}
    className={cn(
      "p-3 rounded-lg transition-all border backdrop-blur-sm",
      selected
        ? "bg-emerald-500/20 border-emerald-500/50"
        : "bg-white/5 border-white/10 hover:bg-white/10"
    )}
  >
    <div className="flex items-center justify-center gap-2">
      {focus === 'performance' && <Zap className="w-4 h-4" />}
      <span className="text-sm capitalize">{focus}</span>
    </div>
  </button>
);

// ≤8 lines: Validation errors display
export const ValidationDisplay: React.FC<ValidationDisplayProps> = ({ validation }) => {
  if (validation.errors.length === 0) return null;
  
  return (
    <div className="p-4 rounded-lg bg-red-500/10 border border-red-500/20">
      <div className="flex items-start gap-2">
        <AlertCircle className="w-5 h-5 text-red-400 mt-0.5" />
        <ValidationErrorList errors={validation.errors} />
      </div>
    </div>
  );
};

// ≤8 lines: Validation error list
const ValidationErrorList: React.FC<{ errors: readonly string[] }> = ({ errors }) => (
  <div>
    <h4 className="font-medium text-red-300 mb-2">Validation Errors</h4>
    <ul className="space-y-1">
      {errors.map((error, idx) => (
        <li key={generateUniqueId('error')} className="text-sm text-gray-300">
          {error}
        </li>
      ))}
    </ul>
  </div>
);