/**
 * Platform Detection Utilities
 *
 * Issue #860: Windows WebSocket compatibility utilities
 * Strategic alignment with Issue #420 Docker bypass strategy
 *
 * Business Value Protection: Maintains $500K+ ARR by ensuring Windows developers
 * can connect to staging environment when local Docker/WebSocket setup fails
 */

import { logger } from '@/lib/logger';

/**
 * Comprehensive platform detection
 */
export interface PlatformInfo {
  platform: 'windows' | 'macos' | 'linux' | 'unknown';
  version?: string;
  architecture?: string;
  isSupported: boolean;
  recommendedEnvironment: 'development' | 'staging';
  compatibilityNotes: string[];
}

/**
 * Detect the current platform with comprehensive information
 */
export function detectPlatform(): PlatformInfo {
  const platform = getPlatformName();
  const version = getPlatformVersion();
  const architecture = getPlatformArchitecture();

  const info: PlatformInfo = {
    platform,
    version,
    architecture,
    isSupported: true,
    recommendedEnvironment: 'development',
    compatibilityNotes: []
  };

  // Windows-specific recommendations (Issue #860)
  if (platform === 'windows') {
    info.recommendedEnvironment = 'staging';
    info.compatibilityNotes.push(
      'Windows WebSocket connections work best with staging environment',
      'Local Docker setup may experience connection issues (WinError 1225)',
      'Automatic staging fallback enabled for optimal experience'
    );
  }

  // macOS recommendations
  if (platform === 'macos') {
    info.compatibilityNotes.push(
      'macOS supports full local development environment',
      'Docker Desktop recommended for complete local testing'
    );
  }

  // Linux recommendations
  if (platform === 'linux') {
    info.compatibilityNotes.push(
      'Linux supports full local development environment',
      'Native Docker support provides optimal performance'
    );
  }

  return info;
}

/**
 * Get platform name
 */
function getPlatformName(): 'windows' | 'macos' | 'linux' | 'unknown' {
  // Server-side detection (Node.js)
  if (typeof process !== 'undefined' && process.platform) {
    switch (process.platform) {
      case 'win32':
        return 'windows';
      case 'darwin':
        return 'macos';
      case 'linux':
        return 'linux';
      default:
        return 'unknown';
    }
  }

  // Client-side detection (Browser)
  if (typeof navigator !== 'undefined') {
    const userAgent = navigator.userAgent.toLowerCase();
    const platform = navigator.platform?.toLowerCase() || '';

    if (platform.includes('win') || /windows|win32|win64|wow32|wow64/i.test(userAgent)) {
      return 'windows';
    }
    if (platform.includes('mac') || /macintosh|mac os x/i.test(userAgent)) {
      return 'macos';
    }
    if (platform.includes('linux') || /linux/i.test(userAgent)) {
      return 'linux';
    }
  }

  return 'unknown';
}

/**
 * Get platform version (best effort)
 */
function getPlatformVersion(): string | undefined {
  // Server-side detection
  if (typeof process !== 'undefined' && process.platform === 'win32') {
    return process.env.OS || 'Windows';
  }

  // Client-side detection
  if (typeof navigator !== 'undefined') {
    const userAgent = navigator.userAgent;

    // Windows version detection
    const windowsMatch = userAgent.match(/Windows NT (\d+\.\d+)/);
    if (windowsMatch) {
      const version = windowsMatch[1];
      const versionMap: Record<string, string> = {
        '10.0': 'Windows 10/11',
        '6.3': 'Windows 8.1',
        '6.2': 'Windows 8',
        '6.1': 'Windows 7'
      };
      return versionMap[version] || `Windows NT ${version}`;
    }

    // macOS version detection
    const macMatch = userAgent.match(/Mac OS X (\d+[._]\d+[._]?\d*)/);
    if (macMatch) {
      return `macOS ${macMatch[1].replace(/_/g, '.')}`;
    }

    // Linux detection (limited info available)
    if (/linux/i.test(userAgent)) {
      return 'Linux';
    }
  }

  return undefined;
}

/**
 * Get platform architecture (best effort)
 */
function getPlatformArchitecture(): string | undefined {
  // Server-side detection
  if (typeof process !== 'undefined' && process.arch) {
    return process.arch;
  }

  // Client-side detection (limited)
  if (typeof navigator !== 'undefined') {
    const userAgent = navigator.userAgent;

    if (/x64|x86_64|amd64/i.test(userAgent)) {
      return 'x64';
    }
    if (/arm64/i.test(userAgent)) {
      return 'arm64';
    }
    if (/x86|i386|i686/i.test(userAgent)) {
      return 'x86';
    }
  }

  return undefined;
}

/**
 * Check if current platform is Windows
 */
export function isWindows(): boolean {
  return detectPlatform().platform === 'windows';
}

/**
 * Check if current platform is macOS
 */
export function isMacOS(): boolean {
  return detectPlatform().platform === 'macos';
}

/**
 * Check if current platform is Linux
 */
export function isLinux(): boolean {
  return detectPlatform().platform === 'linux';
}

/**
 * Get development environment recommendation based on platform
 */
export function getRecommendedEnvironment(): 'development' | 'staging' {
  const platform = detectPlatform();
  return platform.recommendedEnvironment;
}

/**
 * Get platform-specific compatibility notes
 */
export function getCompatibilityNotes(): string[] {
  const platform = detectPlatform();
  return platform.compatibilityNotes;
}

/**
 * Check if platform supports full local development
 */
export function supportsLocalDevelopment(): boolean {
  const platform = detectPlatform().platform;
  // Windows has known WebSocket/Docker issues, recommend staging
  return platform !== 'windows';
}

/**
 * Get environment variables for optimal platform configuration
 */
export function getOptimalEnvironmentConfig(): Record<string, string> {
  const platform = detectPlatform();
  const config: Record<string, string> = {};

  if (platform.platform === 'windows') {
    // Issue #860: Windows staging fallback configuration
    config.NEXT_PUBLIC_ENVIRONMENT = 'staging';
    config.NEXT_PUBLIC_PLATFORM_NOTE = 'Windows platform detected - using staging for WebSocket compatibility';
  }

  return config;
}

/**
 * Log platform detection information
 */
export function logPlatformInfo(): void {
  const platform = detectPlatform();

  logger.info('Platform detection complete', undefined, {
    component: 'PlatformDetection',
    action: 'platform_detected',
    metadata: {
      platform: platform.platform,
      version: platform.version,
      architecture: platform.architecture,
      recommendedEnvironment: platform.recommendedEnvironment,
      isSupported: platform.isSupported,
      compatibilityNotesCount: platform.compatibilityNotes.length,
      issue860: platform.platform === 'windows' ? 'Windows WebSocket compatibility mode' : 'Standard platform'
    }
  });

  // Log compatibility notes if any
  if (platform.compatibilityNotes.length > 0) {
    logger.debug('Platform compatibility notes', undefined, {
      component: 'PlatformDetection',
      action: 'compatibility_notes',
      metadata: {
        platform: platform.platform,
        notes: platform.compatibilityNotes
      }
    });
  }
}

/**
 * Display platform information in development console
 */
export function displayPlatformInfo(): void {
  if (typeof console !== 'undefined' && typeof window !== 'undefined') {
    const platform = detectPlatform();

    console.group('🖥️ Platform Detection (Issue #860)');
    console.log(`Platform: ${platform.platform}`);
    console.log(`Version: ${platform.version || 'Unknown'}`);
    console.log(`Architecture: ${platform.architecture || 'Unknown'}`);
    console.log(`Recommended Environment: ${platform.recommendedEnvironment}`);

    if (platform.compatibilityNotes.length > 0) {
      console.log('Compatibility Notes:');
      platform.compatibilityNotes.forEach((note, index) => {
        console.log(`  ${index + 1}. ${note}`);
      });
    }

    if (platform.platform === 'windows') {
      console.log('🪟 Windows detected: Automatic staging fallback enabled for WebSocket compatibility');
    }

    console.groupEnd();
  }
}

// Export the main platform info for easy access
export const platformInfo = detectPlatform();

// Auto-display platform info in development
if (typeof window !== 'undefined' && process.env.NODE_ENV === 'development') {
  // Delay to ensure logger is ready
  setTimeout(() => {
    logPlatformInfo();
    displayPlatformInfo();
  }, 1000);
}