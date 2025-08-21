/**
 * Authentication Domain Types - Single Source of Truth
 * 
 * Consolidated authentication types extracted from registry.ts and auth.ts.
 * This module serves as the authoritative definition for all auth-related types.
 * 
 * CRITICAL ARCHITECTURAL COMPLIANCE:
 * - Maximum file size: 300 lines
 * - All functions: ≤8 lines
 * - Single source of truth for auth types
 * 
 * BVJ: Unified auth types = consistent user auth experience across all segments
 */

import { MessageType, AgentStatus } from '../shared/enums';

// ============================================================================
// CORE USER TYPES - Primary auth entities
// ============================================================================

export interface User {
  id: string;
  email: string;
  full_name?: string | null;
  picture?: string | null;
  is_active?: boolean;
  is_superuser?: boolean;
  hashed_password?: string | null;
  access_token?: string;
  token_type?: string;
}

export interface DevUser {
  id: string;
  email: string;
  name: string;
  full_name?: string | null;
  is_active: boolean;
  is_admin: boolean;
  created_at: string;
}

export interface GoogleUser {
  id: string;
  email: string;
  verified_email: boolean;
  name: string;
  given_name: string;
  family_name: string;
  picture: string;
  locale: string;
}

// ============================================================================
// AUTHENTICATION ENDPOINTS AND CONFIG
// ============================================================================

export interface AuthEndpoints {
  login: string;
  logout: string;
  callback: string;
  token: string;
  user: string;
  dev_login?: string;
}

export interface AuthConfigResponse {
  google_client_id: string;
  endpoints: AuthEndpoints;
  development_mode: boolean;
  user?: User | null;
  authorized_javascript_origins: string[];
  authorized_redirect_uris: string[];
  google_login_url?: string;
  logout_url?: string;
}

// ============================================================================
// TOKEN AND AUTHENTICATION DATA
// ============================================================================

export interface Token {
  access_token: string;
  token_type: string;
  expires_in?: number | null;
  refresh_token?: string | null;
  user: User;
}

export interface TokenPayload {
  sub: string;
  email: string;
  name: string;
  full_name?: string | null;
  exp: number;
  iat: number;
}

export interface DevLoginRequest {
  username: string;
  password?: string | null;
}

// ============================================================================
// USER CREATION AND UPDATE TYPES
// ============================================================================

export interface UserBase {
  email: string;
  name: string;
  full_name?: string | null;
  is_active?: boolean;
  is_admin?: boolean;
}

export interface UserCreate {
  email: string;
  name: string;
  full_name?: string | null;
  password: string;
  is_active?: boolean;
  is_admin?: boolean;
}

export interface UserCreateOAuth {
  email: string;
  name: string;
  full_name?: string | null;
  provider: string;
  provider_user_id: string;
  is_active?: boolean;
  is_admin?: boolean;
}

export interface UserUpdate {
  email?: string | null;
  name?: string | null;
  full_name?: string | null;
  password?: string | null;
  is_active?: boolean | null;
  is_admin?: boolean | null;
}

// ============================================================================
// VALIDATION HELPERS - All functions ≤8 lines
// ============================================================================

export function isValidUser(user: any): user is User {
  return user && 
    typeof user.id === 'string' && 
    typeof user.email === 'string';
}

export function isActiveUser(user: User): boolean {
  return user.is_active !== false;
}

export function isAdminUser(user: User): boolean {
  return user.is_superuser === true;
}

export function hasValidToken(user: User): boolean {
  return !!(user.access_token && user.token_type);
}

export function createGuestUser(): Partial<User> {
  return {
    id: 'guest',
    email: 'guest@netrasystems.ai',
    is_active: false
  };
}

export function sanitizeUserForClient(user: User): Omit<User, 'hashed_password'> {
  const { hashed_password, ...sanitized } = user;
  return sanitized;
}