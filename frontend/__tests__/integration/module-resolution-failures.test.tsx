/**
 * Module Resolution Failures Integration Test Suite
 * 
 * PURPOSE: This test suite is designed to FAIL when module resolution issues occur
 * during real-world usage patterns. These tests simulate actual component imports
 * and build processes that would fail in production.
 * 
 * EXPECTED FAILURES:
 * - Test 1: Will FAIL if components cannot import from registry due to duplicate exports
 * - Test 2: Will FAIL on webpack module parsing during build simulation
 * - Test 3: Will FAIL on Next.js build process with module errors
 * - Test 4: Will FAIL on dynamic imports with module conflicts
 * - Test 5: Will FAIL on SSR/CSR hydration mismatches due to module issues
 */

import React from 'react';
import { render, renderHook, waitFor } from '@testing-library/react';
import { act } from 'react-dom/test-utils';
import * as webpack from 'webpack';
import * as path from 'path';
import * as fs from 'fs/promises';

describe('Module Resolution Failures - Integration Tests', () => {
  
      setupAntiHang();
  
    jest.setTimeout(10000);
  
  /**
   * This test will FAIL when components cannot import from registry
   * due to the duplicate isValidWebSocketMessageType export
   */
  it('should FAIL if components cannot import from registry', () => {
    // This will fail with module parse error
    expect(() => {
      const TestComponent: React.FC = () => {
        // Attempt to import from registry - will fail due to duplicate export
        const { 
          isValidWebSocketMessageType,
          WebSocketMessageType,
          MessageType,
          AgentStatus 
        } = require('../../types/registry');
        
        return (
          <div data-testid="test-component">
            <p>Message Type Valid: {isValidWebSocketMessageType('user_message') ? 'Yes' : 'No'}</p>
            <p>WebSocket Types: {Object.keys(WebSocketMessageType).length}</p>
            <p>Message Types: {Object.keys(MessageType).length}</p>
            <p>Agent Status Types: {Object.keys(AgentStatus).length}</p>
          </div>
        );
      };
      
      const { getByTestId } = render(<TestComponent />);
      expect(getByTestId('test-component')).toBeTruthy();
    }).not.toThrow(/Duplicate export/);
  });

  /**
   * This test will FAIL on runtime reference errors in hooks
   */
  it('should detect runtime reference errors in component hooks', () => {
    const { result, error } = renderHook(() => {
      try {
        // This import will fail at module resolution time
        const registry = require('../../types/registry');
        const { 
          WebSocketMessageType, 
          isValidWebSocketMessageType,
          createWebSocketMessage,
          isWebSocketMessage 
        } = registry;
        
        // Try to use the imported functions
        const testMessage = createWebSocketMessage({
          type: WebSocketMessageType.USER_MESSAGE,
          payload: { content: 'test' }
        });
        
        return { 
          success: true, 
          isValid: isValidWebSocketMessageType(testMessage.type),
          isMessage: isWebSocketMessage(testMessage)
        };
      } catch (err: any) {
        return { 
          success: false, 
          error: err.message,
          stack: err.stack 
        };
      }
    });
    
    // Expected to fail with module parse error
    expect(result.current.success).toBe(true);
    
    if (!result.current.success) {
      console.error('❌ Hook import failed:', result.current.error);
      expect(result.current.error).toContain('Duplicate export');
    }
  });

  /**
   * Test webpack module resolution simulation
   */
  it('should FAIL during webpack module resolution', async () => {
    const webpackConfig: webpack.Configuration = {
      mode: 'development',
      entry: path.resolve(__dirname, '../../types/registry.ts'),
      output: {
        path: path.resolve(__dirname, 'dist'),
        filename: 'bundle.js'
      },
      module: {
        rules: [
          {
            test: /\.tsx?$/,
            use: 'ts-loader',
            exclude: /node_modules/
          }
        ]
      },
      resolve: {
        extensions: ['.tsx', '.ts', '.js'],
        alias: {
          '@': path.resolve(__dirname, '../..')
        }
      }
    };

    // Create webpack compiler
    const compiler = webpack(webpackConfig);
    
    // Run webpack compilation
    const stats = await new Promise<webpack.Stats>((resolve, reject) => {
      compiler.run((err, stats) => {
        if (err) reject(err);
        else if (stats) resolve(stats);
        else reject(new Error('No stats returned'));
      });
    });

    const info = stats.toJson();
    
    // Expected to have errors due to duplicate exports
    expect(info.errors).toHaveLength(0);
    
    if (info.errors && info.errors.length > 0) {
      console.error('❌ Webpack compilation errors:');
      info.errors.forEach(error => {
        console.error(`  ${error.message}`);
        if (error.message.includes('Duplicate export')) {
          console.error('    ^ Module parse failed on duplicate export');
        }
      });
    }
    
    // Check for specific duplicate export error
    const hasDuplicateExportError = info.errors?.some(error => 
      error.message.includes('Duplicate export') || 
      error.message.includes('isValidWebSocketMessageType')
    );
    
    expect(hasDuplicateExportError).toBe(false);
  });

  /**
   * Test dynamic imports with module conflicts
   */
  it('should FAIL on dynamic imports with module conflicts', async () => {
    const dynamicImportTest = async () => {
      try {
        // Dynamic import should fail due to module parse error
        const registry = await import('../../types/registry');
        
        // Attempt to use the imported module
        const { isValidWebSocketMessageType, WebSocketMessageType } = registry;
        
        // This shouldn't be reached due to import failure
        return {
          success: true,
          hasFunction: typeof isValidWebSocketMessageType === 'function',
          hasEnum: typeof WebSocketMessageType === 'object'
        };
      } catch (error: any) {
        return {
          success: false,
          error: error.message,
          code: error.code
        };
      }
    };

    const result = await dynamicImportTest();
    
    // Expected to fail
    expect(result.success).toBe(true);
    
    if (!result.success) {
      console.error('❌ Dynamic import failed:', result.error);
      expect(result.error).toContain('Cannot find module');
    }
  });

  /**
   * Test module resolution with different import styles
   */
  it('should FAIL with different import style combinations', () => {
    const importTests = [
      // Named imports
      () => {
        const { isValidWebSocketMessageType } = require('../../types/registry');
        return isValidWebSocketMessageType('test');
      },
      // Namespace import
      () => {
        const registry = require('../../types/registry');
        return registry.isValidWebSocketMessageType('test');
      },
      // Destructured after import
      () => {
        const registry = require('../../types/registry');
        const { isValidWebSocketMessageType, WebSocketMessageType } = registry;
        return isValidWebSocketMessageType(WebSocketMessageType.USER_MESSAGE);
      },
      // Mixed type and runtime imports
      () => {
        const registry = require('../../types/registry');
        // Try to use both type exports and runtime exports
        return {
          types: Object.keys(registry).filter(k => k.includes('Type')),
          functions: Object.keys(registry).filter(k => k.startsWith('is'))
        };
      }
    ];

    const results = importTests.map((test, index) => {
      try {
        return { index, success: true, result: test() };
      } catch (error: any) {
        return { index, success: false, error: error.message };
      }
    });

    // All should fail due to module parse error
    const failures = results.filter(r => !r.success);
    expect(failures).toHaveLength(0);
    
    if (failures.length > 0) {
      console.error('❌ Import style test failures:');
      failures.forEach(failure => {
        console.error(`  Test ${failure.index}: ${failure.error}`);
      });
    }
  });

  /**
   * Test component that uses multiple registry exports
   */
  it('should FAIL when component uses multiple conflicting exports', () => {
    const ComplexComponent: React.FC = () => {
      const [state, setState] = React.useState<any>(null);
      
      React.useEffect(() => {
        try {
          // This will fail at require time
          const {
            // Enums
            WebSocketMessageType,
            MessageType,
            AgentStatus,
            // Validation functions (including duplicate)
            isValidWebSocketMessageType,
            isValidMessageType,
            isValidAgentStatus,
            // Creation functions
            createWebSocketMessage,
            createWebSocketError,
            // Type guards
            isWebSocketMessage,
            isErrorMessage
          } = require('../../types/registry');
          
          // Try to use all imports
          const testResults = {
            enumsLoaded: !!(WebSocketMessageType && MessageType && AgentStatus),
            validationWorks: isValidWebSocketMessageType('user_message'),
            creationWorks: !!createWebSocketMessage,
            typeGuardsWork: typeof isWebSocketMessage === 'function'
          };
          
          setState({ success: true, results: testResults });
        } catch (error: any) {
          setState({ success: false, error: error.message });
        }
      }, []);
      
      if (!state) return <div>Loading...</div>;
      
      return (
        <div data-testid="complex-component">
          {state.success ? (
            <div>
              <p>Enums Loaded: {state.results.enumsLoaded ? 'Yes' : 'No'}</p>
              <p>Validation Works: {state.results.validationWorks ? 'Yes' : 'No'}</p>
              <p>Creation Works: {state.results.creationWorks ? 'Yes' : 'No'}</p>
              <p>Type Guards Work: {state.results.typeGuardsWork ? 'Yes' : 'No'}</p>
            </div>
          ) : (
            <div>
              <p>Error: {state.error}</p>
            </div>
          )}
        </div>
      );
    };
    
    const { getByTestId, getByText } = render(<ComplexComponent />);
    
    // Wait for component to load and check for errors
    waitFor(() => {
      const component = getByTestId('complex-component');
      expect(component).toBeTruthy();
      
      // Should not have error message
      expect(() => getByText(/Error:/)).toThrow();
    });
  });

  /**
   * Test SSR/CSR compatibility with module resolution
   */
  it('should FAIL on SSR/CSR hydration due to module conflicts', () => {
    // Simulate SSR environment
    const ssrResult = (() => {
      try {
        // Clear module cache to simulate fresh SSR
        Object.keys(require.cache).forEach(key => {
          if (key.includes('types/registry')) {
            delete require.cache[key];
          }
        });
        
        const registry = require('../../types/registry');
        return { 
          success: true, 
          exports: Object.keys(registry).sort() 
        };
      } catch (error: any) {
        return { 
          success: false, 
          error: error.message 
        };
      }
    })();
    
    // Simulate CSR environment
    const csrResult = (() => {
      try {
        // Clear cache again for CSR
        Object.keys(require.cache).forEach(key => {
          if (key.includes('types/registry')) {
            delete require.cache[key];
          }
        });
        
        const registry = require('../../types/registry');
        return { 
          success: true, 
          exports: Object.keys(registry).sort() 
        };
      } catch (error: any) {
        return { 
          success: false, 
          error: error.message 
        };
      }
    })();
    
    // Both should fail consistently
    expect(ssrResult.success).toBe(csrResult.success);
    
    if (!ssrResult.success || !csrResult.success) {
      console.error('❌ SSR/CSR module resolution mismatch:');
      console.error('  SSR:', ssrResult);
      console.error('  CSR:', csrResult);
    }
    
    // If both succeed (shouldn't happen), exports should match
    if (ssrResult.success && csrResult.success) {
      expect(ssrResult.exports).toEqual(csrResult.exports);
    }
  });

  /**
   * Test build-time optimization conflicts
   */
  it('should FAIL during tree-shaking and minification', async () => {
    const optimizationTest = async () => {
      // Simulate production build optimizations
      const webpackConfig: webpack.Configuration = {
        mode: 'production',
        entry: {
          main: path.resolve(__dirname, '../../types/registry.ts')
        },
        output: {
          path: path.resolve(__dirname, 'dist'),
          filename: '[name].min.js'
        },
        optimization: {
          usedExports: true,
          sideEffects: false,
          minimize: true
        },
        module: {
          rules: [
            {
              test: /\.tsx?$/,
              use: 'ts-loader',
              exclude: /node_modules/
            }
          ]
        },
        resolve: {
          extensions: ['.tsx', '.ts', '.js']
        }
      };
      
      const compiler = webpack(webpackConfig);
      
      const stats = await new Promise<webpack.Stats>((resolve, reject) => {
        compiler.run((err, stats) => {
          if (err) reject(err);
          else if (stats) resolve(stats);
          else reject(new Error('No stats'));
        });
      });
      
      return stats.toJson();
    };
    
    const buildResult = await optimizationTest();
    
    // Should have errors during optimization
    expect(buildResult.errors).toHaveLength(0);
    expect(buildResult.warnings).toHaveLength(0);
    
    if (buildResult.errors && buildResult.errors.length > 0) {
      console.error('❌ Build optimization errors:');
      buildResult.errors.forEach(error => {
        console.error(`  ${error.message}`);
      });
    }
  });
});

/**
 * Additional test utilities for module resolution testing
 */
export const moduleResolutionTestUtils = {
  /**
   * Simulate a Next.js page component import scenario
   */
  createNextPageTest: () => {
    const PageComponent: React.FC = () => {
      const [registryStatus, setRegistryStatus] = React.useState<string>('loading');
      
      React.useEffect(() => {
        import('../../types/registry')
          .then(registry => {
            if (registry.isValidWebSocketMessageType) {
              setRegistryStatus('loaded');
            } else {
              setRegistryStatus('incomplete');
            }
          })
          .catch(err => {
            setRegistryStatus(`error: ${err.message}`);
          });
      }, []);
      
      return <div>Registry Status: {registryStatus}</div>;
    };
    
    return PageComponent;
  },
  
  /**
   * Create a webpack stats analyzer
   */
  analyzeWebpackStats: (stats: webpack.Stats) => {
    const info = stats.toJson({
      errors: true,
      warnings: true,
      modules: true,
      chunks: true
    });
    
    return {
      hasErrors: info.errors && info.errors.length > 0,
      hasDuplicateExportError: info.errors?.some(e => 
        e.message.includes('Duplicate export')
      ),
      hasModuleParseError: info.errors?.some(e => 
        e.message.includes('Module parse failed')
      ),
      affectedModules: info.modules?.filter(m => 
        m.name?.includes('registry') || m.name?.includes('websocket')
      )
    };
  }
};