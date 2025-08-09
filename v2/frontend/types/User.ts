export interface User {
  email: string;
  is_active?: boolean;
  is_superuser?: boolean;
  full_name?: string | null;
  picture?: string | null;
  id: string;
  access_token?: string;
  token_type?: string;
}
