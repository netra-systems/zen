/**
 * Configuration Builder Component (Refactored)
 * 
 * Visual builder for corpus generation configuration.
 * Modular architecture with ≤300 lines, ≤8 lines per function.
 * Glassmorphic design without blue gradients. Strong TypeScript typing.
 */

import React, { useState, useCallback, useEffect } from 'react';
import { Settings, Save } from 'lucide-react';
import { useWebSocket } from '../../../hooks/useWebSocket';
import { cn } from '../../../lib/utils';

// Modular imports
import type {
  CorpusConfiguration,
  ConfigurationBuilderProps,
  ValidationResult,
  GenerationParams,
  OptimizationFocus,
  DomainType
} from './ConfigurationBuilder.types';
import { initializeConfiguration } from './ConfigurationBuilder.data';
import { validateConfiguration } from './ConfigurationBuilder.validation';
import {
  WorkloadTypesSection,
  ParametersSection,
  OptimizationSection,
  ValidationDisplay
} from './ConfigurationBuilder.components';
import {
  createSuggestionRequest,
  createGenerationRequest,
  handleWebSocketMessage,
  applyPreviewToConfig
} from './ConfigurationBuilder.messaging';

const ConfigurationBuilder: React.FC<ConfigurationBuilderProps> = ({
  onConfigurationComplete,
  sessionId,
  className
}) => {
  const [config, setConfig] = useState<CorpusConfiguration>(initializeConfiguration());
  const [validation, setValidation] = useState<ValidationResult>({ valid: true, errors: [] });
  const [suggestions, setSuggestions] = useState<any[]>([]);
  const [preview, setPreview] = useState<any>(null);
  const [saving, setSaving] = useState(false);

  const { sendMessage, lastMessage } = useWebSocket();

  // ≤8 lines: Handle WebSocket messages
  useEffect(() => {
    if (!lastMessage) return;
    handleWebSocketMessage(
      lastMessage,
      setSuggestions,
      setPreview,
      (preview) => applyPreviewToConfig(preview, setConfig)
    );
  }, [lastMessage]);

  // ≤8 lines: Validate configuration on changes
  useEffect(() => {
    const result = validateConfiguration(config);
    setValidation(result);
  }, [config]);

  // ≤8 lines: Request AI suggestions
  const requestSuggestions = useCallback(() => {
    const message = createSuggestionRequest(config, sessionId);
    sendMessage(message);
  }, [config, sendMessage, sessionId]);

  // ≤8 lines: Handle parameter changes
  const handleParameterChange = useCallback((key: keyof GenerationParams, value: any) => {
    setConfig(prev => ({
      ...prev,
      parameters: { ...prev.parameters, [key]: value }
    }));
  }, []);

  // ≤8 lines: Handle workload toggle
  const handleWorkloadToggle = useCallback((workloadId: string) => {
    setConfig(prev => ({
      ...prev,
      workloadTypes: prev.workloadTypes.map(w =>
        w.id === workloadId ? { ...w, selected: !w.selected } : w
      )
    }));
  }, []);

  // ≤8 lines: Handle optimization focus change
  const handleOptimizationChange = useCallback((focus: OptimizationFocus) => {
    setConfig(prev => ({ ...prev, optimizationFocus: focus }));
    requestSuggestions();
  }, [requestSuggestions]);

  // ≤8 lines: Handle basic field changes
  const handleFieldChange = useCallback((field: string, value: string) => {
    setConfig(prev => ({ ...prev, [field]: value }));
  }, []);

  // ≤8 lines: Save configuration
  const handleSave = useCallback(async () => {
    if (!validation.valid) return;
    setSaving(true);
    await sendConfigurationMessage();
    finalizeSaving();
  }, [validation.valid, config, sessionId, onConfigurationComplete]);

  // ≤8 lines: Send configuration message
  const sendConfigurationMessage = useCallback(async () => {
    const message = createGenerationRequest(config, sessionId);
    sendMessage(message);
  }, [config, sessionId, sendMessage]);

  // ≤8 lines: Finalize saving process
  const finalizeSaving = useCallback(() => {
    setTimeout(() => {
      setSaving(false);
      onConfigurationComplete(config);
    }, 1500);
  }, [config, onConfigurationComplete]);

  // ≤8 lines: Render domain selection
  const renderDomainSection = () => (
    <div>
      <label className="block text-sm font-medium mb-2">Domain</label>
      <select
        value={config.domain}
        onChange={(e) => handleFieldChange('domain', e.target.value)}
        className={cn(
          "w-full px-4 py-3 rounded-lg bg-white/5 backdrop-blur-sm",
          "border border-white/10 focus:border-white/20 focus:outline-none"
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
  );

  // ≤8 lines: Render name input section
  const renderNameSection = () => (
    <div>
      <label className="block text-sm font-medium mb-2">Corpus Name</label>
      <input
        type="text"
        value={config.name}
        onChange={(e) => handleFieldChange('name', e.target.value)}
        placeholder="Enter corpus name..."
        className={cn(
          "w-full px-4 py-3 rounded-lg bg-white/5 backdrop-blur-sm",
          "border border-white/10 focus:border-white/20 focus:outline-none"
        )}
      />
    </div>
  );

  // ≤8 lines: Render action buttons
  const renderActionButtons = () => (
    <div className="flex justify-end gap-3 pt-4">
      <button
        onClick={requestSuggestions}
        className={cn(
          "px-4 py-2 rounded-lg transition-all bg-white/5",
          "border border-white/10 hover:bg-white/10"
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
  );

  return (
    <div className={cn(
      "rounded-xl p-6 bg-gray-900/50 backdrop-blur-xl",
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
        {renderNameSection()}
        {renderDomainSection()}
        
        <WorkloadTypesSection 
          workloadTypes={config.workloadTypes} 
          onToggle={handleWorkloadToggle} 
        />
        
        <ParametersSection 
          parameters={config.parameters} 
          onChange={handleParameterChange} 
        />
        
        <OptimizationSection 
          selectedFocus={config.optimizationFocus} 
          onChange={handleOptimizationChange} 
        />
        
        <ValidationDisplay validation={validation} />
        {renderActionButtons()}
      </div>
    </div>
  );
};

export default ConfigurationBuilder;