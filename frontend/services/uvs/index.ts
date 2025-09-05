/**
 * UVS Services Export Index
 * Central export point for all UVS frontend services
 */

export { FrontendComponentFactory } from './FrontendComponentFactory';
export { WebSocketBridgeClient } from './WebSocketBridgeClient';
export { ConversationManager } from './ConversationManager';
export { StateRecoveryManager } from './StateRecoveryManager';

export type { 
  Message, 
  ConversationState, 
  UVSContext 
} from './ConversationManager';