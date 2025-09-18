'use client';

import React, { useState, useEffect, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Shield,
  Activity,
  Users,
  AlertTriangle,
  CheckCircle,
  XCircle,
  Clock,
  Zap,
  Settings,
  RefreshCw,
  TrendingUp,
  AlertCircle,
  Wifi,
  WifiOff
} from 'lucide-react';

interface AuthenticationMetrics {
  total_attempts: number;
  successful_authentications: number;
  failed_authentications: number;
  authentication_timeouts: number;
  circuit_breaker_trips: number;
  average_response_time_ms: number;
  success_rate_percent: number;
  failure_rate_percent: number;
  last_success_timestamp: string | null;
  last_failure_timestamp: string | null;
  uptime_seconds: number;
}

interface AuthenticationHealthStatus {
  status: 'healthy' | 'degraded' | 'critical' | 'unknown';
  metrics: AuthenticationMetrics;
  active_connections: number;
  unhealthy_connections: number;
  monitoring_enabled: boolean;
  last_health_check: string | null;
  errors: string[];
  warnings: string[];
  timestamp: string;
}

interface AuthenticationStats {
  service_info: {
    name: string;
    ssot_compliant: boolean;
    monitoring_enabled: boolean;
    integration_with_connection_monitor: boolean;
  };
  metrics: AuthenticationMetrics;
  circuit_breaker: {
    enabled: boolean;
    is_open: boolean;
    threshold_percent: number;
    timeout_seconds: number;
    last_trip: string | null;
  };
  health_status: {
    last_check: string;
    check_interval_seconds: number;
    errors_count: number;
    warnings_count: number;
  };
  response_time_analysis: {
    samples_count: number;
    average_ms: number;
    min_ms: number;
    max_ms: number;
  };
  connection_monitor?: any;
}

const WebSocketAuthMonitor: React.FC = () => {
  const [healthData, setHealthData] = useState<AuthenticationHealthStatus | null>(null);
  const [metricsData, setMetricsData] = useState<AuthenticationStats | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [autoRefresh, setAutoRefresh] = useState(true);
  const [testUserId, setTestUserId] = useState('');
  const [testResult, setTestResult] = useState<any>(null);

  const fetchAuthHealth = useCallback(async () => {
    try {
      const response = await fetch('/api/admin/websocket-auth/health', {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`,
          'Content-Type': 'application/json',
        },
      });

      if (!response.ok) {
        throw new Error(`Health check failed: ${response.status}`);
      }

      const data = await response.json();
      setHealthData(data);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch health data');
    }
  }, []);

  const fetchAuthMetrics = useCallback(async () => {
    try {
      const response = await fetch('/api/admin/websocket-auth/metrics', {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`,
          'Content-Type': 'application/json',
        },
      });

      if (!response.ok) {
        throw new Error(`Metrics fetch failed: ${response.status}`);
      }

      const data = await response.json();
      setMetricsData(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch metrics data');
    }
  }, []);

  const fetchData = useCallback(async () => {
    setIsLoading(true);
    await Promise.all([fetchAuthHealth(), fetchAuthMetrics()]);
    setIsLoading(false);
  }, [fetchAuthHealth, fetchAuthMetrics]);

  const testConnection = async () => {
    if (!testUserId.trim()) {
      alert('Please enter a user ID to test');
      return;
    }

    try {
      const response = await fetch('/api/admin/websocket-auth/test-connection', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ user_id: testUserId }),
      });

      const data = await response.json();
      setTestResult(data);
    } catch (err) {
      setTestResult({
        error: err instanceof Error ? err.message : 'Test connection failed',
        connection_healthy: false
      });
    }
  };

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  useEffect(() => {
    if (!autoRefresh) return;

    const interval = setInterval(() => {
      fetchData();
    }, 10000); // Refresh every 10 seconds

    return () => clearInterval(interval);
  }, [autoRefresh, fetchData]);

  if (isLoading && !healthData) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="flex items-center space-x-2">
          <RefreshCw className="w-5 h-5 animate-spin" />
          <span>Loading WebSocket authentication monitoring...</span>
        </div>
      </div>
    );
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'healthy': return 'text-green-600 bg-green-100';
      case 'degraded': return 'text-yellow-600 bg-yellow-100';
      case 'critical': return 'text-red-600 bg-red-100';
      default: return 'text-gray-600 bg-gray-100';
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'healthy': return <CheckCircle className="w-5 h-5" />;
      case 'degraded': return <AlertTriangle className="w-5 h-5" />;
      case 'critical': return <XCircle className="w-5 h-5" />;
      default: return <AlertCircle className="w-5 h-5" />;
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-4">
          <div className="w-10 h-10 bg-gradient-to-br from-blue-500 to-blue-600 rounded-full flex items-center justify-center">
            <Shield className="w-5 h-5 text-white" />
          </div>
          <div>
            <h2 className="text-2xl font-bold text-gray-900">WebSocket Authentication Monitor</h2>
            <p className="text-gray-600">Real-time authentication monitoring and diagnostics</p>
          </div>
        </div>
        <div className="flex items-center space-x-4">
          <button
            onClick={() => setAutoRefresh(!autoRefresh)}
            className={`flex items-center space-x-2 px-3 py-2 rounded-lg text-sm font-medium ${
              autoRefresh
                ? 'bg-green-100 text-green-800 hover:bg-green-200'
                : 'bg-gray-100 text-gray-800 hover:bg-gray-200'
            }`}
          >
            <Activity className={`w-4 h-4 ${autoRefresh ? 'animate-pulse' : ''}`} />
            <span>Auto-refresh {autoRefresh ? 'ON' : 'OFF'}</span>
          </button>
          <button
            onClick={fetchData}
            disabled={isLoading}
            className="flex items-center space-x-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
          >
            <RefreshCw className={`w-4 h-4 ${isLoading ? 'animate-spin' : ''}`} />
            <span>Refresh</span>
          </button>
        </div>
      </div>

      {/* Error Display */}
      {error && (
        <motion.div
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          className="bg-red-50 border border-red-200 rounded-lg p-4"
        >
          <div className="flex items-center space-x-2">
            <XCircle className="w-5 h-5 text-red-500" />
            <span className="text-red-800 font-medium">Error</span>
          </div>
          <p className="text-red-700 mt-1">{error}</p>
        </motion.div>
      )}

      {/* Health Status Overview */}
      {healthData && (
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          className="bg-white rounded-lg shadow-sm border border-gray-100 p-6"
        >
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold text-gray-900">Overall Health Status</h3>
            <div className={`flex items-center space-x-2 px-3 py-1 rounded-full text-sm font-medium ${getStatusColor(healthData.status)}`}>
              {getStatusIcon(healthData.status)}
              <span className="capitalize">{healthData.status}</span>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
            <div className="text-center">
              <div className="w-12 h-12 bg-blue-100 rounded-full flex items-center justify-center mx-auto mb-2">
                <Users className="w-6 h-6 text-blue-600" />
              </div>
              <div className="text-2xl font-bold text-gray-900">{healthData.active_connections}</div>
              <div className="text-sm text-gray-600">Active Connections</div>
            </div>

            <div className="text-center">
              <div className="w-12 h-12 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-2">
                <TrendingUp className="w-6 h-6 text-green-600" />
              </div>
              <div className="text-2xl font-bold text-gray-900">{healthData.metrics.success_rate_percent.toFixed(1)}%</div>
              <div className="text-sm text-gray-600">Success Rate</div>
            </div>

            <div className="text-center">
              <div className="w-12 h-12 bg-yellow-100 rounded-full flex items-center justify-center mx-auto mb-2">
                <Clock className="w-6 h-6 text-yellow-600" />
              </div>
              <div className="text-2xl font-bold text-gray-900">{healthData.metrics.average_response_time_ms.toFixed(0)}ms</div>
              <div className="text-sm text-gray-600">Avg Response Time</div>
            </div>

            <div className="text-center">
              <div className="w-12 h-12 bg-red-100 rounded-full flex items-center justify-center mx-auto mb-2">
                <AlertTriangle className="w-6 h-6 text-red-600" />
              </div>
              <div className="text-2xl font-bold text-gray-900">{healthData.unhealthy_connections}</div>
              <div className="text-sm text-gray-600">Unhealthy Connections</div>
            </div>
          </div>

          {/* Errors and Warnings */}
          {(healthData.errors.length > 0 || healthData.warnings.length > 0) && (
            <div className="mt-6 space-y-2">
              {healthData.errors.map((error, index) => (
                <div key={`error-${index}`} className="flex items-center space-x-2 text-red-700 bg-red-50 p-2 rounded">
                  <XCircle className="w-4 h-4" />
                  <span className="text-sm">{error}</span>
                </div>
              ))}
              {healthData.warnings.map((warning, index) => (
                <div key={`warning-${index}`} className="flex items-center space-x-2 text-yellow-700 bg-yellow-50 p-2 rounded">
                  <AlertTriangle className="w-4 h-4" />
                  <span className="text-sm">{warning}</span>
                </div>
              ))}
            </div>
          )}
        </motion.div>
      )}

      {/* Detailed Metrics */}
      {metricsData && (
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="bg-white rounded-lg shadow-sm border border-gray-100 p-6"
        >
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Authentication Metrics</h3>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {/* Authentication Stats */}
            <div className="space-y-4">
              <h4 className="font-medium text-gray-900">Authentication Statistics</h4>
              <div className="space-y-2 text-sm">
                <div className="flex justify-between">
                  <span className="text-gray-600">Total Attempts:</span>
                  <span className="font-medium">{metricsData.metrics.total_attempts}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">Successful:</span>
                  <span className="font-medium text-green-600">{metricsData.metrics.successful_authentications}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">Failed:</span>
                  <span className="font-medium text-red-600">{metricsData.metrics.failed_authentications}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">Timeouts:</span>
                  <span className="font-medium text-yellow-600">{metricsData.metrics.authentication_timeouts}</span>
                </div>
              </div>
            </div>

            {/* Circuit Breaker */}
            <div className="space-y-4">
              <h4 className="font-medium text-gray-900">Circuit Breaker</h4>
              <div className="space-y-2 text-sm">
                <div className="flex justify-between">
                  <span className="text-gray-600">Status:</span>
                  <span className={`font-medium ${metricsData.circuit_breaker.is_open ? 'text-red-600' : 'text-green-600'}`}>
                    {metricsData.circuit_breaker.is_open ? 'Open' : 'Closed'}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">Threshold:</span>
                  <span className="font-medium">{metricsData.circuit_breaker.threshold_percent}%</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">Trips:</span>
                  <span className="font-medium">{metricsData.metrics.circuit_breaker_trips}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">Timeout:</span>
                  <span className="font-medium">{metricsData.circuit_breaker.timeout_seconds}s</span>
                </div>
              </div>
            </div>

            {/* Response Times */}
            <div className="space-y-4">
              <h4 className="font-medium text-gray-900">Response Times</h4>
              <div className="space-y-2 text-sm">
                <div className="flex justify-between">
                  <span className="text-gray-600">Average:</span>
                  <span className="font-medium">{metricsData.response_time_analysis.average_ms}ms</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">Min:</span>
                  <span className="font-medium">{metricsData.response_time_analysis.min_ms}ms</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">Max:</span>
                  <span className="font-medium">{metricsData.response_time_analysis.max_ms}ms</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">Samples:</span>
                  <span className="font-medium">{metricsData.response_time_analysis.samples_count}</span>
                </div>
              </div>
            </div>
          </div>
        </motion.div>
      )}

      {/* Connection Testing */}
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.2 }}
        className="bg-white rounded-lg shadow-sm border border-gray-100 p-6"
      >
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Connection Testing</h3>

        <div className="flex items-center space-x-4 mb-4">
          <input
            type="text"
            value={testUserId}
            onChange={(e) => setTestUserId(e.target.value)}
            placeholder="Enter user ID to test..."
            className="flex-1 px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          />
          <button
            onClick={testConnection}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 flex items-center space-x-2"
          >
            <Zap className="w-4 h-4" />
            <span>Test Connection</span>
          </button>
        </div>

        {testResult && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className={`p-4 rounded-lg ${testResult.connection_healthy ? 'bg-green-50 border border-green-200' : 'bg-red-50 border border-red-200'}`}
          >
            <div className="flex items-center space-x-2 mb-2">
              {testResult.connection_healthy ? (
                <Wifi className="w-5 h-5 text-green-600" />
              ) : (
                <WifiOff className="w-5 h-5 text-red-600" />
              )}
              <span className={`font-medium ${testResult.connection_healthy ? 'text-green-800' : 'text-red-800'}`}>
                Connection {testResult.connection_healthy ? 'Healthy' : 'Unhealthy'}
              </span>
            </div>
            {testResult.error && (
              <p className="text-red-700 text-sm">{testResult.error}</p>
            )}
            <p className="text-gray-600 text-sm mt-1">
              Tested at: {new Date(testResult.test_timestamp).toLocaleString()}
            </p>
          </motion.div>
        )}
      </motion.div>
    </div>
  );
};

export default WebSocketAuthMonitor;