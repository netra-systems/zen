import { AuthConfigResponse, User } from "@/types";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

export async function getAuthConfig(): Promise<AuthConfigResponse> {
  const response = await fetch(`${API_BASE_URL}/api/v3/auth/endpoints`);
  if (!response.ok) {
    throw new Error("Failed to fetch auth config");
  }
  return response.json();
}

export async function getUser(): Promise<User | null> {
  const response = await fetch(`${API_BASE_URL}/api/v3/auth/user`);
  if (!response.ok) {
    return null;
  }
  return response.json();
}
