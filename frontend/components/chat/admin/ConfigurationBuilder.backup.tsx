/**
 * Configuration Builder Component
 * 
 * Visual builder for corpus generation configuration.
 * Follows glassmorphic design with real-time validation.
 * Each function ≤8 lines. No blue gradients. Strong TypeScript typing.
 */

import React, { useState, useCallback, useEffect } from 'react';
import { ConfigConfigValidationResult } from '@/types/shared/validation';
import { Settings, Save, AlertCircle, CheckCircle, Zap } from 'lucide-react';
import { generateUniqueId } from '../../../lib/utils';
import { useWebSocket } from '../../../hooks/useWebSocket';
import { cn } from '../../../lib/utils';

// Strong TypeScript typing - single source of truth
interface WorkloadType {
  readonly id: string;
  readonly name: string;
  selected: boolean;
}

type ComplexityLevel = 'low' | 'medium' | 'high';
type DistributionType = 'normal' | 'uniform' | 'exponential';
type OptimizationFocus = 'performance' | 'quality' | 'balanced';
type DomainType = 'ecommerce' | 'fintech' | 'healthcare' | 'saas' | 'iot';

interface GenerationParams {
  recordCount: number;
  complexity: ComplexityLevel;
  errorRate: number;
  distribution: DistributionType;
  concurrency: number;
}


interface CorpusConfiguration {
  name: string;
  domain: DomainType | '';
  workloadTypes: WorkloadType[];
  parameters: GenerationParams;
  targetTable: string;
  optimizationFocus: OptimizationFocus;
}

interface ConfigurationBuilderProps {
  onConfigurationComplete: (config: CorpusConfiguration) => void;
  sessionId: string;
  className?: string;
}

const ConfigurationBuilder: React.FC<ConfigurationBuilderProps> = ({
  onConfigurationComplete,
  sessionId,
  className
}) => {
  const [config, setConfig] = useState<CorpusConfiguration>({
    name: '',
    domain: '',
    workloadTypes: initializeWorkloadTypes(),
    parameters: initializeParameters(),
    targetTable: '',
    optimizationFocus: 'balanced'
  });
  
  const [validation, setValidation] = useState<ConfigValidationResult>({
    valid: true,
    errors: []
  });
  
  const [suggestions, setSuggestions] = useState<any[]>([]);
  const [preview, setPreview] = useState<any>(null);
  const [saving, setSaving] = useState(false);
  
  const { sendMessage, lastMessage } = useWebSocket();

  useEffect(() => {
    handleWebSocketMessage();
  }, [lastMessage]);

  useEffect(() => {
    validateConfiguration();
  }, [config]);

  // ≤8 lines: Initialize workload types
  function initializeWorkloadTypes(): WorkloadType[] {
    const workloads: WorkloadType[] = [
      { id: 'data_processing', name: 'Data Processing', selected: false },
      { id: 'machine_learning', name: 'Machine Learning', selected: false },
      { id: 'web_services', name: 'Web Services', selected: false },
      { id: 'database', name: 'Database', selected: false },
      { id: 'analytics', name: 'Analytics', selected: false },
      { id: 'infrastructure', name: 'Infrastructure', selected: false }
    ];
    return workloads;
  }

  // ≤8 lines: Initialize generation parameters
  function initializeParameters(): GenerationParams {
    return {
      recordCount: 10000,
      complexity: 'medium' as ComplexityLevel,
      errorRate: 0.01,
      distribution: 'normal' as DistributionType,
      concurrency: 10
    };
  }

  const handleWebSocketMessage = useCallback(() => {
    if (!lastMessage) return;
    
    if (lastMessage.message_type === 'config_suggestion_response') {
      processSuggestions(lastMessage);
    } else if (lastMessage.message_type === 'corpus_config_preview') {
      setPreview(lastMessage);
    }
  }, [lastMessage]);

  const processSuggestions = (response: any) => {
    setSuggestions(response.suggestions || []);
    if (response.preview) {
      applyPreviewToConfig(response.preview);
    }
  };

  const applyPreviewToConfig = (preview: any) => {
    setConfig(prev => ({
      ...prev,
      parameters: {
        ...prev.parameters,
        ...preview
      }
    }));
  };

  // ≤8 lines: Validate configuration
  const validateConfiguration = useCallback(() => {
    const errors = collectValidationErrors();
    setValidation({ valid: errors.length === 0, errors });
  }, [config]);

  // ≤8 lines: Collect validation errors
  const collectValidationErrors = (): string[] => {
    const errors: string[] = [];
    validateBasicFields(errors);
    validateWorkloadSelection(errors);
    validateRecordCount(errors);
    return errors;
  };

  // ≤8 lines: Validate basic fields
  const validateBasicFields = (errors: string[]) => {
    if (!config.name || config.name.length < 3) {
      errors.push('Corpus name must be at least 3 characters');
    }
    if (!config.domain) {
      errors.push('Domain is required');
    }
  };

  // ≤8 lines: Validate workload selection
  const validateWorkloadSelection = (errors: string[]) => {
    if (!config.workloadTypes.some(w => w.selected)) {
      errors.push('Select at least one workload type');
    }
  };

  // ≤8 lines: Validate record count
  const validateRecordCount = (errors: string[]) => {
    const { recordCount } = config.parameters;
    if (recordCount < 100 || recordCount > 10000000) {
      errors.push('Record count must be between 100 and 10,000,000');
    }
  };

  // ≤8 lines: Request AI suggestions
  const requestSuggestions = useCallback(() => {
    const selectedWorkload = config.workloadTypes.find(w => w.selected);
    sendMessage({
      message_type: 'config_suggestion_request',
      optimization_focus: config.optimizationFocus,
      domain: config.domain,
      workload_type: selectedWorkload?.id,
      session_id: sessionId
    });
  }, [config, sendMessage, sessionId]);

  // ≤8 lines: Update generation parameters
  const handleParameterChange = (key: keyof GenerationParams, value: any) => {
    setConfig(prev => ({
      ...prev,
      parameters: {
        ...prev.parameters,
        [key]: value
      }
    }));
  };

  // ≤8 lines: Toggle workload selection
  const handleWorkloadToggle = (workloadId: string) => {
    setConfig(prev => ({
      ...prev,
      workloadTypes: prev.workloadTypes.map(w =>
        w.id === workloadId ? { ...w, selected: !w.selected } : w
      )
    }));
  };

  // ≤8 lines: Change optimization focus
  const handleOptimizationChange = (focus: OptimizationFocus) => {
    setConfig(prev => ({ ...prev, optimizationFocus: focus }));
    requestSuggestions();
  };

  // ≤8 lines: Save configuration
  const handleSave = async () => {
    if (!validation.valid) return;
    
    setSaving(true);
    await sendConfigurationMessage();
    finalizeSaving();
  };

  // ≤8 lines: Send configuration via WebSocket
  const sendConfigurationMessage = async () => {
    const selectedWorkloads = config.workloadTypes.filter(w => w.selected);
    sendMessage({
      message_type: 'corpus_generation_request',
      domain: config.domain,
      workload_types: selectedWorkloads.map(w => w.id),
      parameters: config.parameters,
      target_table: config.targetTable,
      session_id: sessionId
    });
  };

  // ≤8 lines: Finalize saving process
  const finalizeSaving = () => {
    setTimeout(() => {
      setSaving(false);
      onConfigurationComplete(config);
    }, 1500);
  };

  const renderWorkloadTypes = () => (
    <div className="space-y-2">
      <label className="block text-sm font-medium mb-2">Workload Types</label>
      <div className="grid grid-cols-2 gap-2">
        {config.workloadTypes.map(workload => (
          <button
            key={workload.id}
            onClick={() => handleWorkloadToggle(workload.id)}
            className={cn(
              "p-3 rounded-lg transition-all text-left",
              "border backdrop-blur-sm",
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
        ))}
      </div>
    </div>
  );

  const renderParameters = () => (
    <div className="space-y-4">
      <label className="block text-sm font-medium mb-2">Generation Parameters</label>
      
      <div>
        <label className="block text-xs text-gray-400 mb-1">Record Count</label>
        <input
          type="number"
          value={config.parameters.recordCount}
          onChange={(e) => handleParameterChange('recordCount', parseInt(e.target.value))}
          className={cn(
            "w-full px-3 py-2 rounded-lg",
            "bg-white/5 backdrop-blur-sm",
            "border border-white/10",
            "focus:border-white/20 focus:outline-none"
          )}
        />
      </div>
      
      <div>
        <label className="block text-xs text-gray-400 mb-1">Complexity</label>
        <select
          value={config.parameters.complexity}
          onChange={(e) => handleParameterChange('complexity', e.target.value)}
          className={cn(
            "w-full px-3 py-2 rounded-lg",
            "bg-white/5 backdrop-blur-sm",
            "border border-white/10",
            "focus:border-white/20 focus:outline-none"
          )}
        >
          <option value="low">Low</option>
          <option value="medium">Medium</option>
          <option value="high">High</option>
        </select>
      </div>
      
      <div>
        <label className="block text-xs text-gray-400 mb-1">Error Rate</label>
        <input
          type="number"
          step="0.001"
          value={config.parameters.errorRate}
          onChange={(e) => handleParameterChange('errorRate', parseFloat(e.target.value))}
          className={cn(
            "w-full px-3 py-2 rounded-lg",
            "bg-white/5 backdrop-blur-sm",
            "border border-white/10",
            "focus:border-white/20 focus:outline-none"
          )}
        />
      </div>
    </div>
  );

  const renderOptimization = () => (
    <div className="space-y-2">
      <label className="block text-sm font-medium mb-2">Optimization Focus</label>
      <div className="grid grid-cols-3 gap-2">
        {(['performance', 'quality', 'balanced'] as const).map(focus => (
          <button
            key={focus}
            onClick={() => handleOptimizationChange(focus)}
            className={cn(
              "p-3 rounded-lg transition-all",
              "border backdrop-blur-sm",
              config.optimizationFocus === focus
                ? "bg-emerald-500/20 border-emerald-500/50"
                : "bg-white/5 border-white/10 hover:bg-white/10"
            )}
          >
            <div className="flex items-center justify-center gap-2">
              {focus === 'performance' && <Zap className="w-4 h-4" />}
              <span className="text-sm capitalize">{focus}</span>
            </div>
          </button>
        ))}
      </div>
    </div>
  );

  const renderValidation = () => {
    if (validation.errors.length === 0) return null;
    
    return (
      <div className="p-4 rounded-lg bg-red-500/10 border border-red-500/20">
        <div className="flex items-start gap-2">
          <AlertCircle className="w-5 h-5 text-red-400 mt-0.5" />
          <div>
            <h4 className="font-medium text-red-300 mb-2">Validation Errors</h4>
            <ul className="space-y-1">
              {validation.errors.map((error, idx) => (
                <li key={generateUniqueId('error')} className="text-sm text-gray-300">
                  {error}
                </li>
              ))}
            </ul>
          </div>
        </div>
      </div>
    );
  };

  return (
    <div className={cn(
      "rounded-xl p-6",
      "bg-gray-900/50 backdrop-blur-xl",
      "border border-gray-700/50",
      className
    )}>
      <div className="mb-6">
        <h2 className="text-xl font-semibold mb-2 flex items-center gap-2">
          <Settings className="w-5 h-5" />
          Configuration Builder
        </h2>
        <p className="text-gray-400">
          Build your corpus generation configuration
        </p>
      </div>

      <div className="space-y-6">
        <div>
          <label className="block text-sm font-medium mb-2">Corpus Name</label>
          <input
            type="text"
            value={config.name}
            onChange={(e) => setConfig(prev => ({ ...prev, name: e.target.value }))}
            placeholder="Enter corpus name..."
            className={cn(
              "w-full px-4 py-3 rounded-lg",
              "bg-white/5 backdrop-blur-sm",
              "border border-white/10",
              "focus:border-white/20 focus:outline-none"
            )}
          />
        </div>

        <div>
          <label className="block text-sm font-medium mb-2">Domain</label>
          <select
            value={config.domain}
            onChange={(e) => setConfig(prev => ({ ...prev, domain: e.target.value }))}
            className={cn(
              "w-full px-4 py-3 rounded-lg",
              "bg-white/5 backdrop-blur-sm",
              "border border-white/10",
              "focus:border-white/20 focus:outline-none"
            )}
          >
            <option value="">Select domain...</option>
            <option value="ecommerce">E-commerce</option>
            <option value="fintech">Fintech</option>
            <option value="healthcare">Healthcare</option>
            <option value="saas">SaaS</option>
            <option value="iot">IoT</option>
          </select>
        </div>

        {renderWorkloadTypes()}
        {renderParameters()}
        {renderOptimization()}
        {renderValidation()}

        <div className="flex justify-end gap-3 pt-4">
          <button
            onClick={requestSuggestions}
            className={cn(
              "px-4 py-2 rounded-lg transition-all",
              "bg-white/5 border border-white/10",
              "hover:bg-white/10"
            )}
          >
            Get Suggestions
          </button>
          <button
            onClick={handleSave}
            disabled={!validation.valid || saving}
            className={cn(
              "px-6 py-2 rounded-lg transition-all flex items-center gap-2",
              validation.valid
                ? "bg-emerald-500 hover:bg-emerald-600"
                : "bg-gray-600 cursor-not-allowed"
            )}
          >
            <Save className="w-4 h-4" />
            {saving ? 'Saving...' : 'Save Configuration'}
          </button>
        </div>
      </div>
    </div>
  );
};

export default ConfigurationBuilder;