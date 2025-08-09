import { User } from './User';

export interface AuthEndpoints {
  login: string;
  logout: string;
  token: string;
  user: string;
  dev_login: string;
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
