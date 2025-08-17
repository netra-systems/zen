/**
 * Error Recovery Integration Tests
 * 
 * BVJ: Enterprise segment - ensures platform resilience and error recovery
 * Tests advanced error boundaries, graceful degradation, and recovery mechanisms.
 */

import {
  React,
  render,
  waitFor,
  fireEvent,
  setupTestEnvironment,
  cleanupTestEnvironment,
  createMockWebSocketServer,
  createMockError,
  TEST_TIMEOUTS,
  WS
} from './test-utils';

import {
  PERFORMANCE_THRESHOLDS
} from './utils/performance-test-utils';

// Apply Next.js navigation mock
jest.mock('next/navigation', () => ({
  useRouter: () => ({
    push: jest.fn(),
    replace: jest.fn(),
    refresh: jest.fn(),
    back: jest.fn(),
    forward: jest.fn(),
    pathname: '/',
    query: {},
    asPath: '/',
  }),
  usePathname: () => '/',
  useSearchParams: () => new URLSearchParams(),
}));

describe('Error Recovery Integration Tests', () => {
  let server: WS;
  
  beforeEach(() => {
    server = createMockWebSocketServer();
    setupTestEnvironment(server);
  });

  afterEach(() => {
    cleanupTestEnvironment();
  });

  describe('Advanced Error Boundaries', () => {
    it('should recover from component errors gracefully', async () => {
      const TestWrapper = createErrorBoundaryTestWrapper();
      
      const { getByText, getByTestId } = render(<TestWrapper />);
      
      await verifyInitialWorkingState(getByTestId);
      await triggerComponentError(getByText, getByTestId);
      await testErrorRecovery(getByText, getByTestId);
    });

    it('should handle cascading errors with isolation', async () => {
      const CascadingErrorComponent = createCascadingErrorComponent();
      
      const { getByText, getByTestId } = render(<CascadingErrorComponent />);
      
      await testCascadingErrorIsolation(getByText, getByTestId);
    });

    it('should maintain error context and logging', async () => {
      const ErrorLoggingComponent = createErrorLoggingComponent();
      
      const { getByText, getByTestId } = render(<ErrorLoggingComponent />);
      
      await testErrorLogging(getByText, getByTestId);
    });
  });

  describe('Graceful Degradation', () => {
    it('should degrade gracefully when features fail', async () => {
      const GracefulDegradationComponent = createGracefulDegradationComponent();
      
      const { getByText, getByTestId } = render(<GracefulDegradationComponent />);
      
      await testFeatureDegradation(getByText, getByTestId);
    });

    it('should provide fallback UI for failed components', async () => {
      const FallbackUIComponent = createFallbackUIComponent();
      
      const { getByText, getByTestId } = render(<FallbackUIComponent />);
      
      await testFallbackUI(getByText, getByTestId);
    });
  });

  describe('Recovery Mechanisms', () => {
    it('should implement automatic retry with backoff', async () => {
      const RetryMechanismComponent = createRetryMechanismComponent();
      
      const { getByText, getByTestId } = render(<RetryMechanismComponent />);
      
      await testRetryMechanism(getByText, getByTestId);
    });

    it('should handle partial system recovery', async () => {
      const PartialRecoveryComponent = createPartialRecoveryComponent();
      
      const { getByText, getByTestId } = render(<PartialRecoveryComponent />);
      
      await testPartialRecovery(getByText, getByTestId);
    });
  });
});

// Error Boundary Component
class ErrorBoundary extends React.Component<
  { children: React.ReactNode },
  { hasError: boolean; errorInfo: any; retryCount: number }
> {
  constructor(props: any) {
    super(props);
    this.state = { hasError: false, errorInfo: null, retryCount: 0 };
  }
  
  static getDerivedStateFromError(error: Error) {
    return { hasError: true };
  }
  
  componentDidCatch(error: Error, errorInfo: any) {
    this.setState({ errorInfo });
  }
  
  retry = () => {
    this.setState(prev => ({
      hasError: false,
      errorInfo: null,
      retryCount: prev.retryCount + 1
    }));
  }
  
  render() {
    if (this.state.hasError) {
      return renderErrorBoundaryUI(this.state.retryCount, this.retry);
    }
    
    return this.props.children;
  }
}

// Enhanced Error Boundary with Isolation
class IsolatedErrorBoundary extends React.Component<
  { children: React.ReactNode; componentName: string },
  { hasError: boolean; isolatedComponents: Set<string> }
> {
  constructor(props: any) {
    super(props);
    this.state = { hasError: false, isolatedComponents: new Set() };
  }
  
  static getDerivedStateFromError(error: Error) {
    return { hasError: true };
  }
  
  componentDidCatch(error: Error, errorInfo: any) {
    this.setState(prev => ({
      isolatedComponents: new Set([...prev.isolatedComponents, this.props.componentName])
    }));
  }
  
  render() {
    if (this.state.hasError) {
      return renderIsolatedErrorUI(this.props.componentName, this.state.isolatedComponents.size);
    }
    
    return this.props.children;
  }
}

// Component factory functions (≤8 lines each)
const createErrorBoundaryTestWrapper = () => {
  return () => {
    const [shouldError, setShouldError] = React.useState(false);
    
    const ProblematicComponent = ({ shouldError }: { shouldError: boolean }) => {
      if (shouldError) {
        throw createMockError('Component error for testing');
      }
      return <div data-testid="working-component">Component working fine</div>;
    };
    
    return renderErrorBoundaryTestWrapper(shouldError, setShouldError, ProblematicComponent);
  };
};

const createCascadingErrorComponent = () => {
  return () => {
    const [triggerCascade, setTriggerCascade] = React.useState(false);
    const [isolatedCount, setIsolatedCount] = React.useState(0);
    
    const ComponentA = () => triggerCascade ? (() => { throw new Error('Component A failed'); })() : 
      <div data-testid="component-a">Component A Working</div>;
    
    const ComponentB = () => triggerCascade ? (() => { throw new Error('Component B failed'); })() : 
      <div data-testid="component-b">Component B Working</div>;
    
    return renderCascadingErrorComponent(triggerCascade, setTriggerCascade, isolatedCount, ComponentA, ComponentB);
  };
};

const createErrorLoggingComponent = () => {
  return () => {
    const [errorLogs, setErrorLogs] = React.useState<any[]>([]);
    const [shouldError, setShouldError] = React.useState(false);
    
    const LoggingErrorBoundary = createLoggingErrorBoundary(setErrorLogs);
    const ErrorProneComponent = () => shouldError ? (() => { throw new Error('Logged error'); })() : 
      <div data-testid="error-prone">No errors</div>;
    
    return renderErrorLoggingComponent(errorLogs, setShouldError, LoggingErrorBoundary, ErrorProneComponent);
  };
};

const createGracefulDegradationComponent = () => {
  return () => {
    const [featureStatus, setFeatureStatus] = React.useState({
      primaryFeature: true,
      secondaryFeature: true,
      tertiaryFeature: true
    });
    
    const degradeFeature = (feature: string) => setFeatureStatus(prev => ({
      ...prev,
      [feature]: false
    }));
    
    return renderGracefulDegradationComponent(featureStatus, degradeFeature);
  };
};

const createFallbackUIComponent = () => {
  return () => {
    const [showFallback, setShowFallback] = React.useState(false);
    
    const FallbackBoundary = createFallbackBoundary();
    const MainComponent = () => showFallback ? (() => { throw new Error('Main component failed'); })() :
      <div data-testid="main-component">Main Component</div>;
    
    return renderFallbackUIComponent(setShowFallback, FallbackBoundary, MainComponent);
  };
};

const createRetryMechanismComponent = () => {
  return () => {
    const [retryState, setRetryState] = React.useState({
      attempts: 0,
      isRetrying: false,
      success: false,
      backoffDelay: 1000
    });
    
    const attemptOperation = () => attemptOperationWithRetry(setRetryState);
    
    return renderRetryMechanismComponent(retryState, attemptOperation);
  };
};

const createPartialRecoveryComponent = () => {
  return () => {
    const [systemState, setSystemState] = React.useState({
      coreSystem: 'healthy',
      featureA: 'healthy',
      featureB: 'healthy',
      featureC: 'healthy'
    });
    
    const simulateFailure = () => simulatePartialSystemFailure(setSystemState);
    const recoverSystem = () => recoverPartialSystem(setSystemState);
    
    return renderPartialRecoveryComponent(systemState, simulateFailure, recoverSystem);
  };
};

// Helper component factories (≤8 lines each)
const createLoggingErrorBoundary = (setErrorLogs: any) => {
  return class extends React.Component<{ children: React.ReactNode }, { hasError: boolean }> {
    constructor(props: any) {
      super(props);
      this.state = { hasError: false };
    }
    
    static getDerivedStateFromError() {
      return { hasError: true };
    }
    
    componentDidCatch(error: Error, errorInfo: any) {
      setErrorLogs((prev: any[]) => [...prev, { error: error.message, info: errorInfo, timestamp: Date.now() }]);
    }
    
    render() {
      return this.state.hasError ? <div data-testid="logged-error">Error logged</div> : this.props.children;
    }
  };
};

const createFallbackBoundary = () => {
  return class extends React.Component<{ children: React.ReactNode }, { hasError: boolean }> {
    constructor(props: any) {
      super(props);
      this.state = { hasError: false };
    }
    
    static getDerivedStateFromError() {
      return { hasError: true };
    }
    
    render() {
      return this.state.hasError ? 
        <div data-testid="fallback-ui">Fallback UI Active</div> : 
        this.props.children;
    }
  };
};

// Business logic functions (≤8 lines each)
const attemptOperationWithRetry = (setRetryState: any): void => {
  setRetryState((prev: any) => ({
    ...prev,
    attempts: prev.attempts + 1,
    isRetrying: true
  }));
  
  setTimeout(() => {
    setRetryState((prev: any) => ({
      ...prev,
      isRetrying: false,
      success: prev.attempts >= 3,
      backoffDelay: prev.backoffDelay * 2
    }));
  }, 500);
};

const simulatePartialSystemFailure = (setSystemState: any): void => {
  setSystemState({
    coreSystem: 'healthy',
    featureA: 'failed',
    featureB: 'degraded',
    featureC: 'healthy'
  });
};

const recoverPartialSystem = (setSystemState: any): void => {
  setSystemState((prev: any) => ({
    ...prev,
    featureA: prev.featureA === 'failed' ? 'recovering' : prev.featureA,
    featureB: prev.featureB === 'degraded' ? 'healthy' : prev.featureB
  }));
  
  setTimeout(() => {
    setSystemState((prev: any) => ({
      ...prev,
      featureA: 'healthy'
    }));
  }, 1000);
};

// UI rendering functions (≤8 lines each)
const renderErrorBoundaryUI = (retryCount: number, retry: () => void) => (
  <div data-testid="error-boundary">
    <div>Something went wrong!</div>
    <div data-testid="retry-count">Retries: {retryCount}</div>
    <button onClick={retry}>Try Again</button>
  </div>
);

const renderIsolatedErrorUI = (componentName: string, isolatedCount: number) => (
  <div data-testid="isolated-error">
    <div>Component {componentName} isolated</div>
    <div data-testid="isolated-count">{isolatedCount} components isolated</div>
  </div>
);

const renderErrorBoundaryTestWrapper = (
  shouldError: boolean, setShouldError: any, ProblematicComponent: any
) => (
  <div>
    <button onClick={() => setShouldError(true)}>Trigger Error</button>
    <button onClick={() => setShouldError(false)}>Fix Component</button>
    <ErrorBoundary>
      <ProblematicComponent shouldError={shouldError} />
    </ErrorBoundary>
  </div>
);

const renderCascadingErrorComponent = (
  triggerCascade: boolean, setTriggerCascade: any, isolatedCount: number, ComponentA: any, ComponentB: any
) => (
  <div>
    <button onClick={() => setTriggerCascade(true)}>Trigger Cascade</button>
    <div data-testid="isolated-count">{isolatedCount} isolated</div>
    <IsolatedErrorBoundary componentName="A">
      <ComponentA />
    </IsolatedErrorBoundary>
    <IsolatedErrorBoundary componentName="B">
      <ComponentB />
    </IsolatedErrorBoundary>
  </div>
);

const renderErrorLoggingComponent = (
  errorLogs: any[], setShouldError: any, LoggingErrorBoundary: any, ErrorProneComponent: any
) => (
  <div>
    <div data-testid="error-log-count">{errorLogs.length} errors logged</div>
    <button onClick={() => setShouldError(true)}>Trigger Logged Error</button>
    <LoggingErrorBoundary>
      <ErrorProneComponent />
    </LoggingErrorBoundary>
  </div>
);

const renderGracefulDegradationComponent = (featureStatus: any, degradeFeature: any) => (
  <div>
    <div data-testid="primary-feature">{featureStatus.primaryFeature ? 'Primary Active' : 'Primary Degraded'}</div>
    <div data-testid="secondary-feature">{featureStatus.secondaryFeature ? 'Secondary Active' : 'Secondary Degraded'}</div>
    <div data-testid="tertiary-feature">{featureStatus.tertiaryFeature ? 'Tertiary Active' : 'Tertiary Degraded'}</div>
    <button onClick={() => degradeFeature('primaryFeature')}>Degrade Primary</button>
    <button onClick={() => degradeFeature('secondaryFeature')}>Degrade Secondary</button>
  </div>
);

const renderFallbackUIComponent = (setShowFallback: any, FallbackBoundary: any, MainComponent: any) => (
  <div>
    <button onClick={() => setShowFallback(true)}>Trigger Fallback</button>
    <FallbackBoundary>
      <MainComponent />
    </FallbackBoundary>
  </div>
);

const renderRetryMechanismComponent = (retryState: any, attemptOperation: any) => (
  <div>
    <div data-testid="retry-attempts">{retryState.attempts} attempts</div>
    <div data-testid="retry-status">{retryState.isRetrying ? 'retrying' : 'idle'}</div>
    <div data-testid="operation-success">{retryState.success ? 'success' : 'pending'}</div>
    <div data-testid="backoff-delay">{retryState.backoffDelay}ms delay</div>
    <button onClick={attemptOperation} disabled={retryState.isRetrying}>Attempt Operation</button>
  </div>
);

const renderPartialRecoveryComponent = (systemState: any, simulateFailure: any, recoverSystem: any) => (
  <div>
    <div data-testid="core-system">{systemState.coreSystem}</div>
    <div data-testid="feature-a">{systemState.featureA}</div>
    <div data-testid="feature-b">{systemState.featureB}</div>
    <div data-testid="feature-c">{systemState.featureC}</div>
    <button onClick={simulateFailure}>Simulate Failure</button>
    <button onClick={recoverSystem}>Recover System</button>
  </div>
);

// Test verification functions (≤8 lines each)
const verifyInitialWorkingState = async (getByTestId: any): Promise<void> => {
  expect(getByTestId('working-component')).toHaveTextContent('Component working fine');
};

const triggerComponentError = async (getByText: any, getByTestId: any): Promise<void> => {
  fireEvent.click(getByText('Trigger Error'));
  
  await waitFor(() => {
    expect(getByTestId('error-boundary')).toHaveTextContent('Something went wrong!');
    expect(getByTestId('retry-count')).toHaveTextContent('Retries: 0');
  });
};

const testErrorRecovery = async (getByText: any, getByTestId: any): Promise<void> => {
  fireEvent.click(getByText('Try Again'));
  
  await waitFor(() => {
    expect(getByTestId('retry-count')).toHaveTextContent('Retries: 1');
  });
  
  fireEvent.click(getByText('Fix Component'));
  fireEvent.click(getByText('Try Again'));
  
  await waitFor(() => {
    expect(getByTestId('working-component')).toHaveTextContent('Component working fine');
  });
};

const testCascadingErrorIsolation = async (getByText: any, getByTestId: any): Promise<void> => {
  fireEvent.click(getByText('Trigger Cascade'));
  
  await waitFor(() => {
    expect(getByTestId('isolated-count')).toHaveTextContent('2 isolated');
  });
};

const testErrorLogging = async (getByText: any, getByTestId: any): Promise<void> => {
  fireEvent.click(getByText('Trigger Logged Error'));
  
  await waitFor(() => {
    expect(getByTestId('error-log-count')).toHaveTextContent('1 errors logged');
    expect(getByTestId('logged-error')).toHaveTextContent('Error logged');
  });
};

const testFeatureDegradation = async (getByText: any, getByTestId: any): Promise<void> => {
  fireEvent.click(getByText('Degrade Primary'));
  
  await waitFor(() => {
    expect(getByTestId('primary-feature')).toHaveTextContent('Primary Degraded');
    expect(getByTestId('secondary-feature')).toHaveTextContent('Secondary Active');
  });
  
  fireEvent.click(getByText('Degrade Secondary'));
  
  await waitFor(() => {
    expect(getByTestId('secondary-feature')).toHaveTextContent('Secondary Degraded');
  });
};

const testFallbackUI = async (getByText: any, getByTestId: any): Promise<void> => {
  fireEvent.click(getByText('Trigger Fallback'));
  
  await waitFor(() => {
    expect(getByTestId('fallback-ui')).toHaveTextContent('Fallback UI Active');
  });
};

const testRetryMechanism = async (getByText: any, getByTestId: any): Promise<void> => {
  fireEvent.click(getByText('Attempt Operation'));
  
  await waitFor(() => {
    expect(getByTestId('retry-attempts')).toHaveTextContent('1 attempts');
    expect(getByTestId('retry-status')).toHaveTextContent('retrying');
  });
  
  await waitFor(() => {
    expect(getByTestId('retry-status')).toHaveTextContent('idle');
  }, { timeout: TEST_TIMEOUTS.SHORT });
  
  // Test multiple retries until success
  fireEvent.click(getByText('Attempt Operation'));
  fireEvent.click(getByText('Attempt Operation'));
  
  await waitFor(() => {
    expect(getByTestId('operation-success')).toHaveTextContent('success');
  }, { timeout: TEST_TIMEOUTS.SHORT });
};

const testPartialRecovery = async (getByText: any, getByTestId: any): Promise<void> => {
  fireEvent.click(getByText('Simulate Failure'));
  
  await waitFor(() => {
    expect(getByTestId('core-system')).toHaveTextContent('healthy');
    expect(getByTestId('feature-a')).toHaveTextContent('failed');
    expect(getByTestId('feature-b')).toHaveTextContent('degraded');
  });
  
  fireEvent.click(getByText('Recover System'));
  
  await waitFor(() => {
    expect(getByTestId('feature-a')).toHaveTextContent('recovering');
    expect(getByTestId('feature-b')).toHaveTextContent('healthy');
  });
  
  await waitFor(() => {
    expect(getByTestId('feature-a')).toHaveTextContent('healthy');
  }, { timeout: TEST_TIMEOUTS.SHORT });
};