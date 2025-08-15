/* tslint:disable */
/* eslint-disable */
/**
 * Authentication-related type definitions
 * Auto-generated from pydantic models - do not modify by hand
 */

export interface AuthConfigResponse {
  google_client_id: string;
  google_redirect_uri: string;
  dev_mode: boolean;
}

export interface AuthEndpoints {
  login_url: string;
  logout_url: string;
  user_info_url: string;
  refresh_url: string;
}

export interface DevLoginRequest {
  username: string;
  password?: string | null;
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

export interface User {
  id: string;
  email: string;
  name: string;
  full_name?: string | null;
  is_active: boolean;
  is_admin: boolean;
  created_at: string;
  updated_at?: string | null;
}

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