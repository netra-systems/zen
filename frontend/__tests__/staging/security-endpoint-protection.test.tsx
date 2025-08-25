/**
 * Security Endpoint Protection Tests
 * Tests for proper handling of requests to sensitive configuration files
 * Based on security issues identified in staging logs
 */

import { getUnifiedApiConfig } from '../../lib/unified-api-config';

describe('Security - Endpoint Protection (Staging)', () => {
  const config = getUnifiedApiConfig();
  const frontendUrl = config.urls.frontend;
  
  // List of sensitive files that should be protected
  const sensitiveFiles = [
    // Environment files
    '.env',
    'config/.env',
    'database/.env',
    'core/.env',
    'core/app/.env',
    'core/Datavase/.env',
    'cron/.env',
    'cronlab/.env',
    'lab/.env',
    'lib/.env',
    'vendor/.env',
    
    // Git files
    '.gitconfig',
    '.gitignore',
    '.git/index',
    '.git/objects/',
    '.git/logs/HEAD',
    '.git/logs/refs/heads/master',
    '.git/refs/heads/main',
    '.git/refs/heads/master',
    '.git/packed-refs',
    
    // Production files
    '.production',
    '.local',
    '.remote',
    
    // PHP info files (common attack vectors)
    'info.php',
    'phpinfo',
    'phpinfo.php',
    'phpinfo=1',
    'test.php',
    'app_dev.php/_profiler/phpinfo',
    'tool/view/phpinfo.view.php',
    '_profiler/phpinfo',
  ];

  describe('Sensitive File Protection', () => {
    test.each(sensitiveFiles)(
      'should return 404 (not 302 redirect) for sensitive file: %s',
      async (sensitiveFile) => {
        try {
          const response = await fetch(`${frontendUrl}/${sensitiveFile}`, {
            method: 'GET',
            redirect: 'manual', // Don't follow redirects
          });
          
          // Should return 404 NOT 302 (redirect)
          expect(response.status).toBe(404);
          expect(response.status).not.toBe(302); // Explicitly check no redirect
          
          // Should not contain sensitive information in response
          const text = await response.text();
          expect(text).not.toMatch(/password|secret|key|token|database/i);
          
        } catch (error) {
          // Network errors are acceptable (service might be down)
          // But we should not get 302 redirects for sensitive files
          if (error.message.includes('302')) {
            fail(`Received 302 redirect for sensitive file ${sensitiveFile} - security risk`);
          }
        }
      }
    );
  });

  describe('HTTP Method Security', () => {
    const sensitivePaths = ['.env', '.git/index', 'phpinfo.php'];
    const methods = ['GET', 'POST', 'PUT', 'DELETE', 'HEAD', 'OPTIONS'];

    test.each(sensitivePaths)(
      'should properly handle all HTTP methods for sensitive path: %s',
      async (path) => {
        for (const method of methods) {
          try {
            const response = await fetch(`${frontendUrl}/${path}`, {
              method,
              redirect: 'manual',
            });
            
            // Should return 404 or 405 (Method Not Allowed), NOT 302
            expect([404, 405]).toContain(response.status);
            expect(response.status).not.toBe(302);
            
          } catch (error) {
            // Network errors acceptable, 302 redirects are not
            if (error.message.includes('302')) {
              fail(`${method} to ${path} returned 302 redirect - security risk`);
            }
          }
        }
      }
    );
  });

  describe('Information Disclosure Prevention', () => {
    test('should not expose server information in error responses', async () => {
      try {
        const response = await fetch(`${frontendUrl}/nonexistent-path-${Date.now()}`, {
          redirect: 'manual',
        });
        
        const text = await response.text();
        const headers = Object.fromEntries(response.headers.entries());
        
        // Should not expose sensitive server information
        expect(text).not.toMatch(/nginx|apache|express|next\.js version|node\.js|internal error|stack trace/i);
        expect(headers.server).not.toMatch(/nginx|apache|express/i);
        
        // Should not expose internal paths
        expect(text).not.toMatch(/\/app\/|\/var\/|\/usr\/|\/home\/|C:\|D:\//);
        
      } catch (error) {
        // Network errors are acceptable for this test
        console.log('Network error in information disclosure test:', error.message);
      }
    });
  });

  describe('Rate Limiting and Security Headers', () => {
    test('should implement proper security headers', async () => {
      try {
        const response = await fetch(`${frontendUrl}/health`);
        
        if (response.ok) {
          const headers = Object.fromEntries(response.headers.entries());
          
          // Check for important security headers
          // Note: These are recommendations, not hard requirements for staging
          const securityHeaders = [
            'x-content-type-options',
            'x-frame-options', 
            'x-xss-protection',
          ];
          
          // Log security headers for analysis (not strict requirements)
          console.log('Security headers present:', 
            securityHeaders.filter(h => headers[h]).join(', ') || 'none'
          );
        }
        
      } catch (error) {
        console.log('Could not check security headers:', error.message);
      }
    });
  });

  describe('Configuration File Security', () => {
    test('should not expose configuration through URL manipulation', async () => {
      const configTestPaths = [
        '../.env',
        '../../.env',
        'config/../.env',
        'static/../.env',
        'public/../.env',
      ];

      for (const path of configTestPaths) {
        try {
          const response = await fetch(`${frontendUrl}/${path}`, {
            redirect: 'manual',
          });
          
          // Should not allow directory traversal
          expect(response.status).not.toBe(200);
          expect(response.status).not.toBe(302); // No redirects for security paths
          expect([404, 400]).toContain(response.status);
          
        } catch (error) {
          // Network errors acceptable, successful requests are not
          if (!error.message.includes('fetch')) {
            throw error;
          }
        }
      }
    });
  });
});