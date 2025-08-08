import { AuthConfigResponse, User } from "@/types";

export async function getAuthConfig(): Promise<AuthConfigResponse> {
  const response = await fetch(`/api/v3/auth/endpoints`);
  if (!response.ok) {
    throw new Error("Failed to fetch auth config");
  }
  return response.json();
}

export async function getUser(): Promise<User | null> {
  const response = await fetch(`/api/v3/auth/user`);
  if (!response.ok) {
    return null;
  }
  return response.json();
}
