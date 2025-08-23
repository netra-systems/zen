/**
 * Regression test for module export initialization
 * Prevents runtime ReferenceError issues with enum exports
 */

import * as registry from '@/types/unified';
import * as enums from '@/types/shared/enums';

describe('Type Registry Export Safety', () => {
  describe('Named exports from registry', () => {
    it('should export MessageType enum without runtime errors', () => {
      expect(registry.MessageType).toBeDefined();
      expect(registry.MessageType.USER).toBe('user');
      expect(registry.MessageType.ASSISTANT).toBe('assistant');
    });

    it('should export AgentStatus enum without runtime errors', () => {
      expect(registry.AgentStatus).toBeDefined();
      expect(registry.AgentStatus.IDLE).toBe('idle');
      expect(registry.AgentStatus.ACTIVE).toBe('active');
    });

    it('should export WebSocketMessageType enum without runtime errors', () => {
      expect(registry.WebSocketMessageType).toBeDefined();
      expect(registry.WebSocketMessageType.USER_MESSAGE).toBe('user_message');
      expect(registry.WebSocketMessageType.AGENT_STARTED).toBe('agent_started');
    });

    it('should export validation functions', () => {
      expect(registry.isValidMessageType).toBeDefined();
      expect(registry.isValidAgentStatus).toBeDefined();
      expect(registry.isValidWebSocketMessageType).toBeDefined();
      expect(typeof registry.isValidMessageType).toBe('function');
    });

    it('should validate enum values correctly', () => {
      expect(registry.isValidMessageType('user')).toBe(true);
      expect(registry.isValidMessageType('invalid')).toBe(false);
      expect(registry.isValidAgentStatus('active')).toBe(true);
      expect(registry.isValidAgentStatus('invalid')).toBe(false);
    });
  });

  describe('Named exports from shared/enums', () => {
    it('should export enums without runtime errors', () => {
      expect(enums.MessageType).toBeDefined();
      expect(enums.AgentStatus).toBeDefined();
      expect(enums.WebSocketMessageType).toBeDefined();
    });

    it('should export ENUM_REGISTRY', () => {
      expect(enums.ENUM_REGISTRY).toBeDefined();
      expect(enums.ENUM_REGISTRY.MessageType).toBe(enums.MessageType);
      expect(enums.ENUM_REGISTRY.AgentStatus).toBe(enums.AgentStatus);
    });
  });

  describe('No default exports (regression prevention)', () => {
    it('should not have default export in registry', () => {
      // This test ensures we don't accidentally re-add problematic default exports
      const registryModule = require('@/types/unified');
      expect(registryModule.default).toBeUndefined();
    });

    it('should not have default export in shared/enums', () => {
      // This test ensures we don't accidentally re-add problematic default exports
      const enumsModule = require('@/types/shared/enums');
      expect(enumsModule.default).toBeUndefined();
    });
  });

  describe('Module initialization order', () => {
    it('should handle circular imports safely', () => {
      // Import in different order to test initialization
      const { MessageType: MT1 } = require('@/types/unified');
      const { MessageType: MT2 } = require('@/types/shared/enums');
      
      expect(MT1).toBe(MT2);
      expect(MT1.USER).toBe('user');
    });

    it('should allow enum usage in object literals after import', () => {
      const { MessageType, AgentStatus } = registry;
      
      // This pattern caused the original error
      const testObject = {
        MessageType,
        AgentStatus
      };
      
      expect(testObject.MessageType).toBe(MessageType);
      expect(testObject.AgentStatus).toBe(AgentStatus);
    });
  });
});