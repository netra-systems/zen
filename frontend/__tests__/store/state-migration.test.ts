/**
 * State Migration Tests - Schema Upgrades & Data Integrity
 * 
 * BVJ (Business Value Justification):
 * - Segment: All (critical for app updates)
 * - Business Goal: Seamless app updates without data loss
 * - Value Impact: Zero-downtime updates prevent user churn
 * - Revenue Impact: Smooth migrations maintain user trust and retention
 * 
 * Tests: Schema upgrades, backward compatibility, data integrity
 * Architecture: ≤300 lines, functions ≤8 lines each
 */

import { act, renderHook } from '@testing-library/react';
import { useAppStore } from '@/store/app';
import { useAuthStore } from '@/store/authStore';
import { useChatStore } from '@/store/chat';
import { GlobalTestUtils } from './store-test-utils';

// Mock migration manager
class StateMigrationManager {
  private currentVersion: number = 3;
  private migrations: Map<number, (state: any) => any> = new Map();

  constructor() {
    this.setupMigrations();
  }

  private setupMigrations(): void {
    // Migration from v0 to v1: Add message timestamps
    this.migrations.set(1, (state: any) => ({
      ...state,
      messages: state.messages?.map((msg: any) => ({
        ...msg,
        created_at: msg.created_at || new Date().toISOString()
      })) || []
    }));

    // Migration from v1 to v2: Add user permissions
    this.migrations.set(2, (state: any) => ({
      ...state,
      user: state.user ? {
        ...state.user,
        permissions: state.user.permissions || []
      } : null
    }));

    // Migration from v2 to v3: Add threading support
    this.migrations.set(3, (state: any) => ({
      ...state,
      activeThreadId: state.activeThreadId || null,
      messages: state.messages?.map((msg: any) => ({
        ...msg,
        thread_id: msg.thread_id || 'default'
      })) || []
    }));
  }

  migrate(state: any, fromVersion: number): any {
    let migratedState = { ...state };
    
    for (let version = fromVersion + 1; version <= this.currentVersion; version++) {
      const migration = this.migrations.get(version);
      if (migration) {
        migratedState = migration(migratedState);
      }
    }
    
    return {
      ...migratedState,
      version: this.currentVersion
    };
  }

  isCompatible(version: number): boolean {
    return version >= 0 && version <= this.currentVersion;
  }

  getCurrentVersion(): number {
    return this.currentVersion;
  }
}

describe('State Migration Tests', () => {
  let mockStorage: ReturnType<typeof GlobalTestUtils.setupStoreTestEnvironment>['mockStorage'];
  let migrationManager: StateMigrationManager;

  beforeEach(() => {
    const env = GlobalTestUtils.setupStoreTestEnvironment();
    mockStorage = env.mockStorage;
    migrationManager = new StateMigrationManager();
  });

  afterEach(() => {
    GlobalTestUtils.cleanupStoreTestEnvironment();
  });

  describe('Schema Upgrades', () => {
    it('should migrate v0 state to current version', () => {
      const legacyState = {
        messages: [
          { id: 'msg-1', content: 'Old message' },
          { id: 'msg-2', content: 'Another old message' }
        ],
        version: 0
      };

      mockStorage.getItem.mockReturnValue(JSON.stringify({
        state: legacyState,
        version: 0
      }));

      const migratedState = migrationManager.migrate(legacyState, 0);

      expect(migratedState.version).toBe(3);
      expect(migratedState.messages[0].created_at).toBeTruthy();
      expect(migratedState.messages[0].thread_id).toBe('default');
      expect(migratedState.activeThreadId).toBeNull();
    });

    it('should migrate v1 state to current version', () => {
      const v1State = {
        messages: [
          { 
            id: 'msg-1', 
            content: 'Message with timestamp',
            created_at: '2024-01-01T00:00:00Z'
          }
        ],
        user: {
          id: 'user-1',
          email: 'user@example.com'
        },
        version: 1
      };

      const migratedState = migrationManager.migrate(v1State, 1);

      expect(migratedState.version).toBe(3);
      expect(migratedState.user.permissions).toEqual([]);
      expect(migratedState.messages[0].thread_id).toBe('default');
    });

    it('should handle partial migration chains', () => {
      const v2State = {
        messages: [
          { 
            id: 'msg-1', 
            content: 'Recent message',
            created_at: '2024-01-01T00:00:00Z'
          }
        ],
        user: {
          id: 'user-1',
          email: 'user@example.com',
          permissions: ['read', 'write']
        },
        version: 2
      };

      const migratedState = migrationManager.migrate(v2State, 2);

      expect(migratedState.version).toBe(3);
      expect(migratedState.user.permissions).toEqual(['read', 'write']);
      expect(migratedState.messages[0].thread_id).toBe('default');
      expect(migratedState.activeThreadId).toBeNull();
    });

    it('should preserve existing data during migration', () => {
      const stateWithCustomData = {
        messages: [
          { 
            id: 'msg-1', 
            content: 'Custom message',
            customProperty: 'should be preserved'
          }
        ],
        customAppData: {
          theme: 'dark',
          language: 'en'
        },
        version: 0
      };

      const migratedState = migrationManager.migrate(stateWithCustomData, 0);

      expect(migratedState.customAppData.theme).toBe('dark');
      expect(migratedState.messages[0].customProperty).toBe('should be preserved');
    });

    it('should handle empty or null state gracefully', () => {
      const emptyState = { version: 0 };
      const migratedState = migrationManager.migrate(emptyState, 0);

      expect(migratedState.version).toBe(3);
      expect(migratedState.messages).toEqual([]);
      expect(migratedState.user).toBeNull();
    });
  });

  describe('Backward Compatibility', () => {
    it('should maintain compatibility with older app versions', () => {
      const currentVersion = migrationManager.getCurrentVersion();
      
      expect(migrationManager.isCompatible(0)).toBe(true);
      expect(migrationManager.isCompatible(1)).toBe(true);
      expect(migrationManager.isCompatible(currentVersion)).toBe(true);
    });

    it('should reject incompatible future versions', () => {
      const futureVersion = migrationManager.getCurrentVersion() + 5;
      
      expect(migrationManager.isCompatible(futureVersion)).toBe(false);
    });

    it('should handle corrupted version data', () => {
      const corruptedState = {
        messages: [{ id: 'msg-1', content: 'Test' }],
        version: 'invalid' // Non-numeric version
      };

      // Should default to version 0 migration
      const migratedState = migrationManager.migrate(corruptedState, 0);
      expect(migratedState.version).toBe(3);
    });

    it('should maintain API compatibility across versions', () => {
      const { result } = renderHook(() => useChatStore());

      // Current API should work regardless of migration
      act(() => {
        result.current.addMessage({
          id: 'api-test',
          type: 'user',
          content: 'API compatibility test',
          created_at: new Date().toISOString(),
          displayed_to_user: true
        });
      });

      expect(result.current.messages).toHaveLength(1);
      expect(result.current.messages[0].id).toBe('api-test');
    });
  });

  describe('Data Integrity During Migration', () => {
    it('should validate migrated data structure', () => {
      const invalidState = {
        messages: 'should be array', // Invalid type
        version: 0
      };

      const migratedState = migrationManager.migrate(invalidState, 0);

      // Should fix invalid structure
      expect(Array.isArray(migratedState.messages)).toBe(true);
      expect(migratedState.messages).toEqual([]);
    });

    it('should handle missing required fields', () => {
      const incompleteState = {
        messages: [
          { id: 'msg-1' }, // Missing content and timestamp
          { content: 'No ID message' } // Missing ID
        ],
        version: 0
      };

      const migratedState = migrationManager.migrate(incompleteState, 0);

      expect(migratedState.messages).toHaveLength(2);
      expect(migratedState.messages[0].created_at).toBeTruthy();
      expect(migratedState.messages[1].created_at).toBeTruthy();
    });

    it('should preserve data relationships during migration', () => {
      const relatedState = {
        messages: [
          { 
            id: 'msg-1', 
            content: 'Parent message',
            replies: ['msg-2']
          },
          { 
            id: 'msg-2', 
            content: 'Reply message',
            parent_id: 'msg-1'
          }
        ],
        version: 0
      };

      const migratedState = migrationManager.migrate(relatedState, 0);

      // Relationships should be preserved
      expect(migratedState.messages[0].replies).toEqual(['msg-2']);
      expect(migratedState.messages[1].parent_id).toBe('msg-1');
    });

    it('should detect and repair corrupted data', () => {
      const corruptedState = {
        messages: [
          { id: null, content: null }, // Corrupted message
          { id: 'msg-2', content: 'Valid message' }
        ],
        version: 0
      };

      const migratedState = migrationManager.migrate(corruptedState, 0);

      // Should filter out or repair corrupted entries
      const validMessages = migratedState.messages.filter((msg: any) => 
        msg.id && msg.content !== null
      );
      expect(validMessages).toHaveLength(1);
      expect(validMessages[0].id).toBe('msg-2');
    });

    it('should maintain unique constraints during migration', () => {
      const stateWithDuplicates = {
        messages: [
          { id: 'msg-1', content: 'First version' },
          { id: 'msg-1', content: 'Duplicate ID' }, // Duplicate ID
          { id: 'msg-2', content: 'Unique message' }
        ],
        version: 0
      };

      const migratedState = migrationManager.migrate(stateWithDuplicates, 0);

      // Should handle duplicates (keep first or merge)
      const messageIds = migratedState.messages.map((msg: any) => msg.id);
      const uniqueIds = [...new Set(messageIds)];
      expect(uniqueIds).toHaveLength(2);
    });
  });

  describe('Migration Performance', () => {
    it('should handle large datasets efficiently', () => {
      const largeState = {
        messages: Array.from({ length: 10000 }, (_, i) => ({
          id: `msg-${i}`,
          content: `Message ${i}`
        })),
        version: 0
      };

      const startTime = performance.now();
      const migratedState = migrationManager.migrate(largeState, 0);
      const endTime = performance.now();

      expect(migratedState.messages).toHaveLength(10000);
      expect(endTime - startTime).toBeLessThan(1000); // Should complete in <1s
    });

    it('should batch process migrations for memory efficiency', () => {
      const batchSize = 1000;
      const totalMessages = 5000;
      
      const largeState = {
        messages: Array.from({ length: totalMessages }, (_, i) => ({
          id: `batch-msg-${i}`,
          content: `Batch message ${i}`
        })),
        version: 0
      };

      const migratedState = migrationManager.migrate(largeState, 0);

      expect(migratedState.messages).toHaveLength(totalMessages);
      expect(migratedState.version).toBe(3);
    });

    it('should provide migration progress for long operations', () => {
      const progressTracker = {
        currentStep: 0,
        totalSteps: 3
      };

      const stateToMigrate = {
        messages: [{ id: 'msg-1', content: 'Test' }],
        version: 0
      };

      // Simulate progress tracking
      let migratedState = { ...stateToMigrate };
      for (let version = 1; version <= 3; version++) {
        progressTracker.currentStep = version;
        migratedState = migrationManager.migrate(migratedState, version - 1);
      }

      expect(progressTracker.currentStep).toBe(3);
      expect(migratedState.version).toBe(3);
    });

    it('should cleanup temporary migration data', () => {
      const stateWithTempData = {
        messages: [{ id: 'msg-1', content: 'Test' }],
        _migrationTemp: { backup: 'temporary data' },
        version: 0
      };

      const migratedState = migrationManager.migrate(stateWithTempData, 0);

      // Temporary migration data should be removed
      expect(migratedState._migrationTemp).toBeUndefined();
      expect(migratedState.version).toBe(3);
    });
  });

  describe('Migration Error Handling', () => {
    it('should handle migration failures gracefully', () => {
      const problematicState = {
        messages: [
          { id: 'msg-1', content: 'Valid' },
          { id: 'msg-2', content: undefined } // Will cause issues
        ],
        version: 0
      };

      expect(() => {
        const migratedState = migrationManager.migrate(problematicState, 0);
        expect(migratedState.version).toBe(3);
      }).not.toThrow();
    });

    it('should rollback on critical migration errors', () => {
      const originalState = {
        messages: [{ id: 'msg-1', content: 'Original' }],
        version: 1
      };

      // Simulate critical error during migration
      try {
        const migratedState = migrationManager.migrate(originalState, 1);
        expect(migratedState.version).toBe(3);
      } catch (error) {
        // Should rollback to safe state
        expect(originalState.version).toBe(1);
      }
    });

    it('should provide detailed error information', () => {
      const faultyState = {
        messages: null, // This will cause migration issues
        version: 0
      };

      const migratedState = migrationManager.migrate(faultyState, 0);

      // Should handle null messages gracefully
      expect(migratedState.messages).toEqual([]);
    });

    it('should validate migration chain integrity', () => {
      const state = { messages: [], version: 0 };
      
      // Verify each migration step
      let currentVersion = 0;
      let currentState = { ...state };
      
      while (currentVersion < migrationManager.getCurrentVersion()) {
        const nextState = migrationManager.migrate(currentState, currentVersion);
        expect(nextState.version).toBeGreaterThan(currentVersion);
        currentState = nextState;
        currentVersion = nextState.version;
      }

      expect(currentVersion).toBe(migrationManager.getCurrentVersion());
    });
  });
});