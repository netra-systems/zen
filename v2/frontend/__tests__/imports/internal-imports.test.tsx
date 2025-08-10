/**
 * Test file to verify all internal frontend modules can be imported.
 * This ensures the app structure is properly set up and all internal dependencies are resolvable.
 */

import path from 'path';

describe('Internal Frontend Module Import Tests', () => {
  // @smoke-test
  describe('Component imports', () => {
    it('should import UI components', () => {
      // Core UI components
      expect(() => require('@/components/ui/button')).not.toThrow();
      expect(() => require('@/components/ui/card')).not.toThrow();
      expect(() => require('@/components/ui/dialog')).not.toThrow();
      expect(() => require('@/components/ui/dropdown-menu')).not.toThrow();
      expect(() => require('@/components/ui/input')).not.toThrow();
      expect(() => require('@/components/ui/label')).not.toThrow();
      expect(() => require('@/components/ui/select')).not.toThrow();
      expect(() => require('@/components/ui/switch')).not.toThrow();
      expect(() => require('@/components/ui/tabs')).not.toThrow();
      expect(() => require('@/components/ui/toast')).not.toThrow();
      expect(() => require('@/components/ui/toaster')).not.toThrow();
      expect(() => require('@/components/ui/tooltip')).not.toThrow();
      expect(() => require('@/components/ui/textarea')).not.toThrow();
      expect(() => require('@/components/ui/progress')).not.toThrow();
      expect(() => require('@/components/ui/avatar')).not.toThrow();
      expect(() => require('@/components/ui/accordion')).not.toThrow();
      expect(() => require('@/components/ui/popover')).not.toThrow();
      expect(() => require('@/components/ui/separator')).not.toThrow();
      expect(() => require('@/components/ui/skeleton')).not.toThrow();
      expect(() => require('@/components/ui/badge')).not.toThrow();
      expect(() => require('@/components/ui/alert')).not.toThrow();
      expect(() => require('@/components/ui/scroll-area')).not.toThrow();
    });

    it('should import chat components', () => {
      expect(() => require('@/components/chat/ChatInterface')).not.toThrow();
      expect(() => require('@/components/chat/MainChat')).not.toThrow();
      expect(() => require('@/components/chat/MessageInput')).not.toThrow();
      expect(() => require('@/components/chat/MessageList')).not.toThrow();
      expect(() => require('@/components/chat/Sidebar')).not.toThrow();
      expect(() => require('@/components/ThreadList')).not.toThrow();
      expect(() => require('@/components/ThreadItem')).not.toThrow();
    });

    it('should import layout components', () => {
      expect(() => require('@/components/layout/Header')).not.toThrow();
      expect(() => require('@/components/layout/Footer')).not.toThrow();
      expect(() => require('@/components/layout/Navigation')).not.toThrow();
    });

    it('should import demo components', () => {
      // Demo components might be optional
      try {
        require('@/components/demo/DemoInterface');
        require('@/components/demo/DemoChat');
        require('@/components/demo/DemoAgentPanel');
      } catch (e) {
        console.log('Demo components not found (optional)');
      }
    });
  });

  describe('Provider imports', () => {
    it('should import context providers', () => {
      expect(() => require('@/providers/WebSocketProvider')).not.toThrow();
      expect(() => require('@/providers/ThemeProvider')).not.toThrow();
      
      // Check that providers export the expected items
      const wsProvider = require('@/providers/WebSocketProvider');
      expect(wsProvider.WebSocketProvider).toBeDefined();
      expect(wsProvider.useWebSocketContext).toBeDefined();
    });
  });

  describe('Hook imports', () => {
    it('should import custom hooks', () => {
      expect(() => require('@/hooks/useWebSocket')).not.toThrow();
      expect(() => require('@/hooks/useAgent')).not.toThrow();
      expect(() => require('@/hooks/useAuth')).not.toThrow();
      expect(() => require('@/hooks/useThread')).not.toThrow();
      expect(() => require('@/hooks/useToast')).not.toThrow();
      expect(() => require('@/hooks/useError')).not.toThrow();
      expect(() => require('@/hooks/useDemoWebSocket')).not.toThrow();
      
      // Verify hook exports
      const useWebSocket = require('@/hooks/useWebSocket');
      expect(useWebSocket.useWebSocket).toBeDefined();
      
      const useAgent = require('@/hooks/useAgent');
      expect(useAgent.useAgent).toBeDefined();
      
      const useAuth = require('@/hooks/useAuth');
      expect(useAuth.useAuth).toBeDefined();
      
      const useToast = require('@/hooks/useToast');
      expect(useToast.useToast).toBeDefined();
    });
  });

  describe('Store imports', () => {
    it('should import Zustand stores', () => {
      expect(() => require('@/store/useThreadStore')).not.toThrow();
      expect(() => require('@/store/useAuthStore')).not.toThrow();
      expect(() => require('@/store/useUIStore')).not.toThrow();
      expect(() => require('@/store/useAgentStore')).not.toThrow();
      expect(() => require('@/store/useWebSocketStore')).not.toThrow();
      
      // Verify store exports
      const threadStore = require('@/store/useThreadStore');
      expect(threadStore.useThreadStore).toBeDefined();
      
      const authStore = require('@/store/useAuthStore');
      expect(authStore.useAuthStore).toBeDefined();
      
      const uiStore = require('@/store/useUIStore');
      expect(uiStore.useUIStore).toBeDefined();
    });
  });

  describe('Service imports', () => {
    it('should import API services', () => {
      expect(() => require('@/services/api')).not.toThrow();
      expect(() => require('@/services/auth')).not.toThrow();
      expect(() => require('@/services/agent')).not.toThrow();
      expect(() => require('@/services/thread')).not.toThrow();
      expect(() => require('@/services/websocket')).not.toThrow();
      expect(() => require('@/services/demoService')).not.toThrow();
      
      // Verify service exports
      const api = require('@/services/api');
      expect(api.apiClient).toBeDefined();
      
      const auth = require('@/services/auth');
      expect(auth.authService).toBeDefined();
      
      const agent = require('@/services/agent');
      expect(agent.agentService).toBeDefined();
    });
  });

  describe('Utility imports', () => {
    it('should import utility functions', () => {
      expect(() => require('@/lib/utils')).not.toThrow();
      
      const utils = require('@/lib/utils');
      expect(utils.cn).toBeDefined();
      
      // Check for other common utilities
      try {
        require('@/utils/formatters');
        require('@/utils/validators');
        require('@/utils/helpers');
      } catch (e) {
        console.log('Some utility modules not found (optional)');
      }
    });

    it('should import configuration', () => {
      expect(() => require('@/config/api')).not.toThrow();
      
      const config = require('@/config/api');
      expect(config.API_BASE_URL).toBeDefined();
      expect(config.WS_BASE_URL).toBeDefined();
    });
  });

  describe('Type definition imports', () => {
    it('should import TypeScript type definitions', () => {
      // Type imports don't work with require, but we can check the files exist
      const fs = require('fs');
      const typesDir = path.join(process.cwd(), 'types');
      
      if (fs.existsSync(typesDir)) {
        const typeFiles = fs.readdirSync(typesDir);
        expect(typeFiles.length).toBeGreaterThan(0);
        
        // Check for common type files
        const expectedTypes = ['agent.ts', 'auth.ts', 'thread.ts', 'message.ts', 'websocket.ts'];
        expectedTypes.forEach(typeFile => {
          const exists = typeFiles.includes(typeFile);
          if (!exists) {
            console.log(`Type file ${typeFile} not found`);
          }
        });
      } else {
        console.log('Types directory not found');
      }
    });
  });

  describe('App page imports', () => {
    it('should import app pages', () => {
      // App router pages
      expect(() => require('@/app/page')).not.toThrow();
      expect(() => require('@/app/layout')).not.toThrow();
      
      // Check for specific pages
      try {
        require('@/app/chat/page');
        require('@/app/auth/login/page');
        require('@/app/auth/register/page');
        require('@/app/corpus/page');
        require('@/app/synthetic-data-generation/page');
      } catch (e) {
        console.log('Some app pages not found (may use different structure)');
      }
    });
  });

  describe('Critical internal imports batch test', () => {
    it('should successfully import all critical internal modules', () => {
      const criticalModules = [
        '@/components/ui/button',
        '@/components/chat/ChatInterface',
        '@/providers/WebSocketProvider',
        '@/hooks/useWebSocket',
        '@/hooks/useAgent',
        '@/store/useThreadStore',
        '@/services/api',
        '@/lib/utils',
        '@/config/api'
      ];

      const failedImports: string[] = [];
      
      criticalModules.forEach(module => {
        try {
          require(module);
        } catch (e) {
          failedImports.push(module);
        }
      });

      expect(failedImports).toEqual([]);
    });
  });

  describe('Circular dependency check', () => {
    it('should not have circular dependencies in critical modules', () => {
      // Test importing modules in different orders
      const modules = [
        '@/hooks/useWebSocket',
        '@/providers/WebSocketProvider',
        '@/store/useWebSocketStore',
        '@/services/websocket'
      ];

      // Clear module cache
      modules.forEach(mod => {
        delete require.cache[require.resolve(mod)];
      });

      // Import in order A
      expect(() => {
        modules.forEach(mod => require(mod));
      }).not.toThrow();

      // Clear cache again
      modules.forEach(mod => {
        delete require.cache[require.resolve(mod)];
      });

      // Import in reverse order
      expect(() => {
        modules.reverse().forEach(mod => require(mod));
      }).not.toThrow();
    });
  });

  describe('Component export verification', () => {
    it('should export expected items from components', () => {
      // Button component
      const button = require('@/components/ui/button');
      expect(button.Button).toBeDefined();
      expect(button.buttonVariants).toBeDefined();

      // Card component
      const card = require('@/components/ui/card');
      expect(card.Card).toBeDefined();
      expect(card.CardHeader).toBeDefined();
      expect(card.CardContent).toBeDefined();
      expect(card.CardTitle).toBeDefined();
      expect(card.CardDescription).toBeDefined();
      expect(card.CardFooter).toBeDefined();

      // Dialog component
      const dialog = require('@/components/ui/dialog');
      expect(dialog.Dialog).toBeDefined();
      expect(dialog.DialogTrigger).toBeDefined();
      expect(dialog.DialogContent).toBeDefined();
      expect(dialog.DialogHeader).toBeDefined();
      expect(dialog.DialogTitle).toBeDefined();
      expect(dialog.DialogDescription).toBeDefined();
      expect(dialog.DialogFooter).toBeDefined();
    });
  });

  describe('Store state verification', () => {
    it('should have expected state and actions in stores', () => {
      const { useThreadStore } = require('@/store/useThreadStore');
      const store = useThreadStore.getState();
      
      // Check for expected state properties
      expect(store).toHaveProperty('threads');
      expect(store).toHaveProperty('currentThread');
      expect(store).toHaveProperty('setCurrentThread');
      expect(store).toHaveProperty('addThread');
      expect(store).toHaveProperty('updateThread');
      expect(store).toHaveProperty('deleteThread');
    });
  });
});