/**
 * Tests for Message Display Utilities
 * 
 * Comprehensive test coverage for agent name display logic.
 */

import { 
  isValidSubAgentName, 
  getMessageDisplayName, 
  getMessageSubtitle, 
  shouldShowSubtitle 
} from './message-display';
import { MessageType } from '@/types/backend_schema_base';

describe('Message Display Utilities', () => {
  describe('isValidSubAgentName', () => {
    it('returns false for null/undefined values', () => {
      expect(isValidSubAgentName(null)).toBe(false);
      expect(isValidSubAgentName(undefined)).toBe(false);
    });

    it('returns false for "undefined" string', () => {
      expect(isValidSubAgentName('undefined')).toBe(false);
    });

    it('returns false for empty/whitespace strings', () => {
      expect(isValidSubAgentName('')).toBe(false);
      expect(isValidSubAgentName('   ')).toBe(false);
      expect(isValidSubAgentName('\t\n')).toBe(false);
    });

    it('returns true for valid agent names', () => {
      expect(isValidSubAgentName('data_analyzer')).toBe(true);
      expect(isValidSubAgentName('Supply Researcher')).toBe(true);
      expect(isValidSubAgentName('Tool Agent')).toBe(true);
    });
  });

  describe('getMessageDisplayName', () => {
    it('returns "You" for user messages', () => {
      expect(getMessageDisplayName('user')).toBe('You');
      expect(getMessageDisplayName('user', 'some_agent')).toBe('You');
      expect(getMessageDisplayName('user', null)).toBe('You');
    });

    it('returns sub-agent name for valid agent names', () => {
      expect(getMessageDisplayName('agent', 'data_analyzer')).toBe('data_analyzer');
      expect(getMessageDisplayName('tool', 'Supply Researcher')).toBe('Supply Researcher');
      expect(getMessageDisplayName('system', 'Tool Agent')).toBe('Tool Agent');
    });

    it('returns "Netra Agent" for invalid/missing agent names', () => {
      expect(getMessageDisplayName('agent')).toBe('Netra Agent');
      expect(getMessageDisplayName('agent', null)).toBe('Netra Agent');
      expect(getMessageDisplayName('agent', undefined)).toBe('Netra Agent');
      expect(getMessageDisplayName('agent', 'undefined')).toBe('Netra Agent');
      expect(getMessageDisplayName('agent', '')).toBe('Netra Agent');
      expect(getMessageDisplayName('agent', '   ')).toBe('Netra Agent');
    });

    it('handles all message types correctly', () => {
      const messageTypes: MessageType[] = ['user', 'agent', 'system', 'error', 'tool'];
      
      messageTypes.forEach(type => {
        if (type === 'user') {
          expect(getMessageDisplayName(type, 'some_agent')).toBe('You');
        } else {
          expect(getMessageDisplayName(type, 'valid_agent')).toBe('valid_agent');
          expect(getMessageDisplayName(type)).toBe('Netra Agent');
        }
      });
    });
  });

  describe('getMessageSubtitle', () => {
    it('returns null for user messages', () => {
      expect(getMessageSubtitle('user', 'some_agent')).toBeNull();
      expect(getMessageSubtitle('user')).toBeNull();
    });

    it('returns null for invalid agent names', () => {
      expect(getMessageSubtitle('agent', null)).toBeNull();
      expect(getMessageSubtitle('agent', 'undefined')).toBeNull();
      expect(getMessageSubtitle('agent', '')).toBeNull();
    });

    it('returns "Tool Execution" for tool messages with valid agents', () => {
      expect(getMessageSubtitle('tool', 'data_tool')).toBe('Tool Execution');
    });

    it('returns "Agent Response" for non-tool, non-user messages with valid agents', () => {
      expect(getMessageSubtitle('agent', 'data_analyzer')).toBe('Agent Response');
      expect(getMessageSubtitle('system', 'system_agent')).toBe('Agent Response');
      expect(getMessageSubtitle('error', 'error_agent')).toBe('Agent Response');
    });
  });

  describe('shouldShowSubtitle', () => {
    it('returns false for user messages', () => {
      expect(shouldShowSubtitle('user', 'some_agent')).toBe(false);
    });

    it('returns false for invalid agent names', () => {
      expect(shouldShowSubtitle('agent', null)).toBe(false);
      expect(shouldShowSubtitle('agent', 'undefined')).toBe(false);
      expect(shouldShowSubtitle('tool', '')).toBe(false);
    });

    it('returns true for valid agent names with non-user types', () => {
      expect(shouldShowSubtitle('agent', 'data_analyzer')).toBe(true);
      expect(shouldShowSubtitle('tool', 'data_tool')).toBe(true);
      expect(shouldShowSubtitle('system', 'system_agent')).toBe(true);
    });
  });

  describe('Edge Cases', () => {
    it('handles edge case strings correctly', () => {
      // Test various edge cases that might appear in production
      const edgeCases = [
        'null',
        'UNDEFINED',
        '0',
        'false',
        'true',
        'NaN',
        '{}',
        '[]'
      ];

      edgeCases.forEach(edgeCase => {
        expect(isValidSubAgentName(edgeCase)).toBe(true);
        expect(getMessageDisplayName('agent', edgeCase)).toBe(edgeCase);
      });
    });

    it('preserves agent name formatting', () => {
      const formattedNames = [
        'Data-Analyzer-v2',
        'Supply_Researcher_Pro',
        'Tool Agent (Beta)',
        'AI Assistant 3.0'
      ];

      formattedNames.forEach(name => {
        expect(getMessageDisplayName('agent', name)).toBe(name);
      });
    });
  });
});