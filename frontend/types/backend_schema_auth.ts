/* tslint:disable */
/* eslint-disable */
/**
/* This file was automatically generated from pydantic models by running pydantic2ts.
/* Do not modify it by hand - just update the pydantic models and then re-run the script
*/

// Authentication and user types
export interface AuthConfigResponse {
  google_client_id: string;
  endpoints: AuthEndpoints;
  development_mode: boolean;
  user?: User | null;
  authorized_javascript_origins: string[];
  authorized_redirect_uris: string[];
}

export interface AuthEndpoints {
  login: string;
  logout: string;
  token: string;
  user: string;
  dev_login: string;
}

export interface User {
  email: string;
  full_name?: string | null;
  picture?: string | null;
  id: string;
  is_active: boolean;
  is_superuser: boolean;
  hashed_password?: string | null;
  [k: string]: unknown;
}

export interface UserBase {
  email: string;
  full_name?: string | null;
  picture?: string | null;
}

export interface UserCreate {
  email: string;
  full_name?: string | null;
  picture?: string | null;
  password: string;
}

export interface UserCreateOAuth {
  email: string;
  full_name?: string | null;
  picture?: string | null;
}

export interface UserUpdate {
  email: string;
  full_name?: string | null;
  picture?: string | null;
}

export interface DevUser {
  email?: string;
  full_name?: string;
  picture?: string | null;
  is_dev?: boolean;
}

export interface DevLoginRequest {
  email: string;
}

/**
 * Represents the user information received from Google's OAuth service.
 */
export interface GoogleUser {
  email: string;
  name?: string | null;
  picture?: string | null;
}

export interface Token {
  access_token: string;
  token_type: string;
}

export interface TokenPayload {
  sub: string;
}
