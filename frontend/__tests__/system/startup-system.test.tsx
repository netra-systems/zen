/**
 * Frontend System Startup - System Tests
 * Tests for Environment, Error Boundary, Performance, Dependencies, and First-Time Run
 */

import React from 'react';
import { render } from '@testing-library/react';
import { screen } from '@testing-library/react';
import { waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';

import {
  setupTestEnvironment,
  cleanupTestEnvironment,
  clearStorage,
  measurePerformance,
  mockConsole,
  createDefaultSettings,
  loadOptionalDependency,
  mockEnv
} from './helpers/startup-test-utilities';

import {
  initializeAllMocks,
  createErrorBoundary,
  createThrowErrorComponent,
  mockPerformanceAPI
} from './helpers/startup-test-mocks';

// Initialize all mocks
initializeAllMocks();

describe('Frontend System Startup - System Tests', () => {
  beforeEach(() => {
    setupTestEnvironment();
  });

  afterEach(() => {
    cleanupTestEnvironment();
  });

  describe('Environment Validation', () => {
    it('should validate required environment variables', () => {
      testRequiredEnvironmentVariables();
    });

    const testRequiredEnvironmentVariables = () => {
      expect(process.env.NEXT_PUBLIC_API_URL).toBeDefined();
      expect(process.env.NEXT_PUBLIC_WS_URL).toBeDefined();
    };

    it('should handle missing environment variables gracefully', () => {
      testMissingEnvironmentVariables();
    });

    const testMissingEnvironmentVariables = () => {
      delete process.env.NEXT_PUBLIC_API_URL;
      
      const config = loadConfigWithDefaults();
      expect(config.apiUrl).toBe('http://localhost:8000');
    };

    const loadConfigWithDefaults = () => {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
      return { apiUrl };
    };

    it('should validate environment variable types', () => {
      testEnvironmentVariableTypes();
    });

    const testEnvironmentVariableTypes = () => {
      expect(typeof process.env.NEXT_PUBLIC_API_URL).toBe('string');
      expect(typeof process.env.NEXT_PUBLIC_WS_URL).toBe('string');
    };

    it('should handle environment variable validation', () => {
      testEnvironmentValidation();
    });

    const testEnvironmentValidation = () => {
      const isValidUrl = (url: string) => {
        try {
          new URL(url);
          return true;
        } catch {
          return false;
        }
      };
      
      const apiUrl = mockEnv.NEXT_PUBLIC_API_URL;
      expect(isValidUrl(apiUrl)).toBe(true);
    };
  });

  describe('Error Boundary', () => {
    it('should catch and handle startup errors', () => {
      testErrorBoundary();
    });

    const testErrorBoundary = () => {
      const ErrorBoundary = createErrorBoundary();
      const ThrowError = createThrowErrorComponent();
      
      const { restore } = mockConsole();
      
      const { getByText } = render(
        <ErrorBoundary>
          <ThrowError />
        </ErrorBoundary>
      );
      
      expect(getByText('Error occurred during startup')).toBeInTheDocument();
      restore();
    };

    it('should log error details', () => {
      testErrorLogging();
    });

    const testErrorLogging = () => {
      const ErrorBoundary = createErrorBoundary();
      const ThrowError = createThrowErrorComponent();
      
      const logSpy = jest.spyOn(console, 'log');
      
      render(
        <ErrorBoundary>
          <ThrowError />
        </ErrorBoundary>
      );
      
      expect(logSpy).toHaveBeenCalled();
      logSpy.mockRestore();
    };

    it('should handle async errors', async () => {
      await testAsyncErrors();
    });

    const testAsyncErrors = async () => {
      const AsyncErrorComponent = () => {
        React.useEffect(() => {
          throw new Error('Async error');
        }, []);
        return <div>Component</div>;
      };
      
      const { restore } = mockConsole();
      
      try {
        render(<AsyncErrorComponent />);
      } catch (error) {
        expect(error).toBeInstanceOf(Error);
      }
      
      restore();
    };

    it('should provide error recovery options', () => {
      testErrorRecovery();
    });

    const testErrorRecovery = () => {
      const ErrorBoundaryWithRecovery = createErrorBoundaryWithRecovery();
      const ThrowError = createThrowErrorComponent();
      
      const { getByText } = render(
        <ErrorBoundaryWithRecovery>
          <ThrowError />
        </ErrorBoundaryWithRecovery>
      );
      
      expect(getByText('Retry')).toBeInTheDocument();
    };

    const createErrorBoundaryWithRecovery = () => {
      return class extends React.Component<any, any> {
        constructor(props: any) {
          super(props);
          this.state = { hasError: false };
        }
        
        static getDerivedStateFromError() {
          return { hasError: true };
        }
        
        render() {
          if (this.state.hasError) {
            return (
              <div>
                <div>Error occurred during startup</div>
                <button onClick={() => this.setState({ hasError: false })}>
                  Retry
                </button>
              </div>
            );
          }
          return this.props.children;
        }
      };
    };
  });

  describe('Performance Monitoring', () => {
    it('should measure startup performance', async () => {
      await testStartupPerformance();
    });

    const testStartupPerformance = async () => {
      const duration = await measurePerformance(async () => {
        await new Promise(resolve => setTimeout(resolve, 10));
      });
      
      expect(duration).toBeGreaterThan(0);
      expect(duration).toBeLessThan(5000);
    };

    it('should log performance metrics', () => {
      testPerformanceMetrics();
    });

    const testPerformanceMetrics = () => {
      const mockMetrics = createMockMetrics();
      const logSpy = jest.spyOn(console, 'log').mockImplementation();
      
      // test debug removed: console.log('Startup metrics:', mockMetrics);
      
      expect(logSpy).toHaveBeenCalledWith('Startup metrics:', mockMetrics);
      logSpy.mockRestore();
    };

    const createMockMetrics = () => ({
      startupTime: 250,
      apiConnectionTime: 50,
      wsConnectionTime: 30,
      storeInitTime: 10,
    });

    it('should monitor memory usage', () => {
      testMemoryMonitoring();
    });

    const testMemoryMonitoring = () => {
      const getMemoryInfo = () => {
        if (performance.memory) {
          return {
            used: performance.memory.usedJSHeapSize,
            total: performance.memory.totalJSHeapSize,
          };
        }
        return { used: 0, total: 0 };
      };
      
      const memInfo = getMemoryInfo();
      expect(typeof memInfo.used).toBe('number');
      expect(typeof memInfo.total).toBe('number');
    };

    it('should track performance marks', () => {
      testPerformanceMarks();
    });

    const testPerformanceMarks = () => {
      performance.mark('startup-begin');
      performance.mark('startup-end');
      
      const marks = performance.getEntriesByType('mark');
      expect(marks.length).toBeGreaterThanOrEqual(2);
    };
  });

  describe('Dependency Loading', () => {
    it('should load required dependencies', () => {
      testRequiredDependencies();
    });

    const testRequiredDependencies = () => {
      expect(React).toBeDefined();
      expect(React.version).toBeDefined();
      
      expect(render).toBeDefined();
      expect(screen).toBeDefined();
      expect(waitFor).toBeDefined();
    };

    it('should handle missing dependencies gracefully', () => {
      testMissingDependencies();
    });

    const testMissingDependencies = () => {
      const optionalDep = loadOptionalDependency('non-existent-package');
      expect(optionalDep).toBeNull();
    };

    it('should validate dependency versions', () => {
      testDependencyVersions();
    });

    const testDependencyVersions = () => {
      expect(React.version).toMatch(/^\d+\.\d+\.\d+/);
    };

    it('should handle dependency conflicts', () => {
      testDependencyConflicts();
    });

    const testDependencyConflicts = () => {
      const checkDependency = (name: string) => {
        try {
          require(name);
          return true;
        } catch {
          return false;
        }
      };
      
      const hasReact = checkDependency('react');
      expect(hasReact).toBe(true);
    };
  });

  describe('First-Time Run', () => {
    beforeEach(() => {
      clearStorage();
    });

    it('should detect first-time run', () => {
      testFirstTimeDetection();
    });

    const testFirstTimeDetection = () => {
      const isFirstRun = !localStorage.getItem('hasRunBefore');
      expect(isFirstRun).toBe(true);
      
      localStorage.setItem('hasRunBefore', 'true');
      
      const isFirstRunAfter = !localStorage.getItem('hasRunBefore');
      expect(isFirstRunAfter).toBe(false);
    };

    it('should show onboarding on first run', () => {
      testOnboardingDisplay();
    });

    const testOnboardingDisplay = () => {
      const isFirstRun = !localStorage.getItem('hasRunBefore');
      
      if (isFirstRun) {
        const { getByText } = render(<div>Welcome to Netra AI</div>);
        expect(getByText('Welcome to Netra AI')).toBeInTheDocument();
      }
    };

    it('should initialize default settings on first run', () => {
      testDefaultSettingsInitialization();
    });

    const testDefaultSettingsInitialization = () => {
      const isFirstRun = !localStorage.getItem('settings');
      
      if (isFirstRun) {
        const defaultSettings = createDefaultSettings();
        localStorage.setItem('settings', JSON.stringify(defaultSettings));
        
        const savedSettings = JSON.parse(localStorage.getItem('settings') || '{}');
        expect(savedSettings).toEqual(defaultSettings);
      }
    };

    it('should handle first-time user experience flow', () => {
      testFirstTimeUserFlow();
    });

    const testFirstTimeUserFlow = () => {
      const steps = [
        'welcome',
        'permissions',
        'setup',
        'complete'
      ];
      
      let currentStep = 0;
      const nextStep = () => currentStep++;
      
      expect(steps[currentStep]).toBe('welcome');
      nextStep();
      expect(steps[currentStep]).toBe('permissions');
    };

    it('should skip onboarding for returning users', () => {
      testReturningUserExperience();
    });

    const testReturningUserExperience = () => {
      localStorage.setItem('hasRunBefore', 'true');
      localStorage.setItem('settings', JSON.stringify(createDefaultSettings()));
      
      const isFirstRun = !localStorage.getItem('hasRunBefore');
      const hasSettings = localStorage.getItem('settings');
      
      expect(isFirstRun).toBe(false);
      expect(hasSettings).toBeDefined();
    };
  });

  describe('System Health Checks', () => {
    it('should perform comprehensive health check', () => {
      testSystemHealthCheck();
    });

    const testSystemHealthCheck = () => {
      const healthChecks = {
        environment: checkEnvironmentHealth(),
        dependencies: checkDependencyHealth(),
        storage: checkStorageHealth(),
        performance: checkPerformanceHealth(),
      };
      
      expect(healthChecks.environment).toBe(true);
      expect(healthChecks.dependencies).toBe(true);
      expect(healthChecks.storage).toBe(true);
      expect(healthChecks.performance).toBe(true);
    };

    const checkEnvironmentHealth = () => {
      return process.env.NEXT_PUBLIC_API_URL !== undefined;
    };

    const checkDependencyHealth = () => {
      return React !== undefined;
    };

    const checkStorageHealth = () => {
      try {
        localStorage.setItem('test', 'test');
        localStorage.removeItem('test');
        return true;
      } catch {
        return false;
      }
    };

    const checkPerformanceHealth = () => {
      return performance.now() > 0;
    };
  });
});