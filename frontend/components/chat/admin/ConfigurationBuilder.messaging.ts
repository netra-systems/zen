/**
 * Configuration Builder WebSocket Messaging
 * 
 * WebSocket message handling for corpus configuration.
 * Each function ≤8 lines for architectural compliance.
 */

import type {
  CorpusConfiguration,
  OptimizationFocus,
  DomainType,
  ConfigSuggestionRequest,
  CorpusGenerationRequest
} from './ConfigurationBuilder.types';
import { getSelectedWorkloadIds } from './ConfigurationBuilder.data';

// ≤8 lines: Create suggestion request message
export const createSuggestionRequest = (
  config: CorpusConfiguration,
  sessionId: string
): ConfigSuggestionRequest => {
  const selectedWorkload = config.workloadTypes.find(w => w.selected);
  return {
    message_type: 'config_suggestion_request',
    optimization_focus: config.optimizationFocus,
    domain: config.domain,
    workload_type: selectedWorkload?.id,
    session_id: sessionId
  };
};

// ≤8 lines: Create corpus generation request message
export const createGenerationRequest = (
  config: CorpusConfiguration,
  sessionId: string
): CorpusGenerationRequest => {
  const selectedWorkloadIds = getSelectedWorkloadIds(config.workloadTypes);
  return {
    message_type: 'corpus_generation_request',
    domain: config.domain,
    workload_types: selectedWorkloadIds,
    parameters: config.parameters,
    target_table: config.targetTable,
    session_id: sessionId
  };
};

// ≤8 lines: Process suggestion response
export const processSuggestionResponse = (
  response: any,
  setSuggestions: (suggestions: any[]) => void,
  applyPreview: (preview: any) => void
): void => {
  setSuggestions(response.suggestions || []);
  if (response.preview) {
    applyPreview(response.preview);
  }
};

// ≤8 lines: Handle WebSocket message routing
export const handleWebSocketMessage = (
  message: any,
  setSuggestions: (suggestions: any[]) => void,
  setPreview: (preview: any) => void,
  applyPreview: (preview: any) => void
): void => {
  if (message.message_type === 'config_suggestion_response') {
    processSuggestionResponse(message, setSuggestions, applyPreview);
  } else if (message.message_type === 'corpus_config_preview') {
    setPreview(message);
  }
};

// ≤8 lines: Apply preview to configuration parameters
export const applyPreviewToConfig = (
  preview: any,
  setConfig: React.Dispatch<React.SetStateAction<CorpusConfiguration>>
): void => {
  setConfig(prev => ({
    ...prev,
    parameters: {
      ...prev.parameters,
      ...preview
    }
  }));
};