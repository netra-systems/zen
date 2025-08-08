import { AuthConfigResponse, User } from "@/types";

const API_URL = process.env.NEXT_PUBLIC_API_URL;

export async function getAuthConfig(): Promise<AuthConfigResponse> {
  const response = await fetch(`${API_URL}/api/auth/endpoints`);
  if (!response.ok) {
    throw new Error("Failed to fetch auth config");
  }
  return response.json();
}

export async function getUser(): Promise<User | null> {
  const response = await fetch(`${API_URL}/api/auth/user`);
  if (!response.ok) {
    return null;
  }
  return response.json();
}
