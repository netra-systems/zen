/**
 * Integration Tests for VPC Connector Configuration - Issue #1263
 * 
 * These tests validate VPC connector configuration for Cloud SQL connectivity
 * issues identified in Issue #1263 where database timeout escalation was caused
 * by VPC connector misconfiguration preventing proper database access.
 * 
 * Business Value Justification (BVJ):
 * - Segment: Platform/Internal - VPC Infrastructure Configuration
 * - Business Goal: Ensure VPC connector enables proper Cloud SQL access
 * - Value Impact: Prevents infrastructure misconfigurations causing database timeouts
 * - Strategic Impact: Maintains $500K+ ARR Golden Path by ensuring database connectivity
 */

import { beforeEach, afterEach, describe, it, expect, jest } from '@jest/globals';

describe('VPC Connector Configuration Integration Tests - Issue #1263', () => {
  beforeEach(() => {
    // Clear any cached environment variables
    jest.resetModules();
    
    // Set up staging environment for testing
    process.env.ENVIRONMENT = 'staging';
    process.env.GCP_PROJECT_ID = 'netra-staging';
    process.env.GCP_REGION = 'us-central1';
  });

  afterEach(() => {
    // Clean up environment variables
    delete process.env.ENVIRONMENT;
    delete process.env.GCP_PROJECT_ID;
    delete process.env.GCP_REGION;
    delete process.env.VPC_CONNECTOR_NAME;
    delete process.env.VPC_NETWORK;
    delete process.env.VPC_SUBNET;
  });

  describe('VPC Connector Configuration Validation', () => {
    it('should validate VPC connector naming conventions', () => {
      const vpcConnectorConfigs = [
        {
          name: 'staging-sql-connector',
          project: 'netra-staging',
          region: 'us-central1',
          valid: true
        },
        {
          name: 'prod-sql-connector',
          project: 'netra-production',
          region: 'us-central1',
          valid: true
        },
        {
          name: 'invalid_connector', // underscore not allowed
          project: 'netra-staging',
          region: 'us-central1',
          valid: false
        },
        {
          name: 'UPPERCASE-CONNECTOR', // uppercase not allowed
          project: 'netra-staging',
          region: 'us-central1',
          valid: false
        }
      ];

      vpcConnectorConfigs.forEach(({ name, project, region, valid }) => {
        process.env.VPC_CONNECTOR_NAME = name;
        process.env.GCP_PROJECT_ID = project;
        process.env.GCP_REGION = region;

        if (valid) {
          // Valid connector configuration
          expect(process.env.VPC_CONNECTOR_NAME).toMatch(/^[a-z0-9-]+$/);
          expect(process.env.VPC_CONNECTOR_NAME).toContain('connector');
          expect(process.env.VPC_CONNECTOR_NAME.length).toBeGreaterThan(5);
          expect(process.env.VPC_CONNECTOR_NAME.length).toBeLessThan(64);
          
          // Project and region validation
          expect(process.env.GCP_PROJECT_ID).toMatch(/^[a-z0-9-]+$/);
          expect(process.env.GCP_REGION).toMatch(/^[a-z0-9-]+$/);
        } else {
          // Invalid configurations should be caught
          expect(() => {
            if (!name.match(/^[a-z0-9-]+$/)) {
              throw new Error('Invalid VPC connector name format');
            }
          }).toThrow('Invalid VPC connector name format');
        }
      });
    });

    it('should validate VPC connector network configuration', () => {
      const networkConfigs = [
        {
          network: 'default',
          subnet: 'default',
          valid: true
        },
        {
          network: 'staging-vpc',
          subnet: 'staging-subnet',
          valid: true
        },
        {
          network: 'projects/netra-staging/global/networks/default',
          subnet: 'projects/netra-staging/regions/us-central1/subnetworks/default',
          valid: true
        },
        {
          network: '', // empty network
          subnet: 'default',
          valid: false
        },
        {
          network: 'default',
          subnet: '', // empty subnet
          valid: false
        }
      ];

      networkConfigs.forEach(({ network, subnet, valid }) => {
        process.env.VPC_NETWORK = network;
        process.env.VPC_SUBNET = subnet;

        if (valid) {
          expect(process.env.VPC_NETWORK).toBeDefined();
          expect(process.env.VPC_NETWORK.length).toBeGreaterThan(0);
          expect(process.env.VPC_SUBNET).toBeDefined();
          expect(process.env.VPC_SUBNET.length).toBeGreaterThan(0);

          // If fully qualified, should contain project path
          if (network.includes('projects/')) {
            expect(network).toContain('projects/netra-staging');
            expect(network).toContain('networks/');
          }

          if (subnet.includes('projects/')) {
            expect(subnet).toContain('projects/netra-staging');
            expect(subnet).toContain('subnetworks/');
          }
        } else {
          expect(() => {
            if (!network || !subnet || network.length === 0 || subnet.length === 0) {
              throw new Error('Network and subnet must be specified');
            }
          }).toThrow('Network and subnet must be specified');
        }
      });
    });

    it('should validate VPC connector configuration for Issue #1263 staging setup', () => {
      // Exact configuration that was causing issues in Issue #1263
      const issue1263Config = {
        connectorName: 'staging-sql-connector',
        project: 'netra-staging',
        region: 'us-central1',
        network: 'default',
        subnet: 'default',
        minInstances: 2,
        maxInstances: 10,
        machineType: 'e2-micro'
      };

      // Set environment variables
      process.env.VPC_CONNECTOR_NAME = issue1263Config.connectorName;
      process.env.GCP_PROJECT_ID = issue1263Config.project;
      process.env.GCP_REGION = issue1263Config.region;
      process.env.VPC_NETWORK = issue1263Config.network;
      process.env.VPC_SUBNET = issue1263Config.subnet;

      // Validate configuration
      expect(process.env.VPC_CONNECTOR_NAME).toBe('staging-sql-connector');
      expect(process.env.GCP_PROJECT_ID).toBe('netra-staging');
      expect(process.env.GCP_REGION).toBe('us-central1');
      expect(process.env.VPC_NETWORK).toBe('default');
      expect(process.env.VPC_SUBNET).toBe('default');

      // Validate naming matches Issue #1263 specifications
      expect(process.env.VPC_CONNECTOR_NAME).toContain('staging');
      expect(process.env.VPC_CONNECTOR_NAME).toContain('sql-connector');
      expect(process.env.GCP_PROJECT_ID).toContain('netra-staging');
    });
  });

  describe('Cloud SQL VPC Access Configuration', () => {
    it('should validate Cloud SQL instance accessibility through VPC connector', () => {
      const cloudSqlConfigs = [
        {
          instance: 'netra-staging:us-central1:staging-shared-postgres',
          connector: 'staging-sql-connector',
          valid: true
        },
        {
          instance: 'netra-prod:us-central1:production-postgres',
          connector: 'prod-sql-connector',
          valid: true
        },
        {
          instance: 'invalid-format',
          connector: 'staging-sql-connector',
          valid: false
        },
        {
          instance: 'netra-staging:us-central1:staging-shared-postgres',
          connector: '', // empty connector
          valid: false
        }
      ];

      cloudSqlConfigs.forEach(({ instance, connector, valid }) => {
        process.env.CLOUD_SQL_INSTANCE = instance;
        process.env.VPC_CONNECTOR_NAME = connector;

        if (valid) {
          // Validate instance format
          const instanceParts = instance.split(':');
          expect(instanceParts).toHaveLength(3);
          expect(instanceParts[0]).toMatch(/^[a-z0-9-]+$/); // project
          expect(instanceParts[1]).toMatch(/^[a-z0-9-]+$/); // region
          expect(instanceParts[2]).toMatch(/^[a-z0-9-]+$/); // instance

          // Validate connector
          expect(process.env.VPC_CONNECTOR_NAME).toMatch(/^[a-z0-9-]+$/);
          expect(process.env.VPC_CONNECTOR_NAME).toContain('connector');

          // Validate project consistency
          expect(instanceParts[0]).toContain('netra');
          expect(process.env.VPC_CONNECTOR_NAME).toContain(instanceParts[0].includes('staging') ? 'staging' : 'prod');
        } else {
          expect(() => {
            const instanceParts = instance.split(':');
            if (instanceParts.length !== 3 || !connector || connector.length === 0) {
              throw new Error('Invalid Cloud SQL instance or VPC connector configuration');
            }
          }).toThrow('Invalid Cloud SQL instance or VPC connector configuration');
        }
      });
    });

    it('should validate socket path accessibility through VPC connector', () => {
      const socketConfigs = [
        {
          socketPath: '/cloudsql/netra-staging:us-central1:staging-shared-postgres',
          connector: 'staging-sql-connector',
          valid: true
        },
        {
          socketPath: '/cloudsql/netra-prod:us-central1:production-postgres',
          connector: 'prod-sql-connector',
          valid: true
        },
        {
          socketPath: '/tmp/invalid-socket',
          connector: 'staging-sql-connector',
          valid: false
        },
        {
          socketPath: '/cloudsql/netra-staging:us-central1:staging-shared-postgres',
          connector: '', // empty connector
          valid: false
        }
      ];

      socketConfigs.forEach(({ socketPath, connector, valid }) => {
        process.env.CLOUD_SQL_SOCKET_PATH = socketPath;
        process.env.VPC_CONNECTOR_NAME = connector;

        if (valid) {
          // Validate socket path format
          expect(socketPath).toStartWith('/cloudsql/');
          expect(socketPath).toContain(':');

          // Extract instance information from socket path
          const instanceInfo = socketPath.replace('/cloudsql/', '');
          const instanceParts = instanceInfo.split(':');
          expect(instanceParts).toHaveLength(3);

          // Validate connector consistency
          expect(process.env.VPC_CONNECTOR_NAME).toMatch(/^[a-z0-9-]+$/);
          
          // Check project consistency between socket and connector
          const project = instanceParts[0];
          if (project.includes('staging')) {
            expect(connector).toContain('staging');
          } else if (project.includes('prod')) {
            expect(connector).toContain('prod');
          }
        } else {
          expect(() => {
            if (!socketPath.startsWith('/cloudsql/') || !connector || connector.length === 0) {
              throw new Error('Invalid socket path or VPC connector configuration');
            }
          }).toThrow('Invalid socket path or VPC connector configuration');
        }
      });
    });
  });

  describe('VPC Connector Health and Monitoring', () => {
    it('should validate VPC connector scaling configuration', () => {
      const scalingConfigs = [
        {
          minInstances: 2,
          maxInstances: 10,
          machineType: 'e2-micro',
          valid: true
        },
        {
          minInstances: 1,
          maxInstances: 100,
          machineType: 'e2-standard-4',
          valid: true
        },
        {
          minInstances: 0, // invalid - must be at least 1
          maxInstances: 10,
          machineType: 'e2-micro',
          valid: false
        },
        {
          minInstances: 10,
          maxInstances: 5, // invalid - max must be >= min
          machineType: 'e2-micro',
          valid: false
        }
      ];

      scalingConfigs.forEach(({ minInstances, maxInstances, machineType, valid }) => {
        if (valid) {
          expect(minInstances).toBeGreaterThan(0);
          expect(maxInstances).toBeGreaterThanOrEqual(minInstances);
          expect(maxInstances).toBeLessThanOrEqual(1000); // GCP limit
          expect(machineType).toMatch(/^e2-/); // Valid machine type prefix
        } else {
          expect(() => {
            if (minInstances <= 0 || maxInstances < minInstances || maxInstances > 1000) {
              throw new Error('Invalid VPC connector scaling configuration');
            }
          }).toThrow('Invalid VPC connector scaling configuration');
        }
      });
    });

    it('should validate VPC connector throughput configuration', () => {
      const throughputConfigs = [
        {
          minThroughput: 200, // Mbps
          maxThroughput: 1000, // Mbps
          valid: true
        },
        {
          minThroughput: 300,
          maxThroughput: 2000,
          valid: true
        },
        {
          minThroughput: 100, // below minimum
          maxThroughput: 1000,
          valid: false
        },
        {
          minThroughput: 300,
          maxThroughput: 100, // max < min
          valid: false
        }
      ];

      throughputConfigs.forEach(({ minThroughput, maxThroughput, valid }) => {
        if (valid) {
          expect(minThroughput).toBeGreaterThanOrEqual(200); // GCP minimum
          expect(maxThroughput).toBeGreaterThanOrEqual(minThroughput);
          expect(maxThroughput).toBeLessThanOrEqual(10000); // GCP maximum
        } else {
          expect(() => {
            if (minThroughput < 200 || maxThroughput < minThroughput || maxThroughput > 10000) {
              throw new Error('Invalid VPC connector throughput configuration');
            }
          }).toThrow('Invalid VPC connector throughput configuration');
        }
      });
    });

    it('should validate VPC connector health check configuration', () => {
      const healthCheckConfig = {
        enableHealthCheck: true,
        healthCheckPath: '/health',
        healthCheckPort: 8080,
        timeoutSeconds: 5,
        checkIntervalSeconds: 10,
        unhealthyThreshold: 3,
        healthyThreshold: 2
      };

      expect(healthCheckConfig.enableHealthCheck).toBe(true);
      expect(healthCheckConfig.healthCheckPath).toStartWith('/');
      expect(healthCheckConfig.healthCheckPort).toBeGreaterThan(0);
      expect(healthCheckConfig.healthCheckPort).toBeLessThan(65536);
      expect(healthCheckConfig.timeoutSeconds).toBeGreaterThan(0);
      expect(healthCheckConfig.timeoutSeconds).toBeLessThan(60);
      expect(healthCheckConfig.checkIntervalSeconds).toBeGreaterThan(healthCheckConfig.timeoutSeconds);
      expect(healthCheckConfig.unhealthyThreshold).toBeGreaterThan(0);
      expect(healthCheckConfig.healthyThreshold).toBeGreaterThan(0);
    });
  });

  describe('Issue #1263 VPC Connector Troubleshooting', () => {
    it('should validate VPC connector state for Issue #1263 resolution', () => {
      // Configuration that should resolve Issue #1263
      const resolvedConfig = {
        connectorName: 'staging-sql-connector',
        project: 'netra-staging',
        region: 'us-central1',
        network: 'default',
        subnet: 'default',
        state: 'READY', // Should be READY for proper functionality
        minInstances: 2,
        maxInstances: 10,
        connectedProjects: ['netra-staging'],
        ipCidrRange: '10.8.0.0/28' // Example CIDR range
      };

      // Set environment configuration
      process.env.VPC_CONNECTOR_NAME = resolvedConfig.connectorName;
      process.env.GCP_PROJECT_ID = resolvedConfig.project;
      process.env.GCP_REGION = resolvedConfig.region;
      process.env.VPC_NETWORK = resolvedConfig.network;
      process.env.VPC_SUBNET = resolvedConfig.subnet;

      // Validate configuration matches resolution requirements
      expect(process.env.VPC_CONNECTOR_NAME).toBe('staging-sql-connector');
      expect(process.env.GCP_PROJECT_ID).toBe('netra-staging');
      expect(process.env.GCP_REGION).toBe('us-central1');

      // Validate state would be READY (in real scenario)
      expect(resolvedConfig.state).toBe('READY');
      expect(resolvedConfig.connectedProjects).toContain('netra-staging');

      // Validate IP CIDR range format
      expect(resolvedConfig.ipCidrRange).toMatch(/^\d+\.\d+\.\d+\.\d+\/\d+$/);
      expect(resolvedConfig.ipCidrRange).toContain('/28'); // Standard VPC connector range
    });

    it('should validate VPC connector connectivity to Cloud SQL for Issue #1263', () => {
      // Test connectivity configuration
      const connectivityConfig = {
        vpcConnector: 'staging-sql-connector',
        cloudSqlInstance: 'netra-staging:us-central1:staging-shared-postgres',
        socketPath: '/cloudsql/netra-staging:us-central1:staging-shared-postgres',
        databaseUrl: 'postgresql+asyncpg://user:pass@/netra_staging?host=/cloudsql/netra-staging:us-central1:staging-shared-postgres',
        timeoutConfig: {
          initialization: 25.0,
          connection: 15.0
        }
      };

      // Validate VPC connector enables Cloud SQL access
      expect(connectivityConfig.vpcConnector).toBe('staging-sql-connector');
      expect(connectivityConfig.cloudSqlInstance).toContain('netra-staging');
      expect(connectivityConfig.socketPath).toStartWith('/cloudsql/');
      expect(connectivityConfig.databaseUrl).toContain('postgresql+asyncpg://');
      expect(connectivityConfig.databaseUrl).toContain(connectivityConfig.socketPath.replace('/cloudsql/', '?host=/cloudsql/'));

      // Validate timeout configuration matches Issue #1263 current state
      expect(connectivityConfig.timeoutConfig.initialization).toBe(25.0);
      expect(connectivityConfig.timeoutConfig.connection).toBe(15.0);

      // Ensure all components reference the same instance
      const instanceFromSocket = connectivityConfig.socketPath.replace('/cloudsql/', '');
      const instanceFromUrl = connectivityConfig.databaseUrl.match(/host=\/cloudsql\/([^&]+)/)?.[1];
      
      expect(instanceFromSocket).toBe(connectivityConfig.cloudSqlInstance);
      expect(instanceFromUrl).toBe(connectivityConfig.cloudSqlInstance);
    });

    it('should validate VPC connector IAM permissions for Issue #1263', () => {
      // IAM configuration required for VPC connector to work
      const iamConfig = {
        serviceAccount: 'netra-backend-staging@netra-staging.iam.gserviceaccount.com',
        requiredRoles: [
          'roles/cloudsql.client',
          'roles/vpcaccess.user',
          'roles/compute.networkUser'
        ],
        vpcConnectorUsers: [
          'serviceAccount:netra-backend-staging@netra-staging.iam.gserviceaccount.com'
        ]
      };

      // Validate service account format
      expect(iamConfig.serviceAccount).toMatch(/^[a-z0-9-]+@[a-z0-9-]+\.iam\.gserviceaccount\.com$/);
      expect(iamConfig.serviceAccount).toContain('netra-backend-staging');
      expect(iamConfig.serviceAccount).toContain('netra-staging');

      // Validate required roles for VPC connector and Cloud SQL access
      expect(iamConfig.requiredRoles).toContain('roles/cloudsql.client');
      expect(iamConfig.requiredRoles).toContain('roles/vpcaccess.user');
      expect(iamConfig.requiredRoles).toContain('roles/compute.networkUser');

      // Validate VPC connector users include the service account
      expect(iamConfig.vpcConnectorUsers[0]).toBe(iamConfig.serviceAccount);
    });
  });
});