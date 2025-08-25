/**
 * Auth Service Export
 * Combines UnifiedAuthService with useAuth hook
 * This provides the authService.useAuth() pattern used throughout the app
 */

import { unifiedAuthService } from './unified-auth-service';
import { useAuth } from './context';

// Create an enhanced authService that includes the useAuth hook
// This allows components to use authService.useAuth() pattern
const authServiceWithHook = Object.create(unifiedAuthService);
authServiceWithHook.useAuth = useAuth;

export const authService = authServiceWithHook;
export default authService;

// Re-export everything from unified-auth-service for compatibility
export * from './unified-auth-service';
